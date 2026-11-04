"""入口：窗口、时钟、固定步长主循环。"""

import os

import pygame

from scenes.scene import Scene

# 待定：窗口尺寸随关卡比例与地面/天花板条带确定
WINDOW_PIXEL_SIZE = (960, 540)
BACKGROUND_COLOR = (235, 235, 235)
LEVEL_PATH = "assets/levels/01.json"
RENDER_FRAME_RATE_LIMIT = 120
PHYSICS_STEP_SECONDS = 1.0 / 60.0
MAX_ELAPSED_SECONDS_PER_FRAME = 0.25


def load_scene() -> Scene:
    """有第一个关卡就用它，没有就用空场景。"""
    if os.path.exists(LEVEL_PATH):
        return Scene.from_level_file(LEVEL_PATH)
    return Scene()


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_PIXEL_SIZE)
    pygame.display.set_caption("game-gravity")

    frame_clock = pygame.time.Clock()
    active_scene = load_scene()
    active_scene.enter()

    is_running = True
    unconsumed_seconds = 0.0

    while is_running:
        elapsed_seconds = frame_clock.tick(RENDER_FRAME_RATE_LIMIT) / 1000.0
        unconsumed_seconds += min(elapsed_seconds, MAX_ELAPSED_SECONDS_PER_FRAME)

        for pygame_event in pygame.event.get():
            if pygame_event.type == pygame.QUIT:
                is_running = False
            else:
                active_scene.handle_event(pygame_event)

        while unconsumed_seconds >= PHYSICS_STEP_SECONDS:
            active_scene.update(PHYSICS_STEP_SECONDS)
            unconsumed_seconds -= PHYSICS_STEP_SECONDS

        screen.fill(BACKGROUND_COLOR)
        active_scene.draw(screen)
        pygame.display.flip()

    active_scene.exit()
    pygame.quit()


if __name__ == "__main__":
    main()
