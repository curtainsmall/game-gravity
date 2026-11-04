"""Item：道具数据。"""


class Item:
    def __init__(self, heavy: bool = False) -> None:
        self.heavy: bool = heavy     # 变重：跳速降一档
        self.consumed: bool = False  # 已被拾取，效果不再重复
