"""编辑器画布里的贴图：和游戏同一套规则。

整张图按世界矩形缩放（浮点、不吸格子），画在方块和木板之上，超出可玩区的部分裁掉；
后画的盖住先画的，数组顺序就是绘制顺序。
"""

import pygame

from core.helpers import resolve_texture

# (路径, 宽, 高, 是否平滑) -> 缩放好的图；None 表示加载失败，坏图只尝试一次
_CACHE: dict[tuple[str, int, int, bool], pygame.Surface | None] = {}


def load_scaled(path: str, size: tuple[int, int], smooth: bool) -> pygame.Surface | None:
    if size[0] <= 0 or size[1] <= 0:
        return None
    key = (path, size[0], size[1], smooth)
    if key in _CACHE:
        return _CACHE[key]
    try:
        image = pygame.image.load(path).convert_alpha()
    except (pygame.error, OSError):
        _CACHE[key] = None
        return None
    transform = pygame.transform.smoothscale if smooth else pygame.transform.scale
    _CACHE[key] = transform(image, size)
    return _CACHE[key]


def image_size(path: str) -> tuple[int, int] | None:
    """读图片的像素尺寸；读不出来返回 None（导入贴图时用它换算世界尺寸）。"""
    try:
        return pygame.image.load(path).get_size()
    except (pygame.error, OSError):
        return None


def texture_rect(layout, entry: dict) -> pygame.Rect:
    x, y = entry["pos"]
    width, height = entry.get("size", [1.0, 1.0])
    return layout.world_rect(x, y, width, height)


def draw_textures(
    surface: pygame.Surface, layout, level, level_path: str | None
) -> None:
    """按数组顺序画，后一个盖前一个。

    编辑器里不裁剪：超出可玩区的部分照样画出来，方便看清整张图对到哪，
    游戏里才裁到可玩区。
    """
    for entry in level.textures:
        path = resolve_texture(entry.get("image"), level_path)
        if path is None:
            continue
        rect = texture_rect(layout, entry)
        image = load_scaled(path, rect.size, bool(entry.get("smooth", False)))
        if image is None:
            continue
        surface.blit(image, rect.topleft)
