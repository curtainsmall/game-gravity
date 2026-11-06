"""背景图：先按高度铺满整个可玩区，再横向重复填满画面。

关卡 JSON 里的 background 是一个相对路径（基准是 game.json 所在目录）。
缩放结果按「路径 + 目标高度」缓存：窗口或关卡尺寸不变时不会每帧重新缩放。
"""

import pygame

from world.world import World

# (路径, 目标高度) -> 缩放好的图；None 表示加载失败，坏图只尝试一次
_CACHE: dict[tuple[str, int], pygame.Surface | None] = {}


def load_scaled(path: str, height: int) -> pygame.Surface | None:
    """把背景图等比缩放到指定高度，跨度和高度都不裁剪。"""
    if height <= 0:
        return None
    key = (path, height)
    if key in _CACHE:
        return _CACHE[key]
    try:
        image = pygame.image.load(path).convert_alpha()
    except (pygame.error, OSError):
        _CACHE[key] = None
        return None
    source_height = image.get_height()
    width = max(1, round(image.get_width() * height / source_height)) if source_height else height
    scaled = pygame.transform.smoothscale(image, (width, height))
    _CACHE[key] = scaled
    return scaled


def draw_background(surface: pygame.Surface, world: World, viewport) -> None:
    """画在可玩区里：天花板那行之下，宽按图案自身宽度重复。"""
    path = world.background_path
    if not path:
        return
    tile = viewport.pixels_per_tile
    height = max(1, round(tile * world.height_in_blocks))
    image = load_scaled(path, height)
    if image is None:
        return

    top = round(viewport.origin_y + tile)          # 可玩区顶边：跳过天花板那一行
    pattern_width = image.get_width()
    # 图案锚在关卡 x = 0 上，跟着镜头左右移动；从左边外侧一整格开始铺
    x = -round(viewport.left_in_blocks * tile) % pattern_width - pattern_width
    while x < surface.get_width():
        surface.blit(image, (x, top))
        x += pattern_width
