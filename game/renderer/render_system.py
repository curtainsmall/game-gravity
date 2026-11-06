"""RenderSystem：按 RenderSpec 绘制所有 GameObject，跟随镜头滚动。"""

import math

import pygame

import debug_display
from controller.flip_rule import flip_area
from core.game_object import GameObject, GameObjectKind
from physics.body import Body
from renderer.background import draw_background
from renderer.render_spec import PlaceholderFace, PlaceholderShape
from renderer.texture import draw_missing_texture, load_scaled
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
        debug: bool = False,
        flip_area_offsets=(0.0, 0.0),
    ) -> None:
        if world is None:
            return
        self.viewport.mode = view_mode
        self.viewport.fit(world, surface)
        self.viewport.follow(focus_x, world, surface)
        draw_background(surface, world, self.viewport)
        # 翻转带画在对象下面：标出区域，但不盖住方块和玩家
        if debug:
            self._debug_flip_area(surface, world, flip_area_offsets)
        playable = self.viewport.playable_rect(world)
        for game_object in objects:
            body = game_object.body
            render = game_object.render
            if body is None or render is None:
                continue
            rect = self.viewport.to_screen_rect(body, world)
            if game_object.kind == GameObjectKind.TEXTURE:
                # 贴图是美术，任何时候都画；图找不到时在调试显示里铺黑紫棋盘格
                if not self._texture(surface, rect, render, playable) and debug:
                    draw_missing_texture(surface, rect.clip(playable))
                continue
            # 其余对象只有占位几何体可画，那就是调试显示：没勾就什么都不画
            if not debug:
                continue
            if render.placeholder_has_axis:
                self._dotted_axis(surface, rect, render.placeholder_color)
            self._shape(surface, rect, render)

    @staticmethod
    def _texture(surface: pygame.Surface, rect: pygame.Rect, render, playable: pygame.Rect) -> bool:
        """贴图按世界矩形整张缩放铺上去，超出可玩区的部分裁掉。没图返回 False。"""
        if not render.texture_path:
            return False
        image = load_scaled(render.texture_path, rect.size, render.texture_smooth)
        if image is None:
            return False
        previous = surface.get_clip()
        surface.set_clip(previous.clip(playable))
        surface.blit(image, rect.topleft)
        surface.set_clip(previous)
        return True

    def _shape(self, surface: pygame.Surface, rect: pygame.Rect, render) -> None:
        shape = render.placeholder_shape
        color = tuple(render.placeholder_color[:3])
        if shape == PlaceholderShape.TRIANGLE:
            self._triangle(surface, rect, render)
        elif shape == PlaceholderShape.FRUSTUM:
            self._frustum(surface, rect, render, color)
        elif shape == PlaceholderShape.PENTAGON:
            radius = min(rect.width, rect.height) / 2.0
            center = rect.center
            points = [
                (
                    center[0] + radius * math.cos(math.radians(-90 + 72 * i)),
                    center[1] + radius * math.sin(math.radians(-90 + 72 * i)),
                )
                for i in range(5)
            ]
            pygame.draw.polygon(surface, color, points)
        else:
            self._fill(surface, rect, render.placeholder_color)

    def _frustum(self, surface: pygame.Surface, rect: pygame.Rect, render, color) -> None:
        """棱台：窄端指向 face 方向，占满这块矩形（和传送门一样大，只是形状是梯形）。"""
        pygame.draw.polygon(
            surface, color, self._frustum_points(rect, render.placeholder_face)
        )

    @staticmethod
    def _frustum_points(rect: pygame.Rect, face) -> list:
        """梯形四个点：底面贴着矩形的 face 反面那条边，窄面在对面、缩进 20%。

        不旋转整块矩形——矩形已经是按朝向摆正过的，这里只是把它的边做成梯形。
        """
        name = str(face)
        if name in ("left", "right"):
            inset = max(1.0, rect.height * 0.2)
            far = rect.right if name == "right" else rect.left
            near = rect.left if name == "right" else rect.right
            return [
                (near, rect.top),
                (far, rect.top + inset),
                (far, rect.bottom - inset),
                (near, rect.bottom),
            ]
        inset = max(1.0, rect.width * 0.2)
        far = rect.top if name == "up" else rect.bottom
        near = rect.bottom if name == "up" else rect.top
        return [
            (rect.left, near),
            (rect.right, near),
            (rect.right - inset, far),
            (rect.left + inset, far),
        ]

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

    # ---- 翻转带调试显示 ---------------------------------------------
    def _debug_flip_area(self, surface: pygame.Surface, world: World, offsets) -> None:
        """翻转带：贴顶那条红色斜纹是向上翻，贴底那条蓝色是向下翻。"""
        height = float(world.height_in_blocks)
        window = surface.get_rect()
        for upward in (True, False):
            low, high = flip_area(height, offsets, upward)
            if high - low <= 0.0:
                continue
            band = Body(left=0.0, bottom=low, width=world.width_in_blocks, height=high - low)
            rect = self.viewport.to_screen_rect(band, world).clip(window)
            if rect.width <= 0 or rect.height <= 0:
                continue
            color = debug_display.FLIP_UP_COLOR if upward else debug_display.FLIP_DOWN_COLOR
            self._hatch(surface, rect, color)
            edge_y = rect.top if upward else rect.bottom - 1
            pygame.draw.line(surface, color[:3], (rect.left, edge_y), (rect.right, edge_y), 1)

    @staticmethod
    def _hatch(surface: pygame.Surface, rect: pygame.Rect, color: tuple, step: int = 14, width: int = 4) -> None:
        """斜向斑马纹：45° 斜线铺满这块矩形，颜色带 alpha 所以是半透明的。"""
        layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        reach = rect.height
        for x in range(-reach - step, rect.width + step, step):
            pygame.draw.line(layer, color, (x, rect.height), (x + reach, 0), width)
        surface.blit(layer, rect.topleft)
