"""Viewport：纵向铺满时沿 x 滚动；横向铺满时整关可见。"""

from enum import StrEnum

import pygame

from renderer.coordinates import body_to_screen_rect, total_row_count
from world.world import World


class ViewMode(StrEnum):
    VERTICAL_EXPAND = "vertical_expand"      # 十行铺满窗口高，横向滚动
    HORIZONTAL_EXPAND = "horizontal_expand"  # 一百二十列铺满窗口宽，整关可见


class Viewport:
    def __init__(self) -> None:
        self.mode: ViewMode = ViewMode.VERTICAL_EXPAND
        self.pixels_per_tile: float = 1.0
        self.left_in_blocks: float = 0.0
        self.origin_y: float = 0.0

    def fit(self, world: World, surface: pygame.Surface) -> None:
        if self.mode == ViewMode.HORIZONTAL_EXPAND:
            self.pixels_per_tile = surface.get_width() / world.width_in_blocks
        else:
            self.pixels_per_tile = surface.get_height() / total_row_count(world)
        band_height = total_row_count(world) * self.pixels_per_tile
        self.origin_y = (surface.get_height() - band_height) / 2.0

    def follow(self, center_x: float | None, world: World, surface: pygame.Surface) -> None:
        if self.mode == ViewMode.HORIZONTAL_EXPAND or center_x is None:
            self.left_in_blocks = 0.0
            return
        visible_in_blocks = surface.get_width() / self.pixels_per_tile
        max_left = max(0.0, world.width_in_blocks - visible_in_blocks)
        self.left_in_blocks = min(max(center_x - visible_in_blocks / 2.0, 0.0), max_left)

    def to_screen_rect(self, body, world: World) -> pygame.Rect:
        return body_to_screen_rect(
            body,
            self.pixels_per_tile,
            self.left_in_blocks,
            total_row_count(world),
            self.origin_y,
        )
