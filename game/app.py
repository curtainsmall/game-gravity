"""App：界面状态机。

界面有标题、选关、过场、游玩、结算五个，暂停和设置是两个浮层：暂停只盖在游玩或
过场上，设置可以盖在任何界面上。游玩本身不存档，退出标题就算放弃进度。
音乐跟着界面走：标题和选关共用标题音乐，每一关放关卡自己的曲子，结算画面放制作名单音乐；
过场按自己的 sound 决定静音、沿用本幕音乐，还是放指定的曲子。
"""

from enum import StrEnum

import pygame

import debug_display
import screens
import ui
import user_settings
from controller.input_source import InputSource, InputState
from cutscene.cutscene import Cutscene, cutscene_of
from cutscene.player import CutscenePlayer
from game_settings import (
    credits_of,
    game_root,
    load_game_settings,
    screen_background,
    title_of,
)
from levels import discover_levels, load_scene
from renderer.viewport import ViewMode
from scenes.scene import Scene
from sound.bgm import CREDITS_KEY, TITLE_KEY, Bgm, game_bgm
from sound.library import library_sounds
from sound.sound_system import SoundSystem

PHYSICS_STEP_SECONDS = 1.0 / 60.0
MAX_ELAPSED_SECONDS_PER_FRAME = 0.25
BACKGROUND_COLOR = (235, 235, 235)
LEVEL_SCROLL_STEP = 60
TOAST_SECONDS = 2.2
SCENE_FADE_SECONDS = 0.5      # 过场结束后场景从黑淡入的高度
CUTSCENE_STEP_SECONDS = 0.1   # 过场每帧最多走多久，卡一下也不会跳掉好几张


class Screen(StrEnum):
    TITLE = "title"
    LEVEL_SELECT = "level_select"
    CUTSCENE = "cutscene"
    PLAYING = "playing"
    ENDING = "ending"


def read_move_axis() -> int:
    pressed = pygame.key.get_pressed()
    if pressed[pygame.K_a]:
        return -1
    if pressed[pygame.K_d]:
        return 1
    return 0


