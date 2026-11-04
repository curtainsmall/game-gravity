"""World：关卡世界。纯数据。"""

WIDTH_IN_BLOCKS = 120
HEIGHT_IN_BLOCKS = 8


class World:
    def __init__(
        self,
        gravity_acceleration_magnitude: float = 0.0,
        width_in_blocks: int = WIDTH_IN_BLOCKS,
        height_in_blocks: int = HEIGHT_IN_BLOCKS,
    ) -> None:
        self.gravity_acceleration_magnitude: float = gravity_acceleration_magnitude  # 整关一个值
        self.width_in_blocks: int = width_in_blocks
        self.height_in_blocks: int = height_in_blocks
