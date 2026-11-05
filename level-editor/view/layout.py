"""Layout：屏幕坐标与关卡世界坐标互换，带缩放和平移。

世界坐标：x 向右、y 向上，单位是格（可以是小数）。关卡可玩区是 y ∈ [0, rows]，
上面还有天花板那一行、下面是地面那一行，所以一条带子共 rows + 2 行。

所有对象都按浮点自由矩形摆放：画和命中一律走 world_rect / world_point；
网格只是画出来的参考线，按住 Shift 时才用 snap_point / snap_rect 对齐。
"""

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

    # ---- 世界坐标（所有对象都用这个） -------------------------------
    def world_rect(self, x: float, y: float, width: float, height: float) -> pygame.Rect:
        """世界矩形（左下角 + 宽高，单位格，可小数）→ 屏幕矩形。"""
        return pygame.Rect(
            round(self.left + x * self.tile),
            round(self.top + (self.rows + 1 - (y + height)) * self.tile),
            max(1, round(width * self.tile)),
            max(1, round(height * self.tile)),
        )

    def world_point(self, position: tuple) -> tuple:
        """屏幕坐标 → 世界连续坐标（左下角为原点，y 向上，单位格）。"""
        return (
            (position[0] - self.left) / self.tile,
            self.rows + 1 - (position[1] - self.top) / self.tile,
        )

    def entry_rect(self, entry: dict) -> pygame.Rect:
        size = entry.get("size", [1.0, 1.0])
        return self.world_rect(entry["pos"][0], entry["pos"][1], size[0], size[1])

    # ---- 网格吸附 ---------------------------------------------------
    def snap_rect(self, x: float, y: float, width: float, height: float) -> tuple:
        """把一个浮点矩形对到整格：左下与右上各自取整。"""
        left, right = round(x), round(x + width)
        bottom, top = round(y), round(y + height)
        return float(left), float(bottom), float(max(1, right - left)), float(max(1, top - bottom))

    def snap_point(self, x: float, y: float) -> tuple:
        """把一个点对到整格线上。"""
        return float(round(x)), float(round(y))
