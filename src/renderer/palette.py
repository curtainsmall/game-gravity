"""占位配色：按对象种类取颜色，含 alpha。"""

from core.game_object import GameObjectKind

BLACK = (0, 0, 0, 255)
BROWN = (139, 69, 19, 128)      # 木板半透明，重叠时能看见下面的方块
PINK = (255, 105, 180, 255)
RED = (220, 20, 60, 255)
ORANGE = (255, 140, 0, 255)
GREEN = (34, 139, 34, 255)
GREY = (180, 180, 180, 255)

COLOR_BY_KIND: dict[GameObjectKind, tuple[int, int, int, int]] = {
    GameObjectKind.BLOCK: BLACK,
    GameObjectKind.PLANK: BROWN,
    GameObjectKind.MOVABLE_BLOCK: PINK,
    GameObjectKind.ITEM: RED,
    GameObjectKind.PLAYER: ORANGE,
    GameObjectKind.DESTINATION: GREEN,
    GameObjectKind.FAN: RED,
}

DEFAULT_COLOR = GREY


def color_for_kind(kind: GameObjectKind) -> tuple[int, int, int, int]:
    return COLOR_BY_KIND.get(kind, DEFAULT_COLOR)
