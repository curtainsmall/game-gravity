"""占位配色：按对象种类取颜色。"""

from core.game_object import GameObjectKind

BLACK = (0, 0, 0)
BROWN = (139, 69, 19)
PINK = (255, 105, 180)
RED = (220, 20, 60)
YELLOW = (255, 215, 0)
GREEN = (34, 139, 34)
GREY = (180, 180, 180)

COLOR_BY_KIND: dict[GameObjectKind, tuple[int, int, int]] = {
    GameObjectKind.BLOCK: BLACK,
    GameObjectKind.PLANK: BROWN,
    GameObjectKind.MOVABLE_BLOCK: PINK,
    GameObjectKind.ITEM: RED,
    GameObjectKind.PLAYER: YELLOW,
    GameObjectKind.DESTINATION: GREEN,
}

DEFAULT_COLOR = GREY


def color_for_kind(kind: GameObjectKind) -> tuple[int, int, int]:
    return COLOR_BY_KIND.get(kind, DEFAULT_COLOR)
