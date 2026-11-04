"""Viewport：只沿 x 滚动，垂直方向整关铺满窗口。"""

import pygame

from renderer.coordinates import body_to_screen_rect, total_row_count
from world.world import World


class Viewport:
    def __init__(self) -> None:
        self.pixels_per_tile: float = 1.0
        self.left_in_blocks: float = 0.0

    def fit(self, world: World, surface: pygame.Surface) -> None:
        """每格像素由「窗口高 / 总行数」决定，10 行正好铺满。"""
        self.pixels_per_tile = surface.get_height() / total_row_count(world)

    def follow(self, center_x: float | None, world: World, surface: pygame.Surface) -> None:
        """把关注点居中，并夹在关卡左右边界内。"""
        visible_in_blocks = surface.get_width() / self.pixels_per_tile
        max_left = max(0.0, world.width_in_blocks - visible_in_blocks)
        if center_x is None:
            self.left_in_blocks = 0.0
            return
        self.left_in_blocks = min(max(center_x - visible_in_blocks / 2.0, 0.0), max_left)

    def to_screen_rect(self, body, world: World) -> pygame.Rect:
        return body_to_screen_rect(
            body,
            self.pixels_per_tile,
            self.left_in_blocks,
            total_row_count(world),
        )
