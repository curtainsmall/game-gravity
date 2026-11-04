"""入口：窗口、时钟、固定步长主循环、输入采集。"""

import sys
from pathlib import Path

import pygame

from controller.input_source import InputState
from scenes.scene import Scene

# 待定：窗口尺寸随关卡比例与地面/天花板条带确定
WINDOW_PIXEL_SIZE = (960, 540)
BACKGROUND_COLOR = (235, 235, 235)
RENDER_FRAME_RATE_LIMIT = 120
PHYSICS_STEP_SECONDS = 1.0 / 60.0
MAX_ELAPSED_SECONDS_PER_FRAME = 0.25

# 打包成 exe 后，资源放在 exe 旁边；直接跑源码时放在仓库根目录
BASE_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent.parent
)
LEVEL_PATH = BASE_DIR / "assets" / "levels" / "01.json"


def load_scene() -> Scene:
    """有第一个关卡就用它，没有就用空场景。"""
    if LEVEL_PATH.exists():
        return Scene.from_level_file(str(LEVEL_PATH))
    return Scene()


def read_move_axis() -> int:
    pressed = pygame.key.get_pressed()
    if pressed[pygame.K_a]:
        return -1
    if pressed[pygame.K_d]:
        return 1
    return 0


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_PIXEL_SIZE)
    pygame.display.set_caption("game-gravity")

    frame_clock = pygame.time.Clock()
    active_scene = load_scene()
    active_scene.enter()

    is_running = True
    unconsumed_seconds = 0.0
    jump_edge = False
    flip_edge = False

    while is_running:
        elapsed_seconds = frame_clock.tick(RENDER_FRAME_RATE_LIMIT) / 1000.0
        unconsumed_seconds += min(elapsed_seconds, MAX_ELAPSED_SECONDS_PER_FRAME)

        restart_requested = False
        for pygame_event in pygame.event.get():
            if pygame_event.type == pygame.QUIT:
                is_running = False
            elif pygame_event.type == pygame.KEYDOWN:
                if pygame_event.key == pygame.K_TAB:
                    active_scene.toggle_view_mode()
                elif pygame_event.key == pygame.K_SPACE:
                    jump_edge = True
                elif pygame_event.key == pygame.K_e:
                    flip_edge = True
                elif pygame_event.key == pygame.K_r:
                    restart_requested = True
            active_scene.handle_event(pygame_event)

        if restart_requested:
            view_mode = active_scene.view_mode
            active_scene.exit()
            active_scene = load_scene()
            active_scene.view_mode = view_mode
            active_scene.enter()
            jump_edge = False
            flip_edge = False
            unconsumed_seconds = 0.0

        active_scene.input_state = InputState(read_move_axis(), jump_edge, flip_edge)

        ran_a_step = False
        while unconsumed_seconds >= PHYSICS_STEP_SECONDS:
            active_scene.update(PHYSICS_STEP_SECONDS)
            unconsumed_seconds -= PHYSICS_STEP_SECONDS
            ran_a_step = True

        # 按键边沿只在真正跑过一步物理后清除，否则这一帧的输入会丢失
        if ran_a_step:
            jump_edge = False
            flip_edge = False

        screen.fill(BACKGROUND_COLOR)
        active_scene.draw(screen)
        pygame.display.flip()

    active_scene.exit()
    pygame.quit()


if __name__ == "__main__":
    main()
