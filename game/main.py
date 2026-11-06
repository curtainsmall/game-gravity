"""入口：窗口、时钟、主循环。界面与关卡推进都在 App 里。"""

import pygame

from app import App

WINDOW_PIXEL_SIZE = (960, 540)
RENDER_FRAME_RATE_LIMIT = 120


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_PIXEL_SIZE)

    frame_clock = pygame.time.Clock()
    app = App(screen)
    # 窗口标题就是 game.json 里的游戏标题
    pygame.display.set_caption(app.title)

    while app.running:
        elapsed_seconds = frame_clock.tick(RENDER_FRAME_RATE_LIMIT) / 1000.0
        for pygame_event in pygame.event.get():
            app.handle_event(pygame_event)
        app.update(elapsed_seconds)
        app.draw(screen)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
