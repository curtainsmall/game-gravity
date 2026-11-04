"""World：关卡世界。纯数据。"""

WIDTH_IN_BLOCKS = 120
HEIGHT_IN_BLOCKS = 8

# 整局固定的重力加速度，单位方块/秒²。它与 60 步/秒的步长绑定，
# 因此不放进关卡数据；跳速表也是按这个值反解的。
GRAVITY_ACCELERATION = 60.0


class World:
    def __init__(
        self,
        gravity_acceleration_magnitude: float = GRAVITY_ACCELERATION,
        width_in_blocks: int = WIDTH_IN_BLOCKS,
        height_in_blocks: int = HEIGHT_IN_BLOCKS,
    ) -> None:
        self.gravity_acceleration_magnitude: float = gravity_acceleration_magnitude  # 整关一个值
        self.width_in_blocks: int = width_in_blocks
        self.height_in_blocks: int = height_in_blocks
