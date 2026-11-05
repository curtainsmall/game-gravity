"""小工具：路径显示、格子判定、颜色与数字格式化。"""

import os
import re

from core.constants import (
    LEVEL_BACKGROUND_NAME,
    LEVELS_DIR,
    NOZZLE_DEFAULT_POWER,
    ROOT,
)


def entry_contains(entry: dict, point: tuple) -> bool:
    """世界坐标点是否落在对象矩形里（对象都是浮点自由矩形）。"""
    x, y = entry["pos"]
    w, h = entry.get("size", [1.0, 1.0])
    return x <= point[0] <= x + w and y <= point[1] <= y + h


def folder_name_for(name: str) -> str:
    """关卡名 → 文件夹名：去掉 Windows 不允许的字符，空的就退回默认名字。"""
    cleaned = re.sub(r'[<>:"/\\|?*]', "", name or "").strip().strip(".")
    return cleaned or "新关卡"


def folder_is_empty(folder: str) -> bool:
    """文件夹里没有东西（不能读也当作非空，别往不明底细的地方写）。"""
    try:
        with os.scandir(folder) as entries:
            return next(entries, None) is None
    except OSError:
        return False


def normalize_rect(a: tuple, b: tuple, minimum: float) -> tuple:
    """两点 → (x, y, w, h)，宽高不小于 minimum。"""
    x0, x1 = sorted((a[0], b[0]))
    y0, y1 = sorted((a[1], b[1]))
    return x0, y0, max(minimum, x1 - x0), max(minimum, y1 - y0)


def round_rect(rect: tuple, digits: int = 2) -> tuple:
    return tuple(round(value, digits) for value in rect)


def nozzle_box(entry: dict) -> dict:
    """喷口是点（底边中点）：画出来的 1×1 三角所在的世界矩形。

    向上的喷口坐在 y 之上，向下的挂在 y 之下，和游戏里风区的朝向一致。
    """
    x, y = entry["pos"]
    up = float(entry.get("power", NOZZLE_DEFAULT_POWER)) >= 0
    return {"pos": [x - 0.5, y if up else y - 1], "size": [1.0, 1.0]}


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


def level_base_dir(level_path: str | None) -> str:
    """关卡的文件夹（path 指向的就是它）；关卡还没保存时用关卡根目录。"""
    if level_path:
        return os.path.abspath(level_path)
    return LEVELS_DIR


def resolve_level_path(value: str, level_path: str | None) -> str | None:
    """相对 scene.json 的路径 → 绝对路径；没有兜底，找不到就 None。"""
    if not value:
        return None
    path = value.replace("/", os.sep)
    if not os.path.isabs(path):
        path = os.path.join(level_base_dir(level_path), path)
    path = os.path.normpath(path)
    return path if os.path.isfile(path) else None


def resolve_background(value: str, level_path: str | None) -> str | None:
    """background 解析成绝对路径；scene.json 没写就退回文件夹里的 background.png。"""
    found = resolve_level_path(value, level_path)
    if found is not None:
        return found
    return resolve_level_path(LEVEL_BACKGROUND_NAME, level_path)


def relative_level_path(path: str, level_path: str | None) -> str:
    """绝对路径 → 相对 scene.json 所在目录的写法，一律用正斜杠。"""
    try:
        relative = os.path.relpath(path, level_base_dir(level_path))
    except ValueError:
        relative = path
    return relative.replace(os.sep, "/")


def resolve_texture(value: str, level_path: str | None) -> str | None:
    """贴图路径解析成绝对路径；相对路径以关卡文件夹为基准，没有兜底。"""
    return resolve_level_path(value, level_path)
