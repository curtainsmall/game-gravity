"""世界坐标（方块单位，浮点）到屏幕像素的映射。"""

import pygame


def total_row_count(world) -> int:
    """可玩行数加上地面与天花板各一行。"""
    return world.height_in_blocks + 2


def body_to_screen_rect(
    body,
    pixels_per_tile: float,
    camera_left: float,
    total_rows: int,
    origin_y: float = 0.0,
) -> pygame.Rect:
    """body 的 y 向上，屏幕 y 向下；相机只沿 x 移动。"""
    left = (body.left - camera_left) * pixels_per_tile
    top = origin_y + (total_rows - 1 - (body.bottom + body.height)) * pixels_per_tile
    width = body.width * pixels_per_tile
    height = body.height * pixels_per_tile
    return pygame.Rect(round(left), round(top), max(1, round(width)), max(1, round(height)))
