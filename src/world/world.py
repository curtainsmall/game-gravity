"""World：关卡世界。纯数据，由关卡场景持有。"""

GRID_WIDTH_IN_BLOCKS = 120
GRID_HEIGHT_IN_BLOCKS = 8
EMPTY_BLOCK_ID = 0


def empty_static_block_grid() -> list[list[int]]:
    """静态方块网格。EMPTY_BLOCK_ID 表示空位。"""
    return [[EMPTY_BLOCK_ID] * GRID_WIDTH_IN_BLOCKS for _ in range(GRID_HEIGHT_IN_BLOCKS)]


class World:
    def __init__(
        self,
        static_block_grid: list[list[int]] | None = None,
        boundary_bodies: list | None = None,
        moving_blocks: list | None = None,
        interactive_objects: list | None = None,
        player_character: object = None,
        gravity_acceleration_magnitude: float = 0.0,
    ):
        self.static_block_grid = static_block_grid if static_block_grid is not None else empty_static_block_grid()
        self.boundary_bodies = boundary_bodies if boundary_bodies is not None else []      # 地面与天花板
        self.moving_blocks = moving_blocks if moving_blocks is not None else []            # 可移动方块
        self.interactive_objects = interactive_objects if interactive_objects is not None else []  # 物件
        self.player_character = player_character
        self.gravity_acceleration_magnitude = gravity_acceleration_magnitude               # 由关卡数据提供
