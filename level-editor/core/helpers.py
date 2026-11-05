"""小工具：路径显示、格子判定、颜色与数字格式化。"""

import os

from core.constants import LEVEL_BACKGROUND_NAME, LEVELS_DIR, NOZZLE_DEFAULT_POWER, ROOT


def entry_contains(entry: dict, cell: tuple) -> bool:
    x, y = entry["pos"]
    w, h = entry.get("size", [1, 1])
    return x <= cell[0] < x + w and y <= cell[1] < y + h


def normalize_drag(a: tuple, b: tuple) -> tuple:
    x0, x1 = sorted((a[0], b[0]))
    y0, y1 = sorted((a[1], b[1]))
    return x0, y0, x1 - x0 + 1, y1 - y0 + 1


def nozzle_box(entry: dict) -> dict:
    """喷口是点（底边中点）；它画出来的 1×1 三角落在哪一格。

    向上的喷口坐在 y 之上，向下的挂在 y 之下，和游戏里风区的朝向一致。
    """
    x, y = entry["pos"]
    up = int(entry.get("power", NOZZLE_DEFAULT_POWER)) >= 0
    return {"pos": [x - 0.5, y if up else y - 1], "size": [1, 1]}


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


def level_base_dir(level_path: str | None) -> str:
    """关卡的文件夹（path 指向的就是它）；关卡还没保存时用关卡根目录。"""
    if level_path:
        return os.path.abspath(level_path)
    return LEVELS_DIR


def resolve_background(value: str, level_path: str | None) -> str | None:
    """background 解析成绝对路径；scene.json 没写就退回文件夹里的 background.png。"""
    base = level_base_dir(level_path)
    candidates = []
    if value:
        path = value.replace("/", os.sep)
        candidates.append(path if os.path.isabs(path) else os.path.join(base, path))
    candidates.append(os.path.join(base, LEVEL_BACKGROUND_NAME))
    for candidate in candidates:
        candidate = os.path.normpath(candidate)
        if os.path.isfile(candidate):
            return candidate
    return None
