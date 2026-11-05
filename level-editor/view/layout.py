"""Layout：屏幕坐标与关卡格子互换，带缩放和平移。"""

import pygame

from core.constants import (
    BAND_PIXEL_HEIGHT,
    COLS,
    FOOTER,
    HEADER,
    MARGIN,
    ROWS,
    RULER_HEIGHT,
    ZOOM_MAX_TILE,
)


class Layout:
    def __init__(
        self,
        window_size: tuple,
        zoom: float | None = None,
        pan_x: float = 0.0,
        pan_y: float = 0.0,
        reserved_right: int = 0,
        cols: int = COLS,
        rows: int = ROWS,
    ) -> None:
        width, height = window_size
        self.window = (width, height)
        self.cols = max(1, int(cols))    # 关卡自己的宽度，格
        self.rows = max(1, int(rows))    # 关卡自己的高度，格
        self.usable_width = max(1, width - 2 * MARGIN - reserved_right)
        self.usable_height = max(1, height - HEADER - FOOTER)
        # 底部留一条刻度，所以可用高度要先扣掉它
        self.min_tile = min(
            self.usable_width / self.cols,
            max(1.0, self.usable_height - RULER_HEIGHT) / (self.rows + 2),
        )
        # 游戏比例：可玩行铺满 400px，和游戏里看到的一致。行数多时它比缩放上限还大，
        # 所以上限要把它一起算进来，否则默认值会被夹小、就不再和游戏 1:1 了。
        self.game_tile = BAND_PIXEL_HEIGHT / self.rows
        self.max_tile = max(ZOOM_MAX_TILE, self.game_tile, self.min_tile)
        wanted = self.game_tile if zoom is None else zoom
        self.tile = min(max(wanted, self.min_tile), self.max_tile)
        self.zoom = zoom
        self.width = self.tile * self.cols
        self.height = self.tile * (self.rows + 2) + RULER_HEIGHT
        self.max_pan_x = max(0.0, self.width - self.usable_width)
        self.max_pan_y = max(0.0, self.height - self.usable_height)
        self.pan_x = min(max(0.0, pan_x), self.max_pan_x)
        self.pan_y = min(max(0.0, pan_y), self.max_pan_y)
        self.left = MARGIN - self.pan_x
        self.top = HEADER - self.pan_y + max(0.0, (self.usable_height - self.height) / 2.0)

    def cell_at(self, position: tuple) -> tuple | None:
        x, y = position
        if not (0 <= x < self.window[0] and HEADER <= y < self.window[1] - FOOTER):
            return None
        if not (self.left <= x < self.left + self.width and self.top <= y < self.top + self.height):
            return None
        col = int((x - self.left) // self.tile)
        screen_row = int((y - self.top) // self.tile)
        level_y = self.rows - screen_row
        if not (0 <= col < self.cols) or not (0 <= level_y < self.rows):
            return None
        return col, level_y

    def level_point(self, position: tuple) -> tuple:
        """屏幕坐标 → 关卡连续坐标（喷口这类「点」对象用它定位）。"""
        return (
            (position[0] - self.left) / self.tile,
            self.rows + 1 - (position[1] - self.top) / self.tile,
        )

    def world_rect(self, x: float, y: float, width: float, height: float) -> pygame.Rect:
        """自由矩形（左下角 + 宽高，单位格，可小数）→ 屏幕矩形。

        贴图这类不吸格子的对象用它；别套 cell_rect，那里的 (size - 1) 是给整数格留的补偿。
        """
        return pygame.Rect(
            round(self.left + x * self.tile),
            round(self.top + (self.rows - (y + height)) * self.tile),
            max(1, round(width * self.tile)),
            max(1, round(height * self.tile)),
        )

    def world_point(self, position: tuple) -> tuple:
        """屏幕坐标 → 世界连续坐标（左下角为原点，y 向上，单位格）。"""
        return (
            (position[0] - self.left) / self.tile,
            self.rows - (position[1] - self.top) / self.tile,
        )

    def cell_rect(self, x: float, y: float, size: tuple = (1, 1)) -> pygame.Rect:
        left = self.left + (x - 0.5 if size[0] < 1 else x) * self.tile
        top = self.top + (self.rows - y - (size[1] - 1)) * self.tile
        return pygame.Rect(
            round(left),
            round(top),
            max(1, round(size[0] * self.tile)),
            max(1, round(size[1] * self.tile)),
        )

    def entry_rect(self, entry: dict) -> pygame.Rect:
        return self.cell_rect(entry["pos"][0], entry["pos"][1], tuple(entry.get("size", [1, 1])))
