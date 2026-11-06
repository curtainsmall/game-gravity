"""编辑器画布里的贴图：和游戏同一套规则。

整张图按世界矩形缩放（浮点、不吸格子），画在方块和木板之上，超出可玩区的部分裁掉；
朝向先把图顺时针转 90° 的整数档，再按需水平镜像，最后才缩放到世界矩形，和游戏一致。
后画的盖住先画的，数组顺序就是绘制顺序。找不到图时（调试显示打开）铺黑紫棋盘格。
"""

import pygame

from core.helpers import resolve_texture

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
    if size[0] <= 0 or size[1] <= 0:
        return None
    key = (path, size[0], size[1], smooth, str(face), bool(flip))
    if key in _CACHE:
        return _CACHE[key]
    try:
        image = pygame.image.load(path).convert_alpha()
    except (pygame.error, OSError):
        _CACHE[key] = None
        return None
    transform = pygame.transform.smoothscale if smooth else pygame.transform.scale
    _CACHE[key] = transform(_oriented(image, face, flip), size)
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


def draw_textures(
    surface: pygame.Surface, layout, level, base_dir: str | None, debug: bool = True
) -> None:
    """按数组顺序画，后一个盖前一个。

    编辑器里不裁剪：超出可玩区的部分照样画出来，方便看清整张图对到哪，
    游戏里才裁到可玩区。朝向和镜像按条目里的 face / flip 摆，和游戏里一样。
    图找不到时，调试显示打开就画黑紫棋盘格。
    """
    for entry in level.textures:
        rect = texture_rect(layout, entry)
        path = resolve_texture(entry.get("image"), base_dir)
        image = None
        if path is not None:
            image = load_scaled(
                path,
                rect.size,
                bool(entry.get("smooth", False)),
                str(entry.get("face", "up")),
                bool(entry.get("flip", False)),
            )
        if image is None:
            if debug:
                draw_missing_texture(surface, rect)
            continue
        surface.blit(image, rect.topleft)
