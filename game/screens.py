"""各个界面的绘制：标题、选关、结算，以及暂停与设置浮层。"""

import pygame

import ui
from levels import level_preview

CREDITS = [
    ("Program", "curtainsmall"),
    ("Level Design", "curtainsmall"),
    ("Made with", "pygame-ce"),
]


def draw_title(surface: pygame.Surface, app) -> None:
    surface.fill(ui.BACKGROUND)
    width, height = surface.get_size()
    ui.draw_text(surface, "GRAVITY", 64, center=(width // 2, int(height * 0.22)))
    if not app.levels:
        ui.draw_text(
            surface,
            "levels/ 里没有可用的关卡",
            18,
            center=(width // 2, int(height * 0.32)),
            color=ui.DIM_TEXT,
        )
    rects = ui.title_rects(surface)
    ui.draw_button(surface, rects["start"], "Start")
    ui.draw_button(surface, rects["levels"], "Select Levels")
    ui.draw_button(surface, rects["quit"], "Quit")

    gear = rects["settings"]
    pygame.draw.rect(surface, ui.BUTTON, gear)
    pygame.draw.rect(surface, ui.BORDER, gear, 2)
    ui.draw_gear(surface, gear.inflate(-16, -16))


def draw_level_select(surface: pygame.Surface, app) -> None:
    surface.fill(ui.BACKGROUND)
    width, _ = surface.get_size()
    ui.draw_text(surface, "Select Level", 34, center=(width // 2, 44))
    ui.draw_button(surface, ui.back_rect(surface), "Back", 18)

    area = ui.level_view_area(surface)
    if not app.levels:
        ui.draw_text(surface, "levels/ 里没有可用的关卡", 18, center=area.center, color=ui.DIM_TEXT)
        return

    previous_clip = surface.get_clip()
    surface.set_clip(area)
    for index, entry in enumerate(app.levels):
        rect = ui.level_row_rect(surface, index, app.level_scroll)
        if rect.bottom <= area.top or rect.top >= area.bottom:
            continue
        pygame.draw.rect(surface, ui.PANEL, rect)
        preview = level_preview(entry, (rect.width - 4, rect.height - 4))
        if preview is not None:
            surface.blit(preview, (rect.left + 2, rect.top + 2))
        pygame.draw.rect(surface, ui.BORDER, rect, 2)

        label = ui.font(20).render(entry.name, True, ui.TEXT)
        badge = pygame.Rect(
            rect.left + 10, rect.top + 10, label.get_width() + 18, label.get_height() + 10
        )
        pygame.draw.rect(surface, ui.BUTTON, badge)
        pygame.draw.rect(surface, ui.BORDER, badge, 1)
        surface.blit(label, (badge.left + 9, badge.top + 5))
    surface.set_clip(previous_clip)

    if ui.max_level_scroll(surface, len(app.levels)):
        hint = ui.font(16).render("滚轮滚动", True, ui.DIM_TEXT)
        surface.blit(hint, (area.right - hint.get_width(), area.bottom + 6))


def draw_ending(surface: pygame.Surface, app) -> None:
    surface.fill(ui.BACKGROUND)
    width, height = surface.get_size()
    ui.draw_text(surface, "Thanks for Playing", 46, center=(width // 2, int(height * 0.16)))
    ui.draw_text(
        surface, "全部关卡已通过", 20, center=(width // 2, int(height * 0.25)), color=ui.DIM_TEXT
    )
    for index, (role, name) in enumerate(CREDITS):
        y = int(height * 0.36) + index * 30
        ui.draw_text(surface, role, 18, center=(width // 2 - 20, y), color=ui.DIM_TEXT)
        ui.draw_text(surface, name, 18, center=(width // 2 + 90, y))

    rects = ui.ending_rects(surface)
    ui.draw_button(surface, rects["title"], "Back to Title")
    ui.draw_button(surface, rects["quit"], "Quit")


def draw_pause(surface: pygame.Surface) -> None:
    ui.draw_shade(surface)
    rects = ui.pause_rects(surface)
    ui.draw_panel(surface, rects["panel"])
    ui.draw_text(surface, "Paused", 30, center=(rects["panel"].centerx, rects["panel"].top + 42))
    ui.draw_button(surface, rects["resume"], "Back to Game")
    ui.draw_button(surface, rects["restart"], "Restart Level")
    ui.draw_button(surface, rects["settings"], "Settings")
    ui.draw_button(surface, rects["title"], "Quit to Title")


def draw_settings(surface: pygame.Surface) -> None:
    ui.draw_shade(surface)
    rects = ui.settings_rects(surface)
    ui.draw_panel(surface, rects["panel"])
    ui.draw_text(surface, "Settings", 30, center=(rects["panel"].centerx, rects["panel"].top + 42))
    ui.draw_text(
        surface,
        "（暂无设置项）",
        18,
        center=(rects["panel"].centerx, rects["panel"].top + 108),
        color=ui.DIM_TEXT,
    )
    ui.draw_button(surface, rects["back"], "Back")
