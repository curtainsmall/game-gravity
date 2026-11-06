"""编辑器画布里的背景图：规则和游戏一致。

先把图等比缩放到可玩区的高度，再按图案自身宽度横向重复；只在可玩区里画，
地面行和天花板行都与它无关。
"""

import pygame

from core.helpers import resolve_background

# (路径, 目标高度) -> 缩放好的图；None 表示加载失败，坏图只尝试一次
_CACHE: dict[tuple[str, int], pygame.Surface | None] = {}


def load_scaled(path: str, height: int) -> pygame.Surface | None:
    """把背景图等比缩放到指定高度。"""
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


def draw_background(
    surface: pygame.Surface, layout, value: str, base_dir: str | None
) -> None:
    """画在可玩区里；裁剪到网格范围，免得盖到右侧面板上。"""
    path = resolve_background(value, base_dir)
    if path is None:
        return
    image = load_scaled(path, max(1, round(layout.tile * layout.rows)))
    if image is None:
        return

    area = layout.world_rect(0, 0, layout.cols, layout.rows)
    previous_clip = surface.get_clip()
    surface.set_clip(area)
    pattern_width = image.get_width()
    x = area.left
    while x < area.right:
        surface.blit(image, (x, area.top))
        x += pattern_width
    surface.set_clip(previous_clip)
