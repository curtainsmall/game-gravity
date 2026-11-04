"""Fan：风区数据与起跳速度的调校。

power 是相对风扇位置的纵向偏移：正数向上吹，负数向下吹。
风区是以风扇为近端、长 |power| 格的矩形。
"""


class Fan:
    def __init__(self, power: int, origin_y: float) -> None:
        self.power: int = power          # 目标偏移，单位方块，正负决定方向
        self.origin_y: float = origin_y  # 风扇位置（风区近端）

    @property
    def target_y(self) -> float:
        return self.origin_y + self.power

    @property
    def length(self) -> int:
        return abs(self.power)


def rise_height(velocity: float, gravity: float, delta_seconds: float) -> float:
    """半隐式欧拉下，以该初速度向上抛出的实际上升高度。"""
    speed, height = velocity, 0.0
    while speed > 0.0:
        speed -= gravity * delta_seconds
        height += speed * delta_seconds
    return height


def launch_speed(height: float, gravity: float, delta_seconds: float) -> float:
    """反解：要让半隐式欧拉的抛物线正好升高 height，初速度取多少。"""
    if height <= 0.0 or gravity <= 0.0:
        return 0.0
    low, high = 0.0, 1.0
    while rise_height(high, gravity, delta_seconds) < height:
        high *= 2.0
        if high > 10000.0:
            return high
    for _ in range(60):
        middle = (low + high) / 2.0
        if rise_height(middle, gravity, delta_seconds) < height:
            low = middle
        else:
            high = middle
    return high
