"""翻转规则：玩家离关卡顶部够远才能翻转重力。纯函数，可单独测试。

翻转区由关卡数据里的 flip_area_offsets 给出，两个数都是「离关卡顶多少格」：
第一个是向上翻的起点，第二个是向下翻的起点。翻转区从那个起点往下一直到底，
所以脚边比起点更靠近天花板时翻不了。
"""

# 关卡没写 flip_area_offsets 时的默认值：两个方向都不设限
FLIP_AREA_OFFSETS_DEFAULT = (0.0, 0.0)


def foot_edge_from_top(body, level_height: float) -> float:
    """脚边离关卡顶多少格：重力向下取下边，重力向上取上边。"""
    edge_y = body.bottom if body.gravity_direction_sign > 0 else body.bottom + body.height
    return level_height - edge_y


def flip_area_offset(body, offsets=FLIP_AREA_OFFSETS_DEFAULT) -> float:
    """当前重力方向对应的翻转区起点（离关卡顶的格数）。"""
    index = 0 if body.gravity_direction_sign > 0 else 1
    return float(offsets[index])


def can_flip_gravity(body, level_height: float, offsets=FLIP_AREA_OFFSETS_DEFAULT) -> bool:
    """此刻是否允许翻转：脚边要落在当前重力方向的翻转区里。"""
    return foot_edge_from_top(body, level_height) >= flip_area_offset(body, offsets)


def flip_gravity(body, controller) -> None:
    """翻转重力：加速度方向取反，木板穿透置真。"""
    body.gravity_direction_sign = -body.gravity_direction_sign
    controller.passes_through_planks = True
