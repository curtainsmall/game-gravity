"""Controller：运动部件。

有 source 的就按来源推进（玩家输入）；没有 source 的可移动方块按 offset 由触发事件驱动，
具体推进由 ControllerSystem 负责（原点、进度都记在系统里）。
"""


class Controller:
    def __init__(
        self,
        source=None,
        offset: tuple[float, float] = (0.0, 0.0),
    ) -> None:
        self.source = source                      # InputSource / None（None = 由触发事件驱动）
        self.offset: tuple[float, float] = (float(offset[0]), float(offset[1]))
        self.passes_through_planks: bool = False
