"""RenderSystem：按 RenderSpec 绘制所有 GameObject，跟随镜头滚动。"""

import pygame

from core.game_object import GameObject
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
            self._fill(surface, rect, render.placeholder_color)

    @staticmethod
    def _fill(surface: pygame.Surface, rect: pygame.Rect, color: tuple[int, int, int, int]) -> None:
        """alpha 小于 255 时走混合路径，否则直接画不透明矩形。"""
        if len(color) == 4 and color[3] < 255:
            layer = pygame.Surface(rect.size, pygame.SRCALPHA)
            layer.fill(color)
            surface.blit(layer, rect.topleft)
        else:
            pygame.draw.rect(surface, tuple(color[:3]), rect)
