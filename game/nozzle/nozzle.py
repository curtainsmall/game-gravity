"""Nozzle：风区数据。

power 是目标位置相对喷口的偏移：正数向上，负数向下。
range 是风区的长度：推人只发生在这一段内，之后靠惯性飞行。
两者都是浮点，可以不是整格。
"""


class Nozzle:
    def __init__(self, power: float, length: float, origin_y: float) -> None:
        self.power: float = power        # 目标偏移，单位方块
        self.length: float = length      # 风区长度，单位方块
        self.origin_y: float = origin_y  # 喷口位置（风区近端）

    @property
    def target_y(self) -> float:
        return self.origin_y + self.power

    @property
    def wind_bottom(self) -> float:
        return self.origin_y if self.power >= 0 else self.origin_y - self.length
