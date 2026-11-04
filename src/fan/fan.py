"""Fan：风区数据。

power 是目标位置相对风扇的偏移：正数向上，负数向下。
range 是风区的长度：推人只发生在这一段内，之后靠惯性飞行。
"""


class Fan:
    def __init__(self, power: int, length: int, origin_y: float) -> None:
        self.power: int = power          # 目标偏移，单位方块
        self.length: int = length        # 风区长度，单位方块
        self.origin_y: float = origin_y  # 风扇位置（风区近端）

    @property
    def target_y(self) -> float:
        return self.origin_y + self.power

    @property
    def wind_bottom(self) -> float:
        return self.origin_y if self.power >= 0 else self.origin_y - self.length


def rise_height(velocity: float, gravity: float, delta_seconds: float) -> float:
    """半隐式欧拉下，以该初速度向上抛出的实际上升高度。"""
    speed, height = velocity, 0.0
    while speed > 0.0:
        speed -= gravity * delta_seconds
        height += speed * delta_seconds
    return height


def launch_speed(height: float, gravity: float, delta_seconds: float) -> float:
    """反解：要让抛物线正好升高 height，初速度取多少。"""
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
