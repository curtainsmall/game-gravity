"""窗口：游戏内部固定 960x540，窗口只能从四个角按对角线拉，松手后保持 16:9。

左右上下四条边不做缩放热区（Windows 上把边框的 WM_NCHITTEST 结果改成 HTBORDER），
拖角才改尺寸；拖的时候先让窗口跟手，松手（WM_EXITSIZEMOVE）再按 16:9 掰正。
缩放取宽和高里小的那个比例，多出来的边填黑（比例换算后最多差一像素）。
鼠标坐标要反着换算回游戏坐标，界面上的按钮、悬停才点得准。
"""

import ctypes
import sys

import pygame

LOGICAL_SIZE = (960, 540)
ASPECT_RATIO = LOGICAL_SIZE[0] / LOGICAL_SIZE[1]
ASPECT_TOLERANCE = 1.0     # 宽度差一像素以内就算已经是 16:9，免得反复重设窗口
BACKDROP_COLOR = (0, 0, 0)
MIN_SCALE = 0.1

# 鼠标事件里带 pos 的几种：位置要换算，rel 没人用，不动
MOUSE_EVENTS = (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION)

# Win32：只留四角的缩放热区，顺便知道一次拖动什么时候结束
WM_NCHITTEST = 0x0084
WM_ENTERSIZEMOVE = 0x0231
WM_EXITSIZEMOVE = 0x0232
GWL_WNDPROC = -4
HTBORDER = 18
EDGE_HITS = frozenset((10, 11, 12, 15))   # 左、右、上、下

_scale = 1.0
_origin = (0.0, 0.0)
_pending_size = None
_settled_size = LOGICAL_SIZE
_maximized = False
_moving = False
_hooked_hwnd = None
_old_proc = None
_window_proc_ref = None


def refresh() -> None:
    """每帧开头调一次：按当前窗口大小算好缩放比例和居中留边。"""
    global _scale, _origin
    width, height = pygame.display.get_window_size()
    if width <= 0 or height <= 0:
        return
    _scale = max(
        MIN_SCALE,
        min(width / LOGICAL_SIZE[0], height / LOGICAL_SIZE[1]),
    )
    _origin = (
        (width - LOGICAL_SIZE[0] * _scale) / 2.0,
        (height - LOGICAL_SIZE[1] * _scale) / 2.0,
    )


def to_logical(pos) -> tuple[float, float]:
    """窗口坐标换算成游戏坐标；落在黑边里就会是负数或超出画面。"""
    return ((pos[0] - _origin[0]) / _scale, (pos[1] - _origin[1]) / _scale)


def _is_proportional(width: int, height: int) -> bool:
    return abs(width - height * ASPECT_RATIO) <= ASPECT_TOLERANCE


def _window_proc(hwnd, message, wparam, lparam):
    global _moving
    result = ctypes.windll.user32.CallWindowProcW(_old_proc, hwnd, message, wparam, lparam)
    if message == WM_ENTERSIZEMOVE:
        _moving = True
    elif message == WM_EXITSIZEMOVE:
        _moving = False
    elif message == WM_NCHITTEST and result in EDGE_HITS:
        return HTBORDER
    return result


def limit_resize_to_corners() -> None:
    """关掉四条边的缩放热区，只留四个角；非 Windows 系统不做这件事。"""
    global _hooked_hwnd, _old_proc, _window_proc_ref
    if sys.platform != "win32":
        return
    hwnd = pygame.display.get_wm_info().get("window")
    if not hwnd or hwnd == _hooked_hwnd:
        return
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    set_long = getattr(user32, "SetWindowLongPtrW", None) or user32.SetWindowLongW
    set_long.restype = ctypes.c_void_p
    set_long.argtypes = (wintypes.HWND, ctypes.c_int, ctypes.c_void_p)
    user32.CallWindowProcW.restype = ctypes.c_ssize_t
    user32.CallWindowProcW.argtypes = (
        ctypes.c_void_p,
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    )
    proc_type = ctypes.WINFUNCTYPE(
        ctypes.c_ssize_t,
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    )
    _window_proc_ref = proc_type(_window_proc)
    old_proc = set_long(hwnd, GWL_WNDPROC, ctypes.cast(_window_proc_ref, ctypes.c_void_p))
    if not old_proc:
        _window_proc_ref = None
        return
    _old_proc = old_proc
    _hooked_hwnd = hwnd


def _proportional_size(width: int, height: int) -> tuple[int, int]:
    """哪一边被拖得多就听哪一边，另一边按 16:9 折算。"""
    settled_width, settled_height = _settled_size
    width_shift = abs(width - settled_width) / max(1, settled_width)
    height_shift = abs(height - settled_height) / max(1, settled_height)
    if width_shift >= height_shift:
        return width, max(1, round(width / ASPECT_RATIO))
    return max(1, round(height * ASPECT_RATIO)), height


def handle_event(event: pygame.event.Event) -> None:
    """记下窗口状态：最大化时别去动它，新尺寸等这一批事件收完再定。"""
    global _pending_size, _maximized
    if event.type == pygame.WINDOWMAXIMIZED:
        _maximized = True
        _pending_size = None
    elif event.type == pygame.WINDOWRESTORED:
        _maximized = False
    elif event.type == pygame.VIDEORESIZE and not _maximized:
        _pending_size = event.size


def settle() -> None:
    """每帧事件收完调一次：松手后把窗口按 16:9 掰正。"""
    global _pending_size, _settled_size
    if _pending_size is None or _moving or _maximized:
        return
    _pending_size = None
    width, height = pygame.display.get_window_size()
    if width <= 0 or height <= 0:
        return
    if _is_proportional(width, height):
        _settled_size = (width, height)
        return
    pygame.display.set_mode(_proportional_size(width, height), pygame.RESIZABLE)
    limit_resize_to_corners()
    refresh()
    _settled_size = pygame.display.get_window_size()


def mouse_pos() -> tuple[float, float]:
    """鼠标在游戏坐标里的位置，界面拿它算悬停。"""
    return to_logical(pygame.mouse.get_pos())


def logical_event(event: pygame.event.Event) -> pygame.event.Event:
    """带坐标的鼠标事件换成游戏坐标；别的事件原样返回。"""
    if event.type not in MOUSE_EVENTS:
        return event
    payload = dict(event.dict)
    payload["pos"] = to_logical(event.pos)
    return pygame.event.Event(event.type, payload)


def present(surface: pygame.Surface, frame: pygame.Surface) -> None:
    """把 960x540 的画面等比缩放后贴到窗口正中，四周空出来的地方填黑。"""
    width, height = surface.get_size()
    if width <= 0 or height <= 0:
        return
    surface.fill(BACKDROP_COLOR)
    target = (round(LOGICAL_SIZE[0] * _scale), round(LOGICAL_SIZE[1] * _scale))
    picture = frame if target == LOGICAL_SIZE else pygame.transform.smoothscale(frame, target)
    surface.blit(picture, (round(_origin[0]), round(_origin[1])))
