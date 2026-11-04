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
            pygame.draw.rect(surface, render.placeholder_color, rect)
