"""弹道：半隐式欧拉下的上升高度与反解起跳速度。

跳和喷口用的是同一套积分（先减速再位移），所以两处都从这里取速度，
不再预先算好一张表。
"""


def rise_height(velocity: float, gravity: float, delta_seconds: float) -> float:
    """以该初速度向上抛出，在半隐式欧拉下实际能升高多少。"""
    speed, height = velocity, 0.0
    while speed > 0.0:
        speed -= gravity * delta_seconds
        height += speed * delta_seconds
    return height


def launch_speed(height: float, gravity: float, delta_seconds: float) -> float:
    """反解：要让抛物线正好升高 height，初速度取多少。"""
    if height <= 0.0 or gravity <= 0.0:
        return 0.0
    low, high = 0.0, 1.0
    while rise_height(high, gravity, delta_seconds) < height:
        high *= 2.0
        if high > 10000.0:
            return high
    for _ in range(60):
        middle = (low + high) / 2.0
        if rise_height(middle, gravity, delta_seconds) < height:
            low = middle
        else:
            high = middle
    return high
