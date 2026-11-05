"""Portal：传送门数据。

pos/size 是画出来的那块门，range 是触发区的宽高（以门的中心为中心），
target 是另一个门的名字。玩家从目标门出来之后，目标门在玩家离开它的触发区
之前不再触发，所以不会来回弹。
"""

PORTAL_DEFAULT_RANGE = (1.0, 0.3)   # 没写 range 时：触发区就是画出来的那块门
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
    def __init__(self, target: str = "", face: str = "up", range_size=PORTAL_DEFAULT_RANGE) -> None:
        self.target: str = target          # 目标门的名字，空串表示不传送
        self.face: str = face              # 朝向：出来时沿这个方向挪一点
        self.range_size: tuple[float, float] = (float(range_size[0]), float(range_size[1]))

    def trigger_bounds(self, body) -> tuple[float, float, float, float]:
        """触发区（left, bottom, right, top）：以门的中心为中心。"""
        width, height = self.range_size
        center_x = body.left + body.width / 2.0
        center_y = body.bottom + body.height / 2.0
        return (
            center_x - width / 2.0,
            center_y - height / 2.0,
            center_x + width / 2.0,
            center_y + height / 2.0,
        )
