"""App：界面状态机。

界面有标题、选关、游玩、结算四个，暂停和设置是两个浮层：暂停只盖在游玩上，
设置可以盖在任何界面上。游玩本身不存档，退出标题就算放弃进度。
音乐跟着界面走：标题和选关共用标题音乐，每一关放关卡自己的曲子，结算放结局音乐。
"""

from enum import StrEnum

import pygame

import screens
import ui
import user_settings
from controller.input_source import InputState
from game_settings import credits_of, game_root, load_game_settings, title_of
from levels import discover_levels, load_scene
from renderer.viewport import ViewMode
from scenes.scene import Scene
from sound.bgm import ENDING_KEY, TITLE_KEY, game_bgm
from sound.sound_system import SoundSystem

PHYSICS_STEP_SECONDS = 1.0 / 60.0
MAX_ELAPSED_SECONDS_PER_FRAME = 0.25
BACKGROUND_COLOR = (235, 235, 235)
LEVEL_SCROLL_STEP = 60
TOAST_SECONDS = 2.2


class Screen(StrEnum):
    TITLE = "title"
    LEVEL_SELECT = "level_select"
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
        # 游戏设置（game.json）：标题和版权信息，标题给窗口和标题画面，版权给结算画面
        self.game_settings = load_game_settings()
        self.title = title_of(self.game_settings)
        self.credits = credits_of(self.game_settings)
        # 标题、结局的音乐在 game.json 里；每一关的音乐跟着关卡文件走（Scene.bgm）
        self.title_bgm = game_bgm(self.game_settings, TITLE_KEY, game_root())
        self.ending_bgm = game_bgm(self.game_settings, ENDING_KEY, game_root())
        self.sound.start()
        self.sound.play(self.title_bgm)
        self.levels = discover_levels()
        self.level_index = 0
        self.scene: Scene | None = None
        self.view_mode = ViewMode.VERTICAL_EXPAND
        self.paused = False
        self.settings_open = False
        self.level_scroll = 0
        self.unconsumed_seconds = 0.0
        self.jump_edge = False
        self.flip_edge = False
        self.toast_text = ""
        self.toast_seconds = 0.0
        # 调试显示：启动时不画占位几何体
        self.debug = False

    # ---- 事件 -------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
            return
        if self.settings_open:
            self.handle_settings_event(event)
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
        elif event.key == pygame.K_SPACE:
            self.jump_edge = True
        elif event.key == pygame.K_r:
            self.flip_edge = True

    def handle_pause_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.set_paused(False)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            rects = ui.pause_rects(self.surface)
            if rects["resume"].collidepoint(event.pos) or not rects["panel"].collidepoint(event.pos):
                self.set_paused(False)
            elif rects["restart"].collidepoint(event.pos):
                self.start_level(self.level_index)
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
        if rects["back"].collidepoint(event.pos) or not rects["panel"].collidepoint(event.pos):
            self.settings_open = False

    def handle_ending_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.quit_to_title()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
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
        """暂停：音乐跟着停住，回来接着放。"""
        self.paused = paused
        if paused:
            self.sound.pause()
        else:
            self.sound.resume()

    # ---- 关卡切换 ---------------------------------------------------
    def show_toast(self, text: str) -> None:
        """屏幕底部弹一句临时提示。"""
        self.toast_text = text
        self.toast_seconds = TOAST_SECONDS

    def start_level(self, index: int) -> None:
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
        # 同一关再进一次时这一首还在放，不会打断重来
        self.sound.play(scene.bgm)

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
            self.screen = Screen.ENDING
            self.sound.play(self.ending_bgm)
            return
        self.start_level(index)

    def quit_to_title(self) -> None:
        if self.scene is not None:
            self.scene.exit()
            self.scene = None
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
        if self.toast_seconds > 0.0:
            self.toast_seconds = max(0.0, self.toast_seconds - elapsed_seconds)
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
            self.advance_level()

    def draw(self, surface: pygame.Surface) -> None:
        if self.screen == Screen.PLAYING and self.scene is not None:
            self.scene.debug = self.debug
            surface.fill(BACKGROUND_COLOR)
            self.scene.draw(surface)
        elif self.screen == Screen.LEVEL_SELECT:
            screens.draw_level_select(surface, self)
        elif self.screen == Screen.ENDING:
            screens.draw_ending(surface, self)
        else:
            screens.draw_title(surface, self)

        if self.paused:
            screens.draw_pause(surface)
        if self.settings_open:
            screens.draw_settings(surface, self)
        if self.toast_seconds > 0.0 and self.toast_text:
            ui.draw_toast(surface, self.toast_text, self.toast_seconds)
