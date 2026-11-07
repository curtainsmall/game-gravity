"""TriggerSource：按钮和道具合并后的「触发源」数据。

一块矩形区域，玩家压在上面就算被按下；模式决定这个「按下」怎么记：
    hold  压着才算，松开就撤销
    once  第一次压到之后一直算按下，之后不再变
jump_offset 是按下期间对玩家跳高的变化（格）：0 表示只是开关，非 0 就是原来的道具
效果；多个触发源同时生效会叠加，撤销时各减各的。
按下状态由 TriggerSourceSystem 每帧写好，TriggerSystem 读它来决定卡片生不生效。
"""

MODE_HOLD = "hold"
MODE_ONCE = "once"
MODES = (MODE_HOLD, MODE_ONCE)
DEFAULT_MODE = MODE_HOLD


class TriggerSource:
    def __init__(self, mode: str = DEFAULT_MODE, jump_offset: float = 0.0) -> None:
        self.mode: str = mode if mode in MODES else DEFAULT_MODE
        self.jump_offset: float = float(jump_offset)
        self.pressed: bool = False     # 现在算不算按下（TriggerSystem 读）
        self.engaged: bool = False     # 跳高加成现在加上了没有
