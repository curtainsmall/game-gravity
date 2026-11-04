"""Body：碰撞体部件。纯数据。"""


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
        is_sensor: bool = False,
        is_static: bool = False,
    ):
        self.left = left
        self.bottom = bottom
        self.width = width
        self.height = height
        self.velocity_x = velocity_x
        self.velocity_y = velocity_y
        self.gravity_direction_sign = gravity_direction_sign  # +1 向下，-1 向上
        self.is_grounded = is_grounded
        self.is_sensor = is_sensor                            # 参与重叠检测，不参与解算
        self.is_static = is_static                            # 参与碰撞，不被积分

    @property
    def top(self) -> float:
        return self.bottom + self.height

    @property
    def right(self) -> float:
        return self.left + self.width
