"""Item：道具数据。"""


class Item:
    def __init__(self, jump_offset: float = 0.0) -> None:
        # 拾取后跳高加多少格：正数跳更高、负数跳更低、0 不变
        self.jump_offset: float = float(jump_offset)
        self.consumed: bool = False  # 已被拾取，效果不再重复
