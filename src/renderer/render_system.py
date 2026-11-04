"""RenderSystem：按部件绘制对象。本阶段不做绘制。"""

import pygame

from core.game_object import GameObject


class RenderSystem:
    def update(self, objects: list[GameObject], surface: pygame.Surface) -> None:
        """绘制目标接入后：遍历有 render 的对象，按 body 位置画占位图形或贴图。"""
