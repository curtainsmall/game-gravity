"""极简 UI：字体、配色、按钮与面板的绘制，以及各个界面的按钮几何。

几何函数只看窗口尺寸，绘制和点击用同一套，保证命中区域和画出来的一致。
"""

import math

import pygame

import window

BACKGROUND = (235, 235, 235)
PANEL = (250, 250, 250)
TEXT = (40, 40, 40)
DIM_TEXT = (120, 120, 120)
BUTTON = (255, 255, 255)
BUTTON_HOVER = (255, 235, 150)
BORDER = (160, 160, 160)
SHADE = (0, 0, 0, 140)

BUTTON_SIZE = (260, 52)
BUTTON_GAP = 14
GEAR_SIZE = 56
LEVEL_ROW_HEIGHT = 96
LEVEL_ROW_GAP = 12
LEVEL_LIST_MARGIN = 48
DEBUG_ROW_HEIGHT = 26     # 设置里那一行勾选框的高度

# 设置浮层里的音量：总音量、音乐、音效，各一行「标签 | 滑条 | − ＋ | 百分比」
VOLUME_KEYS = ("master", "music", "sfx")
VOLUME_LABELS = {"master": "总音量", "music": "音乐", "sfx": "音效"}
VOLUME_ROW_HEIGHT = 34
VOLUME_ROW_GAP = 6
VOLUME_LABEL_WIDTH = 84
VOLUME_STEP_WIDTH = 26
VOLUME_VALUE_WIDTH = 48
SETTINGS_PANEL_SIZE = (460, 386)

# 背包：4 列 × 3 行，右边是 1:1 的说明图；物品多时按页翻
BACKPACK_PANEL_SIZE = (760, 460)
BACKPACK_COLUMNS = 4
BACKPACK_ROWS = 3
BACKPACK_SLOT = 88
BACKPACK_GAP = 12
BACKPACK_DETAIL = 300
BACKPACK_MARGIN = 24


def backpack_rects(
    surface: pygame.Surface, count: int, page: int, selected: int
) -> dict:
    """背包浮层的几何：格子、说明图和页码。画与点击共用这一套矩形。"""
    width, height = surface.get_size()
    panel = pygame.Rect(0, 0, *BACKPACK_PANEL_SIZE)
    panel.center = (width // 2, height // 2)
    title = pygame.Rect(panel.left + BACKPACK_MARGIN, panel.top + 14, 240, 34)
    hint = pygame.Rect(panel.right - BACKPACK_MARGIN - 150, panel.top + 20, 150, 24)
    grid_top = panel.top + 68
    grid_left = panel.left + BACKPACK_MARGIN
    slots = []
    for row in range(BACKPACK_ROWS):
        for column in range(BACKPACK_COLUMNS):
            index = page * BACKPACK_COLUMNS * BACKPACK_ROWS + row * BACKPACK_COLUMNS + column
            slots.append(
                {
                    "rect": pygame.Rect(
                        grid_left + column * (BACKPACK_SLOT + BACKPACK_GAP),
                        grid_top + row * (BACKPACK_SLOT + BACKPACK_GAP),
                        BACKPACK_SLOT,
                        BACKPACK_SLOT,
                    ),
                    "index": index,
                    "filled": index < count,
                }
            )
    detail = pygame.Rect(
        panel.left + BACKPACK_MARGIN + BACKPACK_COLUMNS * BACKPACK_SLOT
        + (BACKPACK_COLUMNS - 1) * BACKPACK_GAP + 24,
        panel.top + 84,
        BACKPACK_DETAIL,
        BACKPACK_DETAIL,
    )
    footer = pygame.Rect(panel.left + BACKPACK_MARGIN, panel.bottom - 38, 400, 24)
    page_count = max(1, (count + BACKPACK_COLUMNS * BACKPACK_ROWS - 1) // (
        BACKPACK_COLUMNS * BACKPACK_ROWS
    ))
    page = max(0, min(int(page), page_count - 1))
    return {
        "panel": panel,
        "title": title,
        "hint": hint,
        "slots": slots,
        "detail": detail,
        "footer": footer,
        "page": page,
        "page_count": page_count,
        "selected": int(selected),
    }

_FONTS: dict[int, pygame.font.Font] = {}


def font(size: int) -> pygame.font.Font:
    if size not in _FONTS:
        _FONTS[size] = pygame.font.SysFont("microsoftyahei", size)
    return _FONTS[size]


