"""Body：碰撞体。纯数据，行为由函数承载。"""


class Body:
    """AABB 碰撞体。单位：方块。y 轴向上，地面为 0。"""

    def __init__(
        self,
        left: float = 0.0,
        bottom: float = 0.0,
        width: float = 1.0,
        height: float = 1.0,
        velocity_x: float = 0.0,
        velocity_y: float = 0.0,
        gravity_direction_sign: int = 1,
        is_grounded: bool = False,
    ):
        self.left = left                            # AABB 左边
        self.bottom = bottom                        # AABB 下边
        self.width = width                          # 宽，整格倍数
        self.height = height                        # 高，整格倍数
        self.velocity_x = velocity_x                # 方块/秒
        self.velocity_y = velocity_y                # 方块/秒
        self.gravity_direction_sign = gravity_direction_sign  # +1 向下，-1 向上
        self.is_grounded = is_grounded              # 每步由碰撞解算写入

    @property
    def top(self) -> float:
        return self.bottom + self.height

    @property
    def right(self) -> float:
        return self.left + self.width
