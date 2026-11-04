"""MovableBlock：可移动方块。位移由所属驱动组给出。"""

from core.body import Body


class MovableBlock:
    def __init__(
        self,
        collision_body: Body | None = None,
        offset_from_group_origin: tuple[float, float] = (0.0, 0.0),
        driver_group_identifier: str = "",
        is_passable_while_flip_flag_set: bool = False,
    ):
        self.collision_body = collision_body if collision_body is not None else Body()
        self.offset_from_group_origin = offset_from_group_origin    # 单位：方块，连续值
        self.driver_group_identifier = driver_group_identifier
        self.is_passable_while_flip_flag_set = is_passable_while_flip_flag_set  # 是否受翻转 flag 控制

    def advance(self, delta_seconds: float) -> None:
        """把所属驱动组给出的位移写回 collision_body。"""
