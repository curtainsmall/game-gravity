"""浮层：启动窗、关卡设置、退出确认。"""

from typing import TYPE_CHECKING

import pygame

from core.constants import (
    BUTTON_BG,
    BUTTON_HEIGHT,
    DIALOG_BORDER,
    DIM_TEXT,
    HIGHLIGHT,
    ROW_HEIGHT,
    TEXT,
)
from core.helpers import display_path
from view.widgets import draw_button, draw_panel, draw_stepper, place_panel, stepper_rects

if TYPE_CHECKING:
    from editing.editor import Editor


def startup_rects(surface: pygame.Surface) -> list:
    panel = pygame.Rect(0, 0, 320, 140)
    panel.center = (surface.get_width() // 2, surface.get_height() // 2)
    return [
        (pygame.Rect(panel.left + 24, panel.top + 70, 120, 32), "new"),
        (pygame.Rect(panel.right - 144, panel.top + 70, 120, 32), "open"),
    ]


def settings_geometry(surface: pygame.Surface) -> tuple:
    panel = place_panel(surface, pygame.Rect(0, 0, 440, 172))
    name_rect = pygame.Rect(panel.left + 12, panel.top + 38, panel.width - 24, ROW_HEIGHT + 2)
    jump_rect = pygame.Rect(panel.left + 12, panel.top + 72, panel.width - 24, ROW_HEIGHT + 2)
    button_y = panel.bottom - BUTTON_HEIGHT - 8
    apply_rect = pygame.Rect(panel.right - 12 - 140, button_y, 68, BUTTON_HEIGHT)
    cancel_rect = pygame.Rect(panel.right - 12 - 68, button_y, 68, BUTTON_HEIGHT)
    return panel, name_rect, jump_rect, apply_rect, cancel_rect


def _draw_settings_row(
    surface: pygame.Surface,
    font: pygame.font.Font,
    rect: pygame.Rect,
    label: str,
    value,
    selected: bool,
) -> None:
    pygame.draw.rect(surface, (62, 62, 72) if selected else (48, 48, 54), rect)
    pygame.draw.rect(surface, HIGHLIGHT if selected else (86, 86, 94), rect, 1)
    text = font.render(f"{label}: {value}", True, HIGHLIGHT if selected else TEXT)
    surface.blit(text, (rect.left + 6, rect.centery - text.get_height() // 2))


def draw_settings(surface: pygame.Surface, editor: Editor, font: pygame.font.Font) -> None:
    panel, name_rect, jump_rect, apply_rect, cancel_rect = settings_geometry(surface)
    draw_panel(surface, panel)

    surface.blit(font.render("关卡设置", True, TEXT), (panel.left + 12, panel.top + 8))
    hint = font.render("点击面板外取消", True, DIM_TEXT)
    surface.blit(hint, (panel.right - 12 - hint.get_width(), panel.top + 8))

    name = editor.settings["name"]
    name_selected = editor.settings_field == 0
    pygame.draw.rect(surface, (62, 62, 72) if name_selected else (48, 48, 54), name_rect)
    pygame.draw.rect(surface, HIGHLIGHT if name_selected else (86, 86, 94), name_rect, 1)
    caret = "|" if name_selected else ""
    text = font.render(f"名称: {name if name else '（空）'}{caret}", True, HIGHLIGHT if name_selected else TEXT)
    clip = max(1, name_rect.width - 12)
    surface.blit(
        text,
        (name_rect.left + 6, name_rect.centery - text.get_height() // 2),
        (0, 0, min(text.get_width(), clip), text.get_height()),
    )

    jump_selected = editor.settings_field == 1
    _draw_settings_row(
        surface, font, jump_rect, "初始跳高", editor.settings["jump_height"], jump_selected
    )
    left, right = stepper_rects(jump_rect)
    draw_stepper(surface, left, -1)
    draw_stepper(surface, right, 1)

    draw_button(surface, font, apply_rect, "应用")
    draw_button(surface, font, cancel_rect, "取消")


def quit_geometry(surface: pygame.Surface) -> tuple:
    panel = place_panel(surface, pygame.Rect(0, 0, 430, 152))
    button_y = panel.bottom - 12 - BUTTON_HEIGHT
    quit_rect = pygame.Rect(panel.right - 12 - 120, button_y, 120, BUTTON_HEIGHT)
    cancel_rect = pygame.Rect(quit_rect.left - 10 - 76, button_y, 76, BUTTON_HEIGHT)
    return panel, quit_rect, cancel_rect


def draw_quit_confirm(surface: pygame.Surface, editor: Editor, font: pygame.font.Font) -> None:
    panel, quit_rect, cancel_rect = quit_geometry(surface)
    draw_panel(surface, panel)

    surface.blit(font.render("关卡还没保存", True, HIGHLIGHT), (panel.left + 14, panel.top + 12))
    surface.blit(
        font.render(display_path(editor.path), True, DIM_TEXT), (panel.left + 14, panel.top + 40)
    )
    surface.blit(
        font.render("有未保存的修改，确定要退出吗？", True, TEXT), (panel.left + 14, panel.top + 62)
    )
    hint = font.render("Enter 退出    Esc 取消", True, DIM_TEXT)
    surface.blit(hint, (panel.left + 14, panel.top + 88))

    draw_button(surface, font, quit_rect, "退出不保存")
    draw_button(surface, font, cancel_rect, "取消")


def draw_startup(surface: pygame.Surface, font: pygame.font.Font) -> None:
    panel = place_panel(surface, pygame.Rect(0, 0, 320, 140))
    draw_panel(surface, panel)
    title = font.render("关卡编辑器", True, TEXT)
    surface.blit(title, (panel.centerx - title.get_width() // 2, panel.top + 16))
    sub = font.render("新建一个关卡，或打开已有关卡文件", True, DIM_TEXT)
    surface.blit(sub, (panel.centerx - sub.get_width() // 2, panel.top + 42))
    for rect, action in startup_rects(surface):
        pygame.draw.rect(surface, BUTTON_BG, rect)
        pygame.draw.rect(surface, DIALOG_BORDER, rect, 1)
        label = "新建关卡" if action == "new" else "打开关卡"
        text = font.render(label, True, TEXT)
        surface.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))
