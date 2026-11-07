"""贴图：把整张美术图按世界矩形缩放，结果按 (路径, 宽, 高, 采样方式, 朝向, 镜像) 缓存。

贴图不是网格对齐的：位置和尺寸都是浮点世界单位，一张图里可以有多个方块的形状，
画上去就盖住了下面的占位方块。朝向先把图顺时针转 90° 的整数档，再按需水平镜像，
最后才缩放到世界矩形；这样美术斜着摆、翻过来用都只要改朝向，不用另存一份图。
找不到图时（调试显示打开）铺黑紫棋盘格标出来。
"""

import pygame

# 朝向到顺时针角度的换算：图片先转，再缩放
FACE_ROTATIONS = {"up": 0, "right": 90, "down": 180, "left": 270}

# 缺图的棋盘格：黑紫相间，一格 8 像素
MISSING_COLORS = ((0, 0, 0), (128, 0, 128))
MISSING_SQUARE = 8

# (路径, 宽, 高, 是否平滑, 朝向, 镜像) -> 缩放好的图；None 表示加载失败，坏图只尝试一次
_CACHE: dict[tuple[str, int, int, bool, str, bool], pygame.Surface | None] = {}


def _oriented(image: pygame.Surface, face: str, flip: bool) -> pygame.Surface:
    """按朝向顺时针转，转完再水平镜像；up、不镜像是原图。"""
    angle = FACE_ROTATIONS.get(str(face), 0)
    if angle:
        image = pygame.transform.rotate(image, -angle)
    if flip:
        image = pygame.transform.flip(image, True, False)
    return image


def load_scaled(
    path: str,
    size: tuple[int, int],
    smooth: bool,
    face: str = "up",
    flip: bool = False,
) -> pygame.Surface | None:
    """按目标像素尺寸缩放整张图；像素画用最近邻，别用平滑。"""
    width, height = size
    if width <= 0 or height <= 0:
        return None
    key = (path, width, height, smooth, str(face), bool(flip))
    if key in _CACHE:
        return _CACHE[key]
    try:
        image = pygame.image.load(path).convert_alpha()
    except (pygame.error, OSError):
        _CACHE[key] = None
        return None
    transform = pygame.transform.smoothscale if smooth else pygame.transform.scale
    _CACHE[key] = transform(_oriented(image, face, flip), (width, height))
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


# 原图尺寸：路径 -> (宽, 高)；读不出来是 None，坏图只尝试一次
_SIZE_CACHE: dict[str, tuple[int, int] | None] = {}


def image_size(path: str) -> tuple[int, int] | None:
    """读图片的像素尺寸（带缓存）；读不出来返回 None。"""
    if path in _SIZE_CACHE:
        return _SIZE_CACHE[path]
    try:
        size = pygame.image.load(path).get_size()
    except (pygame.error, OSError):
        size = None
    _SIZE_CACHE[path] = size
    return size
