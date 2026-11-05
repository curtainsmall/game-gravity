"""Scene：流程单元，持有对象与世界，按固定顺序驱动系统。"""

from pathlib import Path

import pygame

from controller.controller_system import ControllerSystem
from controller.input_source import InputSource
from core.game_object import GameObjectKind
from item.pickup_system import PickupSystem
from physics.physics_system import PhysicsSystem
from renderer.render_system import RenderSystem
from renderer.viewport import ViewMode
from world.level import (
    LevelDefinition,
    build_blocks,
    build_boundaries,
    build_buttons,
    build_destination,
    build_nozzles,
    build_items,
    build_movable_blocks,
    build_player,
    build_textures,
    build_world,
    jump_height_of,
    load_level_file,
    move_speed_of,
)
from world.world import World


class Scene:
    def __init__(
        self,
        world: World | None = None,
        objects: list | None = None,
        shared_context=None,
    ) -> None:
        self.world: World | None = world
        self.shared_context = shared_context
        self.objects: list = objects if objects is not None else []
        self.player = None
        self.input_state = None
        self.view_mode: ViewMode = ViewMode.VERTICAL_EXPAND

        self.controller_system: ControllerSystem = ControllerSystem()
        self.physics_system: PhysicsSystem = PhysicsSystem()
        self.pickup_system: PickupSystem = PickupSystem()
        self.render_system: RenderSystem = RenderSystem()

        self.requested_next_scene: Scene | None = None
        self.elapsed_seconds: float = 0.0

    @classmethod
    def from_level(
        cls, level_definition: LevelDefinition, base_dir: str | Path | None = None
    ) -> "Scene":
        """由关卡数据建场景：方块、机关与物件都成为 GameObject。"""
        world = build_world(level_definition, base_dir)
        InputSource.set_jump_height(jump_height_of(level_definition))
        InputSource.set_move_speed(move_speed_of(level_definition))
        players = build_player(level_definition)
        buttons = build_buttons(level_definition)
        triggers_by_name = {button.name: button for button in buttons if button.name}
        objects = (
            build_blocks(level_definition)                 # 方块与木板
            + build_movable_blocks(level_definition, triggers_by_name)
            + build_boundaries(world)                      # 地面/天花板/墙
            + build_textures(level_definition, base_dir)   # 贴图压在所有方块之上
            + build_items(level_definition)
            + buttons
            + build_nozzles(level_definition)
            + build_destination(level_definition)
            + players                                      # 玩家在最上面
        )
        scene = cls(world=world, objects=objects)
        scene.player = players[0] if players else None
        return scene

    @classmethod
    def from_level_file(cls, path: str) -> "Scene":
        """背景这类资源按关卡文件所在目录解析。"""
        return cls.from_level(load_level_file(path), Path(path).parent)

    def enter(self) -> None:
        """进入场景。"""

    def exit(self) -> None:
        """离开场景。"""

    def handle_event(self, pygame_event: pygame.event.Event) -> None:
        """处理一个 pygame 事件。"""

    def toggle_view_mode(self) -> None:
        """纵向铺满与横向铺满之间切换。"""
        if self.view_mode == ViewMode.VERTICAL_EXPAND:
            self.view_mode = ViewMode.HORIZONTAL_EXPAND
        else:
            self.view_mode = ViewMode.VERTICAL_EXPAND

    def update(self, delta_seconds: float) -> None:
        """一步：控制来源 → 物理积分与解算 → 道具拾取。"""
        self.elapsed_seconds += delta_seconds
        if self.world is None:
            return
        self.controller_system.update(self.objects, self.input_state, delta_seconds)
        self.physics_system.update(self.objects, self.world, delta_seconds)
        self.pickup_system.update(self.objects)

    @property
    def destination_reached(self) -> bool:
        """玩家是否碰到终点：终点是传感器，物理每步会把 interaction_state 写好。"""
        return any(
            game_object.kind == GameObjectKind.DESTINATION and game_object.interaction_state
            for game_object in self.objects
        )

    def draw(self, surface: pygame.Surface) -> None:
        """每帧一次：绘制。镜头跟随玩家水平居中。"""
        focus_x = None
        if self.player is not None and self.player.body is not None:
            body = self.player.body
            focus_x = body.left + body.width / 2.0
        self.render_system.update(self.objects, self.world, surface, focus_x, self.view_mode)
