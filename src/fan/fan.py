"""Fan：风区数据。

power 是相对风扇位置的纵向偏移：正数向上吹，负数向下吹。
风区是以风扇为近端、长 |power| 格的矩形。
"""


class Fan:
    WIND_SPEED = 8.0   # 风区内的最小推速，方块/秒

    def __init__(self, power: int, origin_y: float) -> None:
        self.power: int = power          # 目标偏移，单位方块，正负决定方向
        self.origin_y: float = origin_y  # 风扇位置（风区近端）

    @property
    def target_y(self) -> float:
        return self.origin_y + self.power

    @property
    def length(self) -> int:
        return abs(self.power)
