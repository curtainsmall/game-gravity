"""贴图：把整张美术图按世界矩形缩放，结果按 (路径, 宽, 高, 采样方式) 缓存。

贴图不是网格对齐的：位置和尺寸都是浮点世界单位，一张图里可以有多个方块的形状，
画上去就盖住了下面的占位方块。找不到图时（调试显示打开）铺黑紫棋盘格标出来。
"""

import pygame

# 缺图的棋盘格：黑紫相间，一格 8 像素
MISSING_COLORS = ((0, 0, 0), (128, 0, 128))
MISSING_SQUARE = 8

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


def draw_missing_texture(surface: pygame.Surface, rect: pygame.Rect) -> None:
    """找不到图时铺一块黑紫棋盘格，一看就知道这里缺图（只在调试显示里画）。"""
    if rect.width <= 0 or rect.height <= 0:
        return
    for row in range(0, rect.height, MISSING_SQUARE):
        for col in range(0, rect.width, MISSING_SQUARE):
            color = MISSING_COLORS[(row // MISSING_SQUARE + col // MISSING_SQUARE) % 2]
            pygame.draw.rect(
                surface,
                color,
                (
                    rect.left + col,
                    rect.top + row,
                    min(MISSING_SQUARE, rect.width - col),
                    min(MISSING_SQUARE, rect.height - row),
                ),
            )
