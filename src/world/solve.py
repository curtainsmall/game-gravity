"""碰撞解算。玩家与边界、静态网格、可移动方块之间。"""


def solve_collisions(player, world) -> None:
    """解算玩家碰撞：写入 is_grounded，解除穿透，把平台位移施加给玩家。"""