def draw_text(
    surface: pygame.Surface,
    text: str,
    size: int,
    center: tuple | None = None,
    pos: tuple | None = None,
    color: tuple = TEXT,
) -> pygame.Rect:
    rendered = font(size).render(text, True, color)
    rect = rendered.get_rect()
    if center is not None:
        rect.center = center
    else:
        rect.topleft = pos or (0, 0)
    surface.blit(rendered, rect)
    return rect


def draw_button(surface: pygame.Surface, rect: pygame.Rect, label: str, size: int = 22) -> None:
    hovered = rect.collidepoint(window.mouse_pos())
    pygame.draw.rect(surface, BUTTON_HOVER if hovered else BUTTON, rect)
    pygame.draw.rect(surface, BORDER, rect, 2)
    draw_text(surface, label, size, center=rect.center)


def draw_shade(surface: pygame.Surface) -> None:
    shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    shade.fill(SHADE)
    surface.blit(shade, (0, 0))


def draw_panel(surface: pygame.Surface, rect: pygame.Rect) -> None:
    pygame.draw.rect(surface, PANEL, rect)
    pygame.draw.rect(surface, BORDER, rect, 2)


def draw_gear(surface: pygame.Surface, rect: pygame.Rect, color: tuple = TEXT) -> None:
    """齿轮：一圈方块齿 + 中间挖空的圆。"""
    centre = rect.center
    radius = min(rect.width, rect.height) / 2.0
    for index in range(8):
        angle = math.radians(index * 45)
        inner, outer, half = radius * 0.62, radius * 0.84, radius * 0.12
        corners = [(inner, -half), (outer, -half), (outer, half), (inner, half)]
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        pygame.draw.polygon(
            surface,
            color,
            [
                (centre[0] + x * cos_a - y * sin_a, centre[1] + x * sin_a + y * cos_a)
                for x, y in corners
            ],
        )
    pygame.draw.circle(surface, color, centre, radius * 0.62)
    pygame.draw.circle(surface, BUTTON, centre, radius * 0.24)


