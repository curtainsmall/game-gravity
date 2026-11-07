"""Item：道具数据。

道具自己也是一个触发来源：玩家和它重叠就算触发。
    mode         once    第一次触发后就禁用，永远不再触发；跳高加成一直保留
                 persist 可重复触发：离开就撤销加成，再进来算一次新触发
    jump_offset  触发期间给玩家的跳高加成（格，正数跳更高、负数更低、0 不变）
triggered 是“现在算不算触发中”，也是触发卡片眼里的“按下”；disabled 只对 once 有意义。
"""

MODE_ONCE = "once"
MODE_PERSIST = "persist"
ITEM_MODES = (MODE_ONCE, MODE_PERSIST)
DEFAULT_MODE = MODE_ONCE


class Item:
    def __init__(self, mode: str = DEFAULT_MODE, jump_offset: float = 0.0) -> None:
        self.mode: str = mode if mode in ITEM_MODES else DEFAULT_MODE
        self.jump_offset: float = float(jump_offset)
        self.triggered: bool = False   # 现在算不算触发中（触发卡片的“按下”）
        self.disabled: bool = False    # once 触发过以后就是禁用状态，不再触发
