"""占位配色：按对象种类取颜色，含 alpha。"""

from core.game_object import GameObjectKind

BLACK = (0, 0, 0, 255)
BROWN = (139, 69, 19, 128)      # 木板半透明，重叠时能看见下面的方块
PINK = (255, 105, 180, 255)
RED = (220, 20, 60, 255)
ORANGE = (255, 140, 0, 255)
GREEN = (34, 139, 34, 255)
PURPLE = (130, 80, 200, 255)
GREY = (180, 180, 180, 255)
GHOST = (200, 200, 210, 70)     # 贴图没图可画时留下的淡框，方便看出漏了哪张

COLOR_BY_KIND: dict[GameObjectKind, tuple[int, int, int, int]] = {
    GameObjectKind.BLOCK: BLACK,
    GameObjectKind.PLANK: BROWN,
    GameObjectKind.MOVABLE_BLOCK: PINK,
    GameObjectKind.PLAYER: ORANGE,
    GameObjectKind.DESTINATION: GREEN,
    GameObjectKind.NOZZLE: RED,
    GameObjectKind.TRIGGER_SOURCE: RED,
    GameObjectKind.PORTAL: PURPLE,
    GameObjectKind.WALL: BLACK,
    GameObjectKind.TEXTURE: GHOST,
}

DEFAULT_COLOR = GREY


def color_for_kind(kind: GameObjectKind) -> tuple[int, int, int, int]:
    return COLOR_BY_KIND.get(kind, DEFAULT_COLOR)
