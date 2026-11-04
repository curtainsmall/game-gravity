"""Mover：机关部件。成组移动，由触发者状态驱动。纯数据。"""


class Mover:
    def __init__(
        self,
        offset_from_group_origin: tuple[float, float] = (0.0, 0.0),
        driver_group_identifier: str = "",
        triggered_by=None,
        is_passable_while_flip_flag_set: bool = False,
    ):
        self.offset_from_group_origin = offset_from_group_origin    # 单位：方块，连续值
        self.driver_group_identifier = driver_group_identifier
        self.triggered_by = triggered_by                            # 引用触发它的对象
        self.is_passable_while_flip_flag_set = is_passable_while_flip_flag_set
