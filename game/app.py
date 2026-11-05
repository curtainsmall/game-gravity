"""App：界面状态机。

界面有标题、选关、游玩、结算四个，暂停和设置是两个浮层：暂停只盖在游玩上，
设置可以盖在任何界面上。游玩本身不存档，退出标题就算放弃进度。
"""

from enum import StrEnum

import pygame

import screens
import ui
from controller.input_source import InputState
from levels import discover_levels, load_scene
from renderer.viewport import ViewMode
from scenes.scene import Scene

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
                self.start_level(0)
            elif event.key == pygame.K_ESCAPE:
                self.running = False
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            rects = ui.title_rects(self.surface)
            if rects["start"].collidepoint(event.pos):
                self.start_level(0)
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
                    self.start_level(index)
                    return

    def handle_playing_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.paused = True
        elif event.key == pygame.K_TAB and self.scene is not None:
            self.scene.toggle_view_mode()
            self.view_mode = self.scene.view_mode
        elif event.key == pygame.K_SPACE:
            self.jump_edge = True
        elif event.key == pygame.K_r:
            self.flip_edge = True

    def handle_pause_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.paused = False
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            rects = ui.pause_rects(self.surface)
            if rects["resume"].collidepoint(event.pos) or not rects["panel"].collidepoint(event.pos):
                self.paused = False
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
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            rects = ui.settings_rects(self.surface)
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

    # ---- 关卡切换 ---------------------------------------------------
    def show_toast(self, text: str) -> None:
        """屏幕底部弹一句临时提示。"""
        self.toast_text = text
        self.toast_seconds = TOAST_SECONDS

    def start_level(self, index: int) -> None:
        if not self.levels:
            self.show_toast("levels/ 里没有可用的关卡")
            self.screen = Screen.TITLE
            return
        if not 0 <= index < len(self.levels):
            self.show_toast("没有这个关卡")
            self.screen = Screen.TITLE
            return
        scene = load_scene(self.levels[index])
        if scene is None:
            self.show_toast(f"关卡读不出来：{self.levels[index].name}")
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

    def advance_level(self) -> None:
        next_index = self.level_index + 1
        if next_index >= len(self.levels):
            self.screen = Screen.ENDING
            return
        self.start_level(next_index)

    def quit_to_title(self) -> None:
        if self.scene is not None:
            self.scene.exit()
            self.scene = None
        self.paused = False
        self.settings_open = False
        self.screen = Screen.TITLE

    def clamp_level_scroll(self) -> None:
        limit = ui.max_level_scroll(self.surface, len(self.levels))
        self.level_scroll = max(0, min(self.level_scroll, limit))

    # ---- 每帧 -------------------------------------------------------
    def update(self, elapsed_seconds: float) -> None:
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
