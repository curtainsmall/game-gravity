"""Scene：流程单元，持有对象与世界，按固定顺序驱动系统。"""

from pathlib import Path

import pygame

from controller.controller_system import ControllerSystem
from controller.flip_rule import FLIP_AREA_OFFSETS_DEFAULT
from controller.input_source import InputSource
from core.game_object import GameObjectKind
from cutscene.cutscene import Cutscene, cutscene_of
from game_settings import game_root, load_game_settings, player_of
from item.pickup_system import PickupSystem
from physics.physics_system import PhysicsSystem
from portal.portal_system import PortalSystem
from renderer.render_system import RenderSystem
from renderer.viewport import ViewMode
from sound.bgm import Bgm, level_bgm
from trigger.trigger_system import TriggerSystem
from world.follower import FollowSystem
from world.level import (
    LevelDefinition,
    animation_of,
    build_blocks,
    build_boundaries,
    build_buttons,
    build_destination,
    build_nozzles,
    build_items,
    build_movable_blocks,
    build_player,
    build_portals,
    build_textures,
    build_world,
    flip_area_offsets_of,
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
        self.portal_system: PortalSystem = PortalSystem()
        self.trigger_system: TriggerSystem = TriggerSystem()
        self.follow_system: FollowSystem = FollowSystem()
        self.render_system: RenderSystem = RenderSystem()

        self.requested_next_scene: Scene | None = None
        self.elapsed_seconds: float = 0.0
        # 调试显示：由 App 按设置里的那一个开关填进来
        self.debug: bool = False
        self.flip_area_offsets: tuple[float, float] = FLIP_AREA_OFFSETS_DEFAULT
        self.player_animation: dict = {}
        self.bgm: Bgm | None = None          # 这一关的音乐，App 切场景时放
        self.cutscene: Cutscene | None = None  # 进这一关之前的过场

    @classmethod
    def from_level(
        cls,
        level_definition: LevelDefinition,
        base_dir: str | Path | None = None,
        game_settings: dict | None = None,
    ) -> "Scene":
        """由关卡数据建场景：方块、机关与物件都成为 GameObject。

        玩家的跳高、速度、动画以 game.json 为准，关卡里的 player 写了就覆盖它；
        base_dir 就是 game.json 所在的文件夹，两份 json 里的相对路径都以它为基准。
        """
        game_player = player_of(game_settings or {})
        world = build_world(level_definition, base_dir)
        InputSource.set_jump_height(jump_height_of(level_definition, game_player))
        InputSource.set_move_speed(move_speed_of(level_definition, game_player))
        InputSource.set_flip_area(
            flip_area_offsets_of(level_definition), world.height_in_blocks
        )
        players = build_player(level_definition)
        buttons = build_buttons(level_definition)
        objects = (
            build_blocks(level_definition)                 # 方块与木板
            + build_movable_blocks(level_definition)
            + build_boundaries(world)                      # 地面/天花板/墙
            # 贴图由渲染先铺一层，调试显示再整层压上来；列表顺序只影响占位之间的先后
            + build_textures(level_definition, base_dir)
            + build_items(level_definition)
            + buttons
            + build_portals(level_definition)
            + build_nozzles(level_definition)
            + build_destination(level_definition)
            + players
        )
        scene = cls(world=world, objects=objects)
        scene.player = players[0] if players else None
        # 贴图按名字挂到可移动方块上，记下加载时的相对位置
        scene.follow_system.attach(objects)
        # 触发行为：来源名字解析一次，之后每帧派发事件
        scene.trigger_system.attach(objects)
        scene.flip_area_offsets = flip_area_offsets_of(level_definition)
        # 玩家动画先读出来放着：还没有动画系统拿去用
        scene.player_animation = animation_of(level_definition, game_player, base_dir)
        # 这一关的音乐也跟着关卡文件走，曲子找不到就是没有音乐
        scene.bgm = level_bgm(level_definition, base_dir)
        # 进这一关之前的过场：没图就当作没有
        scene.cutscene = cutscene_of(level_definition, base_dir)
        return scene

    @classmethod
    def from_level_file(cls, path: str) -> "Scene":
        """关卡里的相对路径都以 game.json 所在的文件夹为基准；玩家参数也来自它。"""
        return cls.from_level(load_level_file(path), game_root(), load_game_settings())

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
        """一步：派发触发事件 → 控制来源 → 贴图跟随 → 物理积分与解算 → 道具拾取 → 传送门。"""
        self.elapsed_seconds += delta_seconds
        if self.world is None:
            return
        self.trigger_system.update()
        self.controller_system.update(self.objects, self.input_state, delta_seconds)
        self.follow_system.update()
        self.physics_system.update(self.objects, self.world, delta_seconds)
        self.pickup_system.update(self.objects)
        self.portal_system.update(self.objects, self.player)

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
        self.render_system.update(
            self.objects,
            self.world,
            surface,
            focus_x,
            self.view_mode,
            self.debug,
            self.flip_area_offsets,
        )
