"""Nozzle：风区数据。

pos 是风区底面的中点，face 是风区伸出的方向（up/right/down/left），
power 是目标沿这个方向离 pos 多远，不能为负。
风区的宽高就是 body 的宽高，不再单独记 range。
"""

FACE_VECTORS = {
    "up": (0.0, 1.0),
    "right": (1.0, 0.0),
    "down": (0.0, -1.0),
    "left": (-1.0, 0.0),
}


class Nozzle:
    def __init__(self, face: str = "up", power: float = 0.0, origin=(0.0, 0.0)) -> None:
        self.face: str = face
        self.power: float = max(0.0, float(power))   # 目标离底面中点多远，不给负的
        self.origin: tuple[float, float] = (float(origin[0]), float(origin[1]))

    @property
    def axis(self) -> tuple[float, float]:
        """风区伸出的单位向量。"""
        return FACE_VECTORS.get(str(self.face), FACE_VECTORS["up"])

    @property
    def vertical(self) -> bool:
        """风区是不是竖着的（up/down 才往上下推）。"""
        return self.axis[1] != 0.0

    @property
    def target(self) -> tuple[float, float]:
        """目标点：底面中点沿 face 走出去 power 格。"""
        step_x, step_y = self.axis
        return (
            self.origin[0] + step_x * self.power,
            self.origin[1] + step_y * self.power,
        )
