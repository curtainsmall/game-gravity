"""贴图：把整张美术图按世界矩形缩放，结果按 (路径, 宽, 高, 采样方式) 缓存。

贴图不是网格对齐的：位置和尺寸都是浮点世界单位，一张图里可以有多个方块的形状，
画上去就盖住了下面的占位方块。
"""

import pygame

# (路径, 宽, 高, 是否平滑) -> 缩放好的图；None 表示加载失败，坏图只尝试一次
_CACHE: dict[tuple[str, int, int, bool], pygame.Surface | None] = {}


def load_scaled(path: str, size: tuple[int, int], smooth: bool) -> pygame.Surface | None:
    """按目标像素尺寸缩放整张图；像素画用最近邻，别用平滑。"""
    width, height = size
    if width <= 0 or height <= 0:
        return None
    key = (path, width, height, smooth)
    if key in _CACHE:
        return _CACHE[key]
    try:
        image = pygame.image.load(path).convert_alpha()
    except (pygame.error, OSError):
        _CACHE[key] = None
        return None
    transform = pygame.transform.smoothscale if smooth else pygame.transform.scale
    _CACHE[key] = transform(image, (width, height))
    return _CACHE[key]
