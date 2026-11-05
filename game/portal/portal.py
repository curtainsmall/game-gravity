"""Portal：传送门数据。

pos/size 就是门本身，也是触发区：踩到这块矩形就传送，没有额外的范围。
target 是另一个门的名字。玩家从目标门出来之后，目标门在玩家离开它之前不再触发，
所以不会来回弹。
"""

PORTAL_EXIT_DISTANCE = 0.5          # 从目标门出来时沿门的朝向挪开这么多格

FACE_DIRECTIONS = {
    "up": (0.0, 1.0),
    "right": (1.0, 0.0),
    "down": (0.0, -1.0),
    "left": (-1.0, 0.0),
}


def exit_offset(face: str) -> tuple[float, float]:
    """从朝这个方向的门出来时，往哪个方向挪多远。"""
    step_x, step_y = FACE_DIRECTIONS.get(str(face), FACE_DIRECTIONS["up"])
    return step_x * PORTAL_EXIT_DISTANCE, step_y * PORTAL_EXIT_DISTANCE


class Portal:
    def __init__(self, target: str = "", face: str = "up") -> None:
        self.target: str = target          # 目标门的名字，空串表示不传送
        self.face: str = face              # 朝向：出来时沿这个方向挪一点
