"""翻转规则：玩家的 AABB 和翻转带重叠才能翻转重力。纯函数，可单独测试。

翻转带由关卡数据的 flip_area_offsets 给出，两个数都是带子的高度：
向上翻的带子贴着关卡顶，是 [关卡高度 - 偏移, 关卡高度)；向下翻的带子贴着关卡底，
是 [0, 偏移)。玩家整块矩形（不只脚边一个点）和带子有重叠才翻得动：站进带子里、
或者往上跳的时候刚碰到带子都算。偏移是 0 就是空带子，这一侧永远翻不了。
"""

# 关卡没写 flip_area_offsets 时的默认值：两条空带子，哪儿都翻不了
FLIP_AREA_OFFSETS_DEFAULT = (0.0, 0.0)


def flip_area(level_height: float, offsets, upward: bool) -> tuple[float, float]:
    """翻转带的下界和上界：向上翻贴着关卡顶，向下翻贴着关卡底。"""
    if upward:
        return level_height - float(offsets[0]), level_height
    return 0.0, float(offsets[1])


def can_flip_gravity(body, level_height: float, offsets=FLIP_AREA_OFFSETS_DEFAULT) -> bool:
    """此刻是否允许翻转：玩家的整块 AABB 和当前重力方向的翻转带重叠。"""
    upward = body.gravity_direction_sign > 0
    low, high = flip_area(level_height, offsets, upward)
    if high <= low:
        return False                     # 空带子：这一侧永远翻不了
    return body.bottom < high and body.top > low


def flip_gravity(body) -> None:
    """翻转重力：加速度方向取反，并允许这一趟穿过木板（落地且离开木板后由物理系统清掉）。"""
    body.gravity_direction_sign = -body.gravity_direction_sign
    body.is_flipping = True
