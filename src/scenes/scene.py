"""Scene：流程单元，持有对象与世界，按固定顺序驱动系统。"""

import pygame

from controller.controller_system import ControllerSystem
from physics.physics_system import PhysicsSystem
from renderer.render_system import RenderSystem
from world.level import (
    LevelDefinition,
    build_blocks,
    build_boundaries,
    build_buttons,
    build_destination,
    build_fans,
    build_items,
    build_movable_blocks,
    build_player,
    build_world,
    load_level_file,
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
        self.input_state = None

        self.controller_system: ControllerSystem = ControllerSystem()
        self.physics_system: PhysicsSystem = PhysicsSystem()
        self.render_system: RenderSystem = RenderSystem()

        self.requested_next_scene: Scene | None = None
        self.elapsed_seconds: float = 0.0

    @classmethod
    def from_level(cls, level_definition: LevelDefinition) -> "Scene":
        """由关卡数据建场景：方块、机关与物件都成为 GameObject。"""
        world = build_world(level_definition)
        objects = (
            build_blocks(level_definition)
            + build_movable_blocks(level_definition)
            + build_items(level_definition)
            + build_buttons(level_definition)
            + build_fans(level_definition)
            + build_destination(level_definition)
            + build_player(level_definition)
            + build_boundaries(world)
        )
        return cls(world=world, objects=objects)

    @classmethod
    def from_level_file(cls, path: str) -> "Scene":
        return cls.from_level(load_level_file(path))

    def enter(self) -> None:
        """进入场景。"""

    def exit(self) -> None:
        """离开场景。"""

    def handle_event(self, pygame_event: pygame.event.Event) -> None:
        """处理一个 pygame 事件。"""

    def update(self, delta_seconds: float) -> None:
        """一步：控制来源（输入与机关）先决定运动 → 物理积分与解算。"""
        self.elapsed_seconds += delta_seconds
        if self.world is None:
            return
        self.controller_system.update(self.objects, self.input_state, delta_seconds)
        self.physics_system.update(self.objects, self.world, delta_seconds)

    def draw(self, surface: pygame.Surface) -> None:
        """每帧一次：绘制。与 update 分开，因为一步可能在一帧内执行多次。"""
        self.render_system.update(self.objects, surface)
