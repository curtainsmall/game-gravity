"""入口：窗口、时钟、主循环。界面与关卡推进都在 App 里。

窗口只能从四个角按对角线拉大拉小，并且始终按 16:9：游戏按 960x540 画，再整幅等比贴到窗口上。
"""

import pygame

import window
from app import App

RENDER_FRAME_RATE_LIMIT = 120


def main() -> None:
    pygame.init()
    frame = pygame.Surface(window.LOGICAL_SIZE)
    pygame.display.set_mode(window.LOGICAL_SIZE, pygame.RESIZABLE)
    window.limit_resize_to_corners()

    frame_clock = pygame.time.Clock()
    app = App(frame)
    # 窗口标题就是 game.json 里的游戏标题
    pygame.display.set_caption(app.title)

    while app.running:
        elapsed_seconds = frame_clock.tick(RENDER_FRAME_RATE_LIMIT) / 1000.0
        window.refresh()
        for pygame_event in pygame.event.get():
            window.handle_event(pygame_event)
            app.handle_event(window.logical_event(pygame_event))
        window.settle()
        app.update(elapsed_seconds)
        app.draw(frame)
        window.present(pygame.display.get_surface(), frame)
        pygame.display.flip()

    app.sound.shutdown()
    pygame.quit()


if __name__ == "__main__":
    main()