def draw_toast(surface: pygame.Surface, text: str, remaining: float) -> None:
    """屏幕底部的临时提示；快消失时淡出。"""
    alpha = 255 if remaining > 0.5 else max(0, int(255 * remaining / 0.5))
    label = font(20).render(text, True, (255, 255, 255))
    box = pygame.Rect(0, 0, label.get_width() + 40, label.get_height() + 20)
    box.center = (surface.get_width() // 2, surface.get_height() - 64)
    layer = pygame.Surface(box.size, pygame.SRCALPHA)
    layer.fill((40, 40, 40, min(alpha, 215)))
    surface.blit(layer, box.topleft)
    label.set_alpha(alpha)
    surface.blit(label, (box.left + 20, box.top + 10))


# ---- 标题界面 -------------------------------------------------------
def title_rects(surface: pygame.Surface) -> dict:
    width, height = surface.get_size()
    button_width, button_height = BUTTON_SIZE
    top = int(height * 0.40)
    rects = {}
    for index, key in enumerate(("start", "levels", "quit")):
        rects[key] = pygame.Rect(
            (width - button_width) // 2,
            top + index * (button_height + BUTTON_GAP),
            button_width,
            button_height,
        )
    rects["settings"] = pygame.Rect(
        width - 28 - GEAR_SIZE, height - 28 - GEAR_SIZE, GEAR_SIZE, GEAR_SIZE
    )
    return rects


# ---- 选关界面 -------------------------------------------------------
def level_view_area(surface: pygame.Surface) -> pygame.Rect:
    width, height = surface.get_size()
    return pygame.Rect(
        LEVEL_LIST_MARGIN,
        96,
        max(1, width - 2 * LEVEL_LIST_MARGIN),
        max(1, height - 96 - LEVEL_LIST_MARGIN),
    )


def level_row_rect(surface: pygame.Surface, index: int, scroll: int) -> pygame.Rect:
    area = level_view_area(surface)
    return pygame.Rect(
        area.left,
        area.top + index * (LEVEL_ROW_HEIGHT + LEVEL_ROW_GAP) - scroll,
        area.width,
        LEVEL_ROW_HEIGHT,
    )


def max_level_scroll(surface: pygame.Surface, count: int) -> int:
    area = level_view_area(surface)
    total = count * (LEVEL_ROW_HEIGHT + LEVEL_ROW_GAP)
    return max(0, total - area.height)


def back_rect(surface: pygame.Surface) -> pygame.Rect:
    return pygame.Rect(24, 24, 96, 40)


# ---- 结算界面 -------------------------------------------------------
def ending_rects(surface: pygame.Surface) -> dict:
    """结局画面名单放完之后的两个按钮：竖着叠在画面正中间。"""
    width, height = surface.get_size()
    button_width, button_height = BUTTON_SIZE
    total = button_height * 2 + BUTTON_GAP
    top = (height - total) // 2
    return {
        "title": pygame.Rect((width - button_width) // 2, top, button_width, button_height),
        "quit": pygame.Rect(
            (width - button_width) // 2,
            top + button_height + BUTTON_GAP,
            button_width,
            button_height,
        ),
    }


# ---- 暂停与设置浮层 -------------------------------------------------
def pause_rects(surface: pygame.Surface) -> dict:
    width, height = surface.get_size()
    panel = pygame.Rect(0, 0, 320, 366)
    panel.center = (width // 2, height // 2)
    rects = {"panel": panel}
    for index, key in enumerate(("resume", "restart", "settings", "title")):
        rects[key] = pygame.Rect(
            panel.left + 30,
            panel.top + 84 + index * (BUTTON_SIZE[1] + BUTTON_GAP),
            panel.width - 60,
            BUTTON_SIZE[1],
        )
    return rects


def cutscene_pause_rects(surface: pygame.Surface) -> dict:
    """过场的暂停浮层：和游戏暂停一样，但没有「重新开始」（那是玩法用的）。"""
    width, height = surface.get_size()
    panel = pygame.Rect(0, 0, 320, 288)
    panel.center = (width // 2, height // 2)
    rects = {"panel": panel}
    for index, key in enumerate(("resume", "settings", "title")):
        rects[key] = pygame.Rect(
            panel.left + 30,
            panel.top + 84 + index * (BUTTON_SIZE[1] + BUTTON_GAP),
            panel.width - 60,
            BUTTON_SIZE[1],
        )
    return rects


def settings_rects(surface: pygame.Surface) -> dict:
    """设置浮层：三档音量、两个调试开关，加上返回按钮。

    音量每行是「标签 | 滑条 | − ＋ | 百分比」：点滑条直接跳到那个位置，点加减按
    10% 一格走。滑条的 hit 比画出来的条高，整行都能点中。两个开关各占一行：
    整体的调试显示和只管玩家的调试显示。
    """
    width, height = surface.get_size()
    panel = pygame.Rect(0, 0, *SETTINGS_PANEL_SIZE)
    panel.center = (width // 2, height // 2)

    rows = {}
    top = panel.top + 92
    for index, key in enumerate(VOLUME_KEYS):
        row = pygame.Rect(
            panel.left + 24,
            top + index * (VOLUME_ROW_HEIGHT + VOLUME_ROW_GAP),
            panel.width - 48,
            VOLUME_ROW_HEIGHT,
        )
        plus = pygame.Rect(row.right - VOLUME_STEP_WIDTH, row.centery - 11, VOLUME_STEP_WIDTH, 22)
        minus = pygame.Rect(plus.left - 6 - VOLUME_STEP_WIDTH, plus.top, VOLUME_STEP_WIDTH, 22)
        value = pygame.Rect(
            minus.left - 8 - VOLUME_VALUE_WIDTH, row.top, VOLUME_VALUE_WIDTH, row.height
        )
        track = pygame.Rect(
            row.left + VOLUME_LABEL_WIDTH,
            row.centery - 5,
            max(1, value.left - 8 - (row.left + VOLUME_LABEL_WIDTH)),
            10,
        )
        rows[key] = {
            "row": row,
            "track": track,
            "hit": pygame.Rect(track.left, row.top, track.width, row.height),
            "minus": minus,
            "plus": plus,
            "value": value,
        }

    debug = pygame.Rect(panel.left + 24, panel.top + 236, panel.width - 48, DEBUG_ROW_HEIGHT)
    return {
        "panel": panel,
        "volume": rows,
        "debug": debug,
        "player_debug": pygame.Rect(
            debug.left, debug.bottom + 6, debug.width, DEBUG_ROW_HEIGHT
        ),
        "back": pygame.Rect(
            panel.left + 30, panel.bottom - 20 - BUTTON_SIZE[1], panel.width - 60, BUTTON_SIZE[1]
        ),
    }
