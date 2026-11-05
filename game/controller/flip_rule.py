"""翻转规则：玩家脚边落在翻转带里才能翻转重力。纯函数，可单独测试。

翻转带由关卡数据的 flip_area_offsets 给出，两个数都是带子的高度：
向上翻的带子贴着关卡顶，是 [关卡高度 - 偏移, 关卡高度)；向下翻的带子贴着关卡底，
是 [0, 偏移)。脚边（重力向下取下边，重力向上取上边）落在带子里才翻得动。
偏移是 0 就是空带子，这一侧永远翻不了。
"""

# 关卡没写 flip_area_offsets 时的默认值：两条空带子，哪儿都翻不了
FLIP_AREA_OFFSETS_DEFAULT = (0.0, 0.0)


def foot_edge_height(body) -> float:
    """脚边的高度：重力向下取下边，重力向上取上边。"""
    if body.gravity_direction_sign > 0:
        return body.bottom
    return body.bottom + body.height


def flip_area(level_height: float, offsets, upward: bool) -> tuple[float, float]:
    """翻转带的下界和上界：向上翻贴着关卡顶，向下翻贴着关卡底。"""
    if upward:
        return level_height - float(offsets[0]), level_height
    return 0.0, float(offsets[1])


def can_flip_gravity(body, level_height: float, offsets=FLIP_AREA_OFFSETS_DEFAULT) -> bool:
    """此刻是否允许翻转：脚边要落在当前重力方向的翻转带里。"""
    upward = body.gravity_direction_sign > 0
    low, high = flip_area(level_height, offsets, upward)
    return low <= foot_edge_height(body) < high


def flip_gravity(body, controller) -> None:
    """翻转重力：加速度方向取反，木板穿透置真。"""
    body.gravity_direction_sign = -body.gravity_direction_sign
    controller.passes_through_planks = True
