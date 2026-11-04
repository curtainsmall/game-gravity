"""翻转规则：玩家所在行决定能否翻转重力。纯函数，可单独测试。"""

import math

# 允许翻转的脚边行区间，键为重力方向符号
ALLOWED_FLIP_ROWS_BY_GRAVITY_DIRECTION: dict[int, tuple[int, int]] = {
    1: (4, 7),    # 重力向下：脚边在 4–7 行，翻转为向上
    -1: (0, 3),   # 重力向上：脚边在 0–3 行，翻转为向下
}


def foot_edge_row(body) -> int:
    """脚边所在行：重力向下取下边，重力向上取上边。"""
    edge_height = body.bottom if body.gravity_direction_sign > 0 else body.bottom + body.height
    return math.floor(edge_height)


def can_flip_gravity(body) -> bool:
    """此刻是否允许翻转：脚边行落在当前重力方向的允许区间内。"""
    lowest_allowed_row, highest_allowed_row = ALLOWED_FLIP_ROWS_BY_GRAVITY_DIRECTION[
        body.gravity_direction_sign
    ]
    return lowest_allowed_row <= foot_edge_row(body) <= highest_allowed_row


def flip_gravity(body, controller) -> None:
    """翻转重力：加速度方向取反，木板穿透置真。"""
    body.gravity_direction_sign = -body.gravity_direction_sign
    controller.passes_through_planks = True
