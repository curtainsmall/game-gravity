"""小工具：路径显示、格子判定、颜色与数字格式化。"""

import os
import re

from core.constants import (
    BUTTON_SIZE,
    FACE_DIRECTIONS,
    KIND_BUTTON,
    KIND_NOZZLE,
    KIND_PORTAL,
    LEVEL_BACKGROUND_NAME,
    NOZZLE_DEFAULT_POWER,
    NOZZLE_DEFAULT_SIZE,
    PORTAL_SIZE,
    ROOT,
)


def entry_contains(entry: dict, point: tuple) -> bool:
    """世界坐标点是否落在对象矩形里（对象都是浮点自由矩形）。"""
    x, y = entry["pos"]
    w, h = entry.get("size", [1.0, 1.0])
    return x <= point[0] <= x + w and y <= point[1] <= y + h


# 吸附步长：半格一条，整格自然也落在上面
SNAP_STEP = 0.5


def snap(value: float) -> float:
    """把一个世界坐标对到最近的半格。"""
    return round(float(value) / SNAP_STEP) * SNAP_STEP


def facing_rect(entry: dict, default_size) -> tuple[float, float, float, float]:
    """按钮、传送门和喷口的矩形：pos 是「底面」的中点，矩形从底面朝 face 指的方向长出去。

    up：底面是下边、往上长；down：底面是上边、往下长；
    right：底面是左边、往右长；left：底面是右边、往左长。
    左右朝向时把宽高对调（竖起来），pos 就落在侧面那条边的中点上。
    """
    x, y = entry["pos"]
    width, height = entry.get("size", default_size)
    face = str(entry.get("face", "up"))
    if face == "right":
        return float(x), float(y) - width / 2.0, float(height), float(width)
    if face == "left":
        return float(x) - height, float(y) - width / 2.0, float(height), float(width)
    if face == "down":
        return float(x) - width / 2.0, float(y) - height, float(width), float(height)
    return float(x) - width / 2.0, float(y), float(width), float(height)


def object_box(kind: str, entry: dict) -> dict:
    """画布和命中用的矩形（pos=左下角 + size）。

    喷口是风区矩形，按钮和传送门是有朝向的矩形，其余对象直接用自己的 pos/size。
    """
    if kind == KIND_NOZZLE:
        return nozzle_box(entry)
    if kind == KIND_BUTTON:
        left, bottom, width, height = facing_rect(entry, BUTTON_SIZE)
    elif kind == KIND_PORTAL:
        left, bottom, width, height = facing_rect(entry, PORTAL_SIZE)
    else:
        return entry
    return {"pos": [left, bottom], "size": [width, height]}


def folder_name_for(name: str) -> str:
    """关卡名 → 文件夹名：去掉 Windows 不允许的字符，空的就退回默认名字。"""
    cleaned = re.sub(r'[<>:"/\\|?*]', "", name or "").strip().strip(".")
    return cleaned or "新关卡"


def normalize_rect(a: tuple, b: tuple, minimum: float) -> tuple:
    """两点 → (x, y, w, h)，宽高不小于 minimum。"""
    x0, x1 = sorted((a[0], b[0]))
    y0, y1 = sorted((a[1], b[1]))
    return x0, y0, max(minimum, x1 - x0), max(minimum, y1 - y0)


def round_rect(rect: tuple, digits: int = 2) -> tuple:
    return tuple(round(value, digits) for value in rect)


def nozzle_box(entry: dict) -> dict:
    """喷口的风区矩形：pos 是底面中点，size 是风区宽高，face 是伸出的方向。"""
    left, bottom, width, height = facing_rect(entry, NOZZLE_DEFAULT_SIZE)
    return {"pos": [left, bottom], "size": [width, height]}


def nozzle_marker_box(entry: dict) -> dict:
    """喷口自己画出来的那块 1×1 标记，也按 face 摆。"""
    marker = dict(entry)
    marker["size"] = [1.0, 1.0]
    left, bottom, width, height = facing_rect(marker, (1.0, 1.0))
    return {"pos": [left, bottom], "size": [width, height]}


def nozzle_face_axis(entry: dict) -> tuple[float, float]:
    """风区伸出的方向；老数据没有 face 时按 power 的正负当成上/下。"""
    face = entry.get("face")
    if face is None:
        face = "up" if float(entry.get("power", NOZZLE_DEFAULT_POWER)) >= 0 else "down"
    return FACE_DIRECTIONS.get(str(face), FACE_DIRECTIONS["up"])


def nozzle_power_tip(entry: dict) -> tuple[float, float]:
    """力度箭头的末端（世界坐标）：pos 沿 face 走出去 power 格。"""
    x, y = entry["pos"]
    step_x, step_y = nozzle_face_axis(entry)
    power = max(0.0, float(entry.get("power", 0)))
    return float(x) + step_x * power, float(y) + step_y * power


def display_path(path: str | None) -> str:
    if not path:
        return "未命名（未保存）"
    try:
        return os.path.relpath(path, ROOT)
    except ValueError:
        return path


def readable_color(color: tuple) -> tuple:
    """方块本身就是近黑色，直接拿来描边会看不见，所以太暗的颜色提亮后用。"""
    if sum(color) >= 150:
        return color
    return tuple(min(255, channel + 110) for channel in color)


def number_text(value) -> str:
    return f"{value:g}" if isinstance(value, float) else str(value)


def clamp_int(value, low: int, high: int, fallback: int) -> int:
    """读关卡尺寸：缺字段、非数字或越界都夹回合法区间，坏数据不至于拖垮画布。"""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(low, min(high, number))


def clamp_float(value, low: float, high: float, fallback: float) -> float:
    """读浮点设置：缺字段、非数字或越界都夹回合法区间。"""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(low, min(high, number))


def resolve_level_path(value: str, base_dir: str | None) -> str | None:
    """相对基准目录（关卡文件夹）的路径 → 绝对路径；没有兜底，找不到就 None。"""
    if not value:
        return None
    path = value.replace("/", os.sep)
    if not os.path.isabs(path):
        if base_dir is None:
            return None
        path = os.path.join(base_dir, path)
    path = os.path.normpath(path)
    return path if os.path.isfile(path) else None


def resolve_background(value: str, base_dir: str | None) -> str | None:
    """background 解析成绝对路径；scene.json 没写就退回文件夹里的 background.png。"""
    found = resolve_level_path(value, base_dir)
    if found is not None:
        return found
    return resolve_level_path(LEVEL_BACKGROUND_NAME, base_dir)


def relative_level_path(path: str, base_dir: str | None) -> str:
    """绝对路径 → 相对基准目录（关卡文件夹）的写法，一律用正斜杠。"""
    try:
        relative = os.path.relpath(path, base_dir) if base_dir else path
    except ValueError:
        relative = path
    return relative.replace(os.sep, "/")


def resolve_texture(value: str, level_path: str | None) -> str | None:
    """贴图路径解析成绝对路径；相对路径以关卡文件夹为基准，没有兜底。"""
    return resolve_level_path(value, level_path)
