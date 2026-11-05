"""Viewport：纵向铺满时沿 x 滚动；横向铺满时整关可见。

纵向铺满分格不看窗口高度：可玩行（0 到 height_in_blocks）恒定 BAND_PIXEL_HEIGHT
像素高，行数变了就变格子大小。背景图按这个像素高度画，且只铺可玩区——地面行和
天花板行都在背景之外，所以关卡改高改矮都不用重画背景。
"""

from enum import StrEnum

import pygame

from renderer.coordinates import body_to_screen_rect, total_row_count
from world.world import World

BAND_PIXEL_HEIGHT = 400.0  # 背景图高度：只量可玩行，地面和天花板在它外面


class ViewMode(StrEnum):
    VERTICAL_EXPAND = "vertical_expand"      # 可玩区固定 400px 高，横向滚动
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
            # 400 只摊在可玩行上：行数只影响每格多大，可玩区总高不变，
            # 地面行和天花板行各再占一格，落在背景外侧
            self.pixels_per_tile = BAND_PIXEL_HEIGHT / max(1, world.height_in_blocks)
        band_height = total_row_count(world) * self.pixels_per_tile
        self.origin_y = (surface.get_height() - band_height) / 2.0  # 多出来的高度上下均分

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

    def playable_rect(self, world: World) -> pygame.Rect:
        """可玩区（0..width, 0..height 格）在屏幕上的矩形：贴图超出这块就裁掉。"""
        tile = self.pixels_per_tile
        return pygame.Rect(
            round(-self.left_in_blocks * tile),
            round(self.origin_y + tile),
            max(1, round(world.width_in_blocks * tile)),
            max(1, round(world.height_in_blocks * tile)),
        )
