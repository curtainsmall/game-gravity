"""Scene：流程单元，持有对象与世界，按固定顺序驱动系统。"""

from pathlib import Path

import pygame

from animation.library import library_animations
from animation.sprite import AnimationSystem
from controller.controller_system import ControllerSystem
from controller.flip_rule import FLIP_AREA_OFFSETS_DEFAULT
from controller.input_source import InputSource
from core.game_object import GameObjectKind
from cutscene.cutscene import Cutscene, cutscene_of
from game_settings import (
    game_root,
    load_game_settings,
    player_animation_of,
    player_of,
    player_sound_of,
    tutorial_of,
)
from physics.physics_system import PhysicsSystem
from portal.portal_system import PortalSystem
from renderer.render_system import RenderSystem
from renderer.texture import image_size, load_scaled
from renderer.viewport import ViewMode
from sound.bgm import Bgm, level_bgm
from sound.library import library_sounds
from sound.objects import SoundObjects
from trigger.trigger_system import TriggerSystem
from trigger_source.trigger_source_system import TriggerSourceSystem
from world.follower import FollowSystem
from world.level import (
    LevelDefinition,
    build_animation_objects,
    build_blocks,
    build_boundaries,
    build_destination,
    build_nozzles,
    build_movable_blocks,
    build_player,
    build_player_animation,
    build_player_sound,
    build_portals,
    build_sound_objects,
    build_textures,
    build_trigger_sources,
    build_world,
    flip_area_offsets_of,
    jump_height_of,
    load_level_file,
    move_speed_of,
    player_face_of,
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
        self.trigger_source_system: TriggerSourceSystem = TriggerSourceSystem()
        self.portal_system: PortalSystem = PortalSystem()
        self.trigger_system: TriggerSystem = TriggerSystem()
        self.follow_system: FollowSystem = FollowSystem()
        self.render_system: RenderSystem = RenderSystem()

        self.requested_next_scene: Scene | None = None
        self.elapsed_seconds: float = 0.0
        # 调试显示：由 App 按设置里的开关填进来；玩家那一个开关是单独的
        self.debug: bool = False
        self.player_debug: bool = False
        self.flip_area_offsets: tuple[float, float] = FLIP_AREA_OFFSETS_DEFAULT
        self.animation_system: AnimationSystem = AnimationSystem({})
        # 声音对象：进关卡时放 general，之后按玩家状态切 player（由 App 给它混音器）
        self.sound_objects: SoundObjects = SoundObjects({})
        self.bgm: Bgm | None = None          # 这一关的音乐，App 切场景时放
        self.cutscene: Cutscene | None = None  # 进这一关之前的过场
        # 所有关卡共用的教程图：贴在窗口底部，由 Scene.draw 在关卡视图之后画
        self.tutorial_path: str | None = None
        # 触发源解锁的物品 id：App 每帧取走交给背包，不写回关卡
        self.unlocked_items: list[str] = []

    @classmethod
    def from_level(
        cls,
        level_definition: LevelDefinition,
        base_dir: str | Path | None = None,
        game_settings: dict | None = None,
    ) -> "Scene":
        """由关卡数据建场景：方块、机关与物件都成为 GameObject。

        玩家的跳高、速度以 game.json 为准，关卡里的 player 写了就覆盖它；动画来自
        game.json 的动画库，由动画对象自己带预设和链接。
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
        player_animation = player_animation_of(game_settings or {})
        player_sound = player_sound_of(game_settings or {})
        # 声音库里键 → 路径：这一关的音乐、过场和声音对象都从这里取
        sounds = library_sounds(game_settings, base_dir)
        objects = (
            build_blocks(level_definition)                 # 方块与木板
            + build_movable_blocks(level_definition)
            + build_boundaries(world)                      # 地面/天花板/墙
            # 贴图由渲染先铺一层，调试显示再整层压上来；列表顺序只影响占位之间的先后
            + build_textures(level_definition, base_dir)
            + build_animation_objects(level_definition)
            + build_trigger_sources(level_definition)
            + build_portals(level_definition)
            + build_nozzles(level_definition)
            + build_destination(level_definition)
            + players
            + build_player_animation(player_animation, players[0] if players else None)
        )
        scene = cls(world=world, objects=objects)
        scene.player = players[0] if players else None
        # 贴图按名字挂到可移动方块上，记下加载时的相对位置
        scene.follow_system.attach(objects)
        # 触发行为：来源名字解析一次，之后每帧派发事件
        scene.trigger_system.attach(objects)
        scene.flip_area_offsets = flip_area_offsets_of(level_definition)
        # 动画对象：预设/链接写在关卡里，帧来自 game.json 的动画库；玩家的全局动画
        # 由 player_animation 生成，挂在这一关的玩家上，不进关卡数据
        scene.animation_system = AnimationSystem(
            library_animations(game_settings, base_dir)
        )
        scene.animation_system.attach(objects, scene.player)
        scene.animation_system.facing = player_face_of(level_definition)
        # 声音对象：预设/链接写在关卡里，声音来自 game.json 的声音库；没有 body，不进 objects。
        # 玩家自己的音效来自 player_sound，由这里合成，不写回关卡
        scene.sound_objects = SoundObjects(sounds)
        scene.sound_objects.attach(
            build_sound_objects(level_definition) + build_player_sound(player_sound),
            objects,
            scene.player,
        )
        # 这一关的音乐也跟着关卡文件走，曲子找不到就是没有音乐
        scene.bgm = level_bgm(level_definition, base_dir, sounds)
        # 进这一关之前的过场：没图就当作没有
        scene.cutscene = cutscene_of(level_definition, base_dir, sounds)
        # 教程图由 game.json 给，所有关卡共用；路径找不到就不画
        scene.tutorial_path = tutorial_of(game_settings or {}, base_dir)
        return scene

    def start_sounds(self, sound_system) -> None:
        """App 进关卡时调用：把 general 预设的声音放出来。"""
        self.sound_objects.start(sound_system)

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

    def take_unlocked_items(self) -> list[str]:
        """取走这一帧触发源解锁的物品 id；App 把它们交给背包。"""
        unlocked = self.unlocked_items
        self.unlocked_items = []
        return unlocked

    def update(self, delta_seconds: float) -> None:
        """一步：派发触发事件 → 控制来源 → 贴图跟随 → 物理积分与解算 → 道具 → 传送门 → 动画对象。

        触发源按下的物品会先记进 unlocked_items，由 App 交给背包。
        """
        self.elapsed_seconds += delta_seconds
        if self.world is None:
            return
        self.trigger_system.update()
        self.controller_system.update(self.objects, self.input_state, delta_seconds)
        self.follow_system.update()
        self.physics_system.update(self.objects, self.world, delta_seconds)
        self.unlocked_items.extend(
            self.trigger_source_system.update(self.objects)
        )
        self.portal_system.update(self.objects, self.player)
        # 跟玩家的动画对象要在物理和传送之后才摆位
        self.animation_system.update(delta_seconds)
        # 玩家状态变了就换 player 预设的声音
        self.sound_objects.update(delta_seconds)

    def _destination(self):
        """这一关的终点；没有就是 None。"""
        return next(
            (
                game_object
                for game_object in self.objects
                if game_object.kind == GameObjectKind.DESTINATION
            ),
            None,
        )

    @property
    def destination_reached(self) -> bool:
        """玩家碰到终点，并且终点的触发条件全都生效了。"""
        destination = self._destination()
        return bool(
            destination is not None
            and destination.interaction_state
            and self.trigger_system.all_cards_on(destination)
        )

    @property
    def destination_locked(self) -> bool:
        """玩家正压在终点上，但还有触发条件没生效。"""
        destination = self._destination()
        return bool(
            destination is not None
            and destination.interaction_state
            and not self.trigger_system.all_cards_on(destination)
        )

    @property
    def destination_missing(self) -> int:
        """终点还差几张触发卡片没生效。"""
        return self.trigger_system.inactive_cards(self._destination())

    def draw(self, surface: pygame.Surface) -> None:
        """每帧一次：绘制。镜头跟随玩家水平居中，教程图占掉底部一条。"""
        focus_x = None
        if self.player is not None and self.player.body is not None:
            body = self.player.body
            focus_x = body.left + body.width / 2.0
        tutorial_height = self._tutorial_height(surface)
        gameplay = surface
        if tutorial_height:
            # 关卡视图只画在教程图上方，底部不再被教程盖住
            gameplay = surface.subsurface(
                (0, 0, surface.get_width(), surface.get_height() - tutorial_height)
            )
        self.render_system.update(
            self.objects,
            self.world,
            gameplay,
            focus_x,
            self.view_mode,
            self.debug,
            self.flip_area_offsets,
            self.player_debug,
        )
        self._draw_tutorial(surface, tutorial_height)

    def _tutorial_height(self, surface: pygame.Surface) -> int:
        """教程图按画面宽度铺满后占多高；没图或太高就不占位置。"""
        if self.tutorial_path is None:
            return 0
        original = image_size(self.tutorial_path)
        if original is None or original[0] <= 0 or original[1] <= 0:
            return 0
        width = surface.get_width()
        if width <= 0:
            return 0
        height = max(1, round(original[1] * width / original[0]))
        return height if height < surface.get_height() else 0

    def _draw_tutorial(self, surface: pygame.Surface, height: int) -> None:
        """教程图：按画面宽度铺满，贴在底部，不随镜头滚动。"""
        if height <= 0 or self.tutorial_path is None:
            return
        picture = load_scaled(self.tutorial_path, (surface.get_width(), height), True)
        if picture is None:
            return
        surface.blit(picture, (0, surface.get_height() - height))