class App:
    def __init__(self, surface: pygame.Surface) -> None:
        self.surface = surface
        self.running = True
        self.screen = Screen.TITLE
        # 玩家自己的设置（exe 旁边的 .game/setting.json）：只有音量，改一次写一次
        self.user_settings = user_settings.load_settings()
        self.sound = SoundSystem(user_settings.volume_of(self.user_settings))
        # 游戏设置（game.json）：标题和制作名单，标题给窗口和标题画面，制作名单给结算画面
        self.game_settings = load_game_settings()
        self.title = title_of(self.game_settings)
        self.credits = credits_of(self.game_settings)
        # 标题画面 / 结算画面的背景图（game.json 的 backgrounds），没图就是纯色
        self.title_background = screen_background(self.game_settings, "title", game_root())
        self.credits_background = screen_background(self.game_settings, "credits", game_root())
        # 标题、制作名单的音乐在 game.json 里；每一关的音乐跟着关卡文件走（Scene.bgm）
        # 结算画面显示的就是制作名单，所以这一幕的音乐叫制作名单音乐
        self.title_bgm = game_bgm(self.game_settings, TITLE_KEY, game_root())
        self.credits_bgm = game_bgm(self.game_settings, CREDITS_KEY, game_root())
        # game.json 里的结尾过场：最后一关之后、制作名单之前
        self.ending_cutscene = cutscene_of(
        self.game_settings, game_root(), library_sounds(self.game_settings, game_root())
    )
        self.sound.start()
        self.sound.play(self.title_bgm)
        self.levels = discover_levels()
        self.level_index = 0
        self.scene: Scene | None = None
        self.cutscene_player: CutscenePlayer | None = None
        self.cutscene_target = ""            # 过场结束后去哪："level" / "ending"
        self.cutscene_paused = False
        self.pending_scene: Scene | None = None
        self.pending_level_index = 0
        self.fade_in_seconds = 0.0           # 场景从黑淡入还剩几秒
        self.view_mode = ViewMode.VERTICAL_EXPAND
        self.paused = False
        self.settings_open = False
        self.credits_page = 0        # 结局的制作名单停在第几页
        self.credits_elapsed = 0.0   # 这一页已经展示了多少秒（管淡入淡出和自动翻页）
        self.level_scroll = 0
        self.unconsumed_seconds = 0.0
        self.jump_edge = False
        self.flip_edge = False
        self.toast_text = ""
        self.toast_seconds = 0.0
        # 终点还锁着的时候只提示一次，离开终点再压上去才重新提示
        self.destination_was_locked = False
        # 调试显示：启动时不画占位几何体；玩家的占位框是单独一个开关
        self.debug = False
        self.player_debug = False

    # ---- 事件 -------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
            return
        if self.settings_open:
            self.handle_settings_event(event)
            return
        if self.cutscene_player is not None:
            self.handle_cutscene_event(event)
            return
        if self.screen == Screen.PLAYING and self.paused:
            self.handle_pause_event(event)
            return
        if self.screen == Screen.TITLE:
            self.handle_title_event(event)
        elif self.screen == Screen.LEVEL_SELECT:
            self.handle_level_select_event(event)
        elif self.screen == Screen.PLAYING:
            self.handle_playing_event(event)
        elif self.screen == Screen.ENDING:
            self.handle_ending_event(event)

    def handle_title_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.start_first_level()
            elif event.key == pygame.K_ESCAPE:
                self.running = False
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            rects = ui.title_rects(self.surface)
            if rects["start"].collidepoint(event.pos):
                self.start_first_level()
            elif rects["levels"].collidepoint(event.pos):
                self.level_scroll = 0
                self.screen = Screen.LEVEL_SELECT
            elif rects["quit"].collidepoint(event.pos):
                self.running = False
            elif rects["settings"].collidepoint(event.pos):
                self.settings_open = True

    def handle_level_select_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.screen = Screen.TITLE
            return
        if event.type == pygame.MOUSEWHEEL:
            self.level_scroll -= event.y * LEVEL_SCROLL_STEP
            self.clamp_level_scroll()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if ui.back_rect(self.surface).collidepoint(event.pos):
                self.screen = Screen.TITLE
                return
            area = ui.level_view_area(self.surface)
            if not area.collidepoint(event.pos):
                return
            for index in range(len(self.levels)):
                rect = ui.level_row_rect(self.surface, index, self.level_scroll)
                if rect.collidepoint(event.pos):
                    if self.levels[index].playable:
                        self.start_level(index)
                    else:
                        # 半透明的关卡点不开，只提示一句
                        self.show_toast(f"{self.levels[index].name} 没有起点或终点，已跳过")
                    return

    def handle_playing_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.set_paused(True)
        elif event.key == pygame.K_TAB and self.scene is not None:
            self.scene.toggle_view_mode()
            self.view_mode = self.scene.view_mode
        elif event.key == pygame.K_w:
            self.jump_edge = True
        elif event.key == pygame.K_SPACE:
            self.flip_edge = True

    def handle_cutscene_event(self, event: pygame.event.Event) -> None:
        """过场里：Esc 暂停，按住空格跳过，其它输入都不接。"""
        player = self.cutscene_player
        if player is None:
            return
        if self.cutscene_paused:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.set_cutscene_paused(False)
                return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                rects = ui.cutscene_pause_rects(self.surface)
                if rects["resume"].collidepoint(event.pos) or not rects["panel"].collidepoint(
                    event.pos
                ):
                    self.set_cutscene_paused(False)
                elif rects["settings"].collidepoint(event.pos):
                    self.settings_open = True
                elif rects["title"].collidepoint(event.pos):
                    self.quit_to_title()
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.set_cutscene_paused(True)
            elif event.key == pygame.K_SPACE:
                # 只有过场开始后新按下的空格才算：进来时按着的不会触发
                player.hold_skip()
        elif event.type == pygame.KEYUP and event.key == pygame.K_SPACE:
            player.release_skip()

    def set_cutscene_paused(self, paused: bool) -> None:
        """过场暂停：画面停住，BGM 继续放（和关卡暂停不同）。"""
        self.cutscene_paused = paused
        if self.cutscene_player is not None:
            self.cutscene_player.paused = paused
            self.cutscene_player.release_skip()

    def handle_pause_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.set_paused(False)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            rects = ui.pause_rects(self.surface)
            if rects["resume"].collidepoint(event.pos) or not rects["panel"].collidepoint(event.pos):
                self.set_paused(False)
            elif rects["restart"].collidepoint(event.pos):
                # 重新开始是重试玩法，不重播过场
                self.start_level(self.level_index, cutscene=False)
            elif rects["settings"].collidepoint(event.pos):
                self.settings_open = True
            elif rects["title"].collidepoint(event.pos):
                self.quit_to_title()

    def handle_settings_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.settings_open = False
            return
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        rects = ui.settings_rects(self.surface)
        for key, row in rects["volume"].items():
            if row["minus"].collidepoint(event.pos):
                self.step_volume(key, -1)
                return
            if row["plus"].collidepoint(event.pos):
                self.step_volume(key, 1)
                return
            if row["hit"].collidepoint(event.pos):
                # 点滑条：按点到的位置直接跳过去
                track = row["track"]
                self.set_volume(key, (event.pos[0] - track.left) / max(1, track.width))
                return
        if rects["debug"].collidepoint(event.pos):
            self.debug = not self.debug
            return
        if rects["player_debug"].collidepoint(event.pos):
            self.player_debug = not self.player_debug
            return
        if rects["back"].collidepoint(event.pos) or not rects["panel"].collidepoint(event.pos):
            self.settings_open = False

    def handle_ending_event(self, event: pygame.event.Event) -> None:
        """结局画面：空格跳过这一页；按钮要等最后一页淡入完才可点。"""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            self.skip_credits_page()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not screens.credits_done(self):
                return
            rects = ui.ending_rects(self.surface)
            if rects["title"].collidepoint(event.pos):
                self.quit_to_title()
            elif rects["quit"].collidepoint(event.pos):
                self.running = False

    # ---- 音量与暂停 -------------------------------------------------
    def set_volume(self, key: str, value: float) -> None:
        """改一项音量：马上对正在放的曲子生效，同时写进 .game/setting.json。"""
        volume = user_settings.set_volume(self.user_settings, key, value)
        self.sound.set_volume(volume)
        user_settings.save_settings(self.user_settings)

    def step_volume(self, key: str, steps: int) -> None:
        """按 10% 一格加减（设置里的「−」「＋」）。"""
        volume = user_settings.step_volume(self.user_settings, key, steps)
        self.sound.set_volume(volume)
        user_settings.save_settings(self.user_settings)

    def set_paused(self, paused: bool) -> None:
        """暂停：音乐和音效都跟着停住，回来接着放。"""
        self.paused = paused
        if paused:
            self.sound.pause()
            self.sound.pause_sounds()
        else:
            self.sound.resume()
            self.sound.resume_sounds()

    # ---- 关卡切换 ---------------------------------------------------
    def show_toast(self, text: str) -> None:
        """屏幕底部弹一句临时提示。"""
        self.toast_text = text
        self.toast_seconds = TOAST_SECONDS

    def start_level(self, index: int, cutscene: bool = True) -> None:
        """进关卡：有关卡过场就先播过场，cutscene=False 时直接进（重新开始用）。"""
        if not self.levels:
            self.show_toast("game/levels/ 目录中暂无可用的关卡")
            self.screen = Screen.TITLE
            return
        if not 0 <= index < len(self.levels):
            self.show_toast("该关卡不存在")
            self.screen = Screen.TITLE
            return
        if not self.levels[index].playable:
            # 没有起点或终点的关卡不进游戏，只在选关里半透明列出来
            self.show_toast(f"{self.levels[index].name} 没有起点或终点，已跳过")
            return
        scene = load_scene(self.levels[index])
        if scene is None:
            self.show_toast(f"无法读取关卡：{self.levels[index].name}")
            self.screen = Screen.TITLE
            return
        if cutscene and scene.cutscene is not None:
            self.begin_cutscene(scene.cutscene, "level", scene, index)
            return
        self.enter_level(scene, index)

    def enter_level(self, scene: Scene, index: int, fade_in: bool = False) -> None:
        """真的进关卡：装好场景、开始玩，过场之后进来时从黑淡入。"""
        if self.scene is not None:
            self.scene.exit()
        self.level_index = index
        self.scene = scene
        self.scene.view_mode = self.view_mode
        self.scene.enter()
        self.screen = Screen.PLAYING
        self.paused = False
        self.unconsumed_seconds = 0.0
        self.jump_edge = False
        self.flip_edge = False
        self.destination_was_locked = False
        # 同一首（过场里已经在放的那首）不会重头开始
        self.sound.play(scene.bgm)
        # 上一关的音效先收声，再放这一关声音对象里 general 预设的
        self.sound.stop_sounds()
        scene.start_sounds(self.sound)
        self.fade_in_seconds = SCENE_FADE_SECONDS if fade_in else 0.0

    # ---- 过场 -------------------------------------------------------
    def begin_cutscene(
        self,
        cutscene: Cutscene,
        target: str,
        scene: Scene | None = None,
        index: int = 0,
    ) -> None:
        """开始一段过场：音乐按 sound 定，播完去 target（关卡或结算）。"""
        if self.scene is not None:
            self.scene.exit()
            self.scene = None
        self.sound.stop_sounds()          # 离开关卡：这一关的音效收声
        self.cutscene_player = CutscenePlayer(cutscene, self.surface.get_size())
        self.cutscene_target = target
        self.cutscene_paused = False
        self.pending_scene = scene
        self.pending_level_index = index
        self.screen = Screen.CUTSCENE
        self.paused = False
        self.settings_open = False
        self.fade_in_seconds = 0.0
        self.play_cutscene_music(cutscene, target, scene)
        if not self.cutscene_player.has_pictures:
            # 图全读不出来：别黑屏卡着，直接进下一幕
            self.finish_cutscene()

    def play_cutscene_music(
        self, cutscene: Cutscene, target: str, scene: Scene | None
    ) -> None:
        """sound: false 静音；true 用本幕音乐；对象就用那首。"""
        if cutscene.keep_scene_music:
            music: Bgm | None = self.credits_bgm if target == "ending" else None
            if target != "ending" and scene is not None:
                music = scene.bgm
        elif cutscene.sound is not None:
            music = cutscene.sound
        else:
            music = None
        self.sound.play(music)

    def finish_cutscene(self) -> None:
        target = self.cutscene_target
        scene = self.pending_scene
        index = self.pending_level_index
        self.cutscene_player = None
        self.cutscene_target = ""
        self.cutscene_paused = False
        self.pending_scene = None
        self.pending_level_index = 0
        if target == "level" and scene is not None:
            self.enter_level(scene, index, fade_in=True)
        else:
            self.finish_to_ending(fade_in=True)

    def finish_to_ending(self, fade_in: bool = False) -> None:
        self.screen = Screen.ENDING
        self.credits_page = 0
        self.credits_elapsed = 0.0
        self.sound.stop_sounds()
        self.sound.play(self.credits_bgm)
        self.fade_in_seconds = SCENE_FADE_SECONDS if fade_in else 0.0

    def skip_credits_page(self) -> None:
        """空格：把这一页的停留直接走完（随后淡出、翻页）；最后一页就让名单直接结束。"""
        last = len(screens.credits_pages(self.credits)) - 1
        if self.credits_page < last:
            self.credits_elapsed = max(
                self.credits_elapsed, screens.CREDITS_FADE_IN + screens.CREDITS_HOLD
            )
        else:
            self.credits_elapsed = max(self.credits_elapsed, screens.CREDITS_PAGE_SECONDS)

    def next_playable_index(self, start: int) -> int | None:
        """从 start 起往后第一个能玩的关卡（不往回绕）。"""
        for index in range(max(0, start), len(self.levels)):
            if self.levels[index].playable:
                return index
        return None

    def start_first_level(self) -> None:
        """开始游戏：从第一关能玩的那关开始，都玩不了就提示。"""
        index = self.next_playable_index(0)
        if index is None:
            self.show_toast("没有可玩的关卡：每一关都需要起点和终点")
            self.screen = Screen.TITLE
            return
        self.start_level(index)

    def advance_level(self) -> None:
        index = self.next_playable_index(self.level_index + 1)
        if index is None:
            if self.ending_cutscene is not None:
                self.begin_cutscene(self.ending_cutscene, "ending")
            else:
                self.finish_to_ending()
            return
        self.start_level(index)

    def quit_to_title(self) -> None:
        if self.scene is not None:
            self.scene.exit()
            self.scene = None
        self.sound.stop_sounds()
        self.cutscene_player = None
        self.cutscene_target = ""
        self.cutscene_paused = False
        self.pending_scene = None
        self.pending_level_index = 0
        self.fade_in_seconds = 0.0
        self.paused = False
        self.settings_open = False
        self.screen = Screen.TITLE
        # 从暂停里退回标题时音乐也停在那儿，play 会先把它叫醒
        self.sound.play(self.title_bgm)

    def clamp_level_scroll(self) -> None:
        limit = ui.max_level_scroll(self.surface, len(self.levels))
        self.level_scroll = max(0, min(self.level_scroll, limit))

    # ---- 每帧 -------------------------------------------------------
    def update(self, elapsed_seconds: float) -> None:
        # 换曲时旧曲子淡出、新曲子晚一步开始，都靠这一步推进
        self.sound.update(elapsed_seconds)
        if self.fade_in_seconds > 0.0:
            self.fade_in_seconds = max(0.0, self.fade_in_seconds - elapsed_seconds)
        if self.toast_seconds > 0.0:
            self.toast_seconds = max(0.0, self.toast_seconds - elapsed_seconds)
        if self.screen == Screen.CUTSCENE:
            player = self.cutscene_player
            if player is None or self.cutscene_paused or self.settings_open:
                return
            player.update(min(elapsed_seconds, CUTSCENE_STEP_SECONDS))
            if player.finished:
                self.finish_cutscene()
            return
        if self.screen == Screen.ENDING:
            # 制作名单分页：停够了就淡出、翻到下一页；最后一页淡出完就换成按钮
            last = len(screens.credits_pages(self.credits)) - 1
            self.credits_elapsed += min(elapsed_seconds, MAX_ELAPSED_SECONDS_PER_FRAME)
            if self.credits_page < last and self.credits_elapsed >= screens.CREDITS_PAGE_SECONDS:
                self.credits_page += 1
                self.credits_elapsed = 0.0
            return
        if self.screen != Screen.PLAYING or self.paused or self.settings_open:
            return
        if self.scene is None or self.scene.world is None:
            return
        self.unconsumed_seconds += min(elapsed_seconds, MAX_ELAPSED_SECONDS_PER_FRAME)
        self.scene.input_state = InputState(read_move_axis(), self.jump_edge, self.flip_edge)
        ran_a_step = False
        while self.unconsumed_seconds >= PHYSICS_STEP_SECONDS:
            self.scene.update(PHYSICS_STEP_SECONDS)
            self.unconsumed_seconds -= PHYSICS_STEP_SECONDS
            ran_a_step = True
        # 按键边沿只在真正跑过一步物理后清除，否则这一帧的输入会丢失
        if ran_a_step:
            self.jump_edge = False
            self.flip_edge = False
        if self.scene.destination_reached:
            self.destination_was_locked = False
            self.advance_level()
        else:
            locked = self.scene.destination_locked
            if locked and not self.destination_was_locked:
                self.show_toast(
                    f"终点还没有解锁：还有 {self.scene.destination_missing} 个触发条件没有满足"
                )
            self.destination_was_locked = locked

    def draw(self, surface: pygame.Surface) -> None:
        if self.screen == Screen.CUTSCENE and self.cutscene_player is not None:
            self.cutscene_player.draw(surface)
        elif self.screen == Screen.PLAYING and self.scene is not None:
            self.scene.debug = self.debug
            self.scene.player_debug = self.player_debug
            surface.fill(BACKGROUND_COLOR)
            self.scene.draw(surface)
            if self.player_debug:
                debug_display.draw_player_debug(surface, InputSource.jump_height())
        elif self.screen == Screen.LEVEL_SELECT:
            screens.draw_level_select(surface, self)
        elif self.screen == Screen.ENDING:
            screens.draw_ending(surface, self)
        else:
            screens.draw_title(surface, self)

        if self.fade_in_seconds > 0.0:
            alpha = round(255 * min(1.0, self.fade_in_seconds / SCENE_FADE_SECONDS))
            overlay = pygame.Surface(surface.get_size())
            overlay.fill((0, 0, 0))
            overlay.set_alpha(max(0, min(255, alpha)))
            surface.blit(overlay, (0, 0))
        if self.cutscene_paused:
            screens.draw_cutscene_pause(surface)
        elif self.paused:
            screens.draw_pause(surface)
        if self.settings_open:
            screens.draw_settings(surface, self)
        if self.toast_seconds > 0.0 and self.toast_text:
            ui.draw_toast(surface, self.toast_text, self.toast_seconds)
