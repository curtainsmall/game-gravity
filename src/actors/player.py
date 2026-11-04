"""Player：玩家。唯一的行动者。"""

import math

from core.body import Body

# 允许翻转的脚边行区间，键为重力方向符号
ALLOWED_FLIP_ROWS_BY_GRAVITY_DIRECTION: dict[int, tuple[int, int]] = {
    1: (4, 7),    # 重力向下：脚边在 4–7 行，翻转为向上
    -1: (0, 3),   # 重力向上：脚边在 0–3 行，翻转为向下
}


class Player:
    def __init__(self, collision_body: Body | None = None, spawn_cell_position=(0, 0)):
        self.collision_body = collision_body if collision_body is not None else Body()
        self.spawn_cell_position = spawn_cell_position
        self.passes_through_planks = False

    def foot_edge_row(self) -> int:
        """脚边所在行：重力向下取下边，重力向上取上边。"""
        body = self.collision_body
        edge_height = body.bottom if body.gravity_direction_sign > 0 else body.bottom + body.height
        return math.floor(edge_height)

    def can_flip_gravity(self) -> bool:
        """此刻是否允许翻转：脚边行落在当前重力方向的允许区间内。"""
        lowest_allowed_row, highest_allowed_row = ALLOWED_FLIP_ROWS_BY_GRAVITY_DIRECTION[
            self.collision_body.gravity_direction_sign
        ]
        return lowest_allowed_row <= self.foot_edge_row() <= highest_allowed_row

    def flip_gravity(self) -> None:
        """翻转重力：加速度方向取反，木板穿透置真。"""
        self.collision_body.gravity_direction_sign = -self.collision_body.gravity_direction_sign
        self.passes_through_planks = True

    def advance(self, delta_seconds: float, world) -> None:
        """读输入、水平移动、施加重力。输入接入后补第一个参数。"""

    def settle(self) -> None:
        """收尾：落地后清除木板穿透。"""
        if self.collision_body.is_grounded:
            self.passes_through_planks = False
