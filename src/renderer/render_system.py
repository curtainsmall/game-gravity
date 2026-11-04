"""RenderSystem：按 RenderSpec 绘制所有 GameObject，跟随镜头滚动。"""

import pygame

from core.game_object import GameObject
from renderer.render_spec import PlaceholderShape
from renderer.viewport import ViewMode, Viewport
from world.world import World


class RenderSystem:
    def __init__(self) -> None:
        self.viewport: Viewport = Viewport()

    def update(
        self,
        objects: list[GameObject],
        world: World | None,
        surface: pygame.Surface,
        focus_x: float | None = None,
        view_mode: ViewMode = ViewMode.VERTICAL_EXPAND,
    ) -> None:
        if world is None:
            return
        self.viewport.mode = view_mode
        self.viewport.fit(world, surface)
        self.viewport.follow(focus_x, world, surface)
        for game_object in objects:
            body = game_object.body
            render = game_object.render
            if body is None or render is None:
                continue
            rect = self.viewport.to_screen_rect(body, world)
            if render.placeholder_has_axis:
                self._dotted_axis(surface, rect, render.placeholder_color)
            if render.placeholder_shape == PlaceholderShape.TRIANGLE:
                self._triangle(surface, rect, render)
            else:
                self._fill(surface, rect, render.placeholder_color)

    def _fill(self, surface: pygame.Surface, rect: pygame.Rect, color: tuple[int, int, int, int]) -> None:
        """alpha 小于 255 时走混合路径，否则直接画不透明矩形。"""
        if len(color) == 4 and color[3] < 255:
            layer = pygame.Surface(rect.size, pygame.SRCALPHA)
            layer.fill(color)
            surface.blit(layer, rect.topleft)
        else:
            pygame.draw.rect(surface, tuple(color[:3]), rect)

    @staticmethod
    def _dotted_axis(surface: pygame.Surface, rect: pygame.Rect, color: tuple[int, int, int, int]) -> None:
        """沿 rect 竖直中轴画虚线，用来指示风区的中线。"""
        step = max(4, round(rect.width * 0.25))
        dash = max(2, step // 2)
        x = rect.centerx
        y = rect.top
        while y < rect.bottom:
            pygame.draw.line(surface, tuple(color[:3]), (x, y), (x, min(y + dash, rect.bottom)))
            y += step

    @staticmethod
    def _triangle(surface: pygame.Surface, rect: pygame.Rect, render) -> None:
        """等腰三角形：底边中点落在对象近端，尖端朝吹风方向。"""
        width_ratio, height_ratio = render.placeholder_size_in_blocks
        height = rect.width * (height_ratio / width_ratio if width_ratio else 1.0)
        half_width = rect.width / 2.0
        center_x = rect.centerx
        if render.placeholder_direction >= 0:
            base_y = rect.bottom
            apex_y = base_y - height
        else:
            base_y = rect.top
            apex_y = base_y + height
        points = [
            (center_x - half_width, base_y),
            (center_x + half_width, base_y),
            (center_x, apex_y),
        ]
        pygame.draw.polygon(surface, tuple(render.placeholder_color[:3]), points)
