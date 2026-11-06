"""面板、按钮、箭头这些绘制小件。"""

import pygame

from core.constants import (
    BUTTON_BG,
    DIALOG_BG,
    DIALOG_BORDER,
    FOOTER,
    HEADER,
    HIGHLIGHT,
    MARGIN,
    TEXT,
)


def draw_arrow(surface: pygame.Surface, rect: pygame.Rect, direction: int) -> None:
    inset = 6
    if direction < 0:
        points = [
            (rect.right - inset, rect.top + 5),
            (rect.right - inset, rect.bottom - 5),
            (rect.left + inset, rect.centery),
        ]
    else:
        points = [
            (rect.left + inset, rect.top + 5),
            (rect.left + inset, rect.bottom - 5),
            (rect.right - inset, rect.centery),
        ]
    pygame.draw.polygon(surface, TEXT, points)


def draw_stepper(surface: pygame.Surface, rect: pygame.Rect, direction: int) -> None:
    hovered = rect.collidepoint(pygame.mouse.get_pos())
    pygame.draw.rect(surface, (100, 100, 110) if hovered else BUTTON_BG, rect)
    pygame.draw.rect(surface, DIALOG_BORDER, rect, 1)
    draw_arrow(surface, rect, direction)


def draw_button(
    surface: pygame.Surface, font: pygame.font.Font, rect: pygame.Rect, caption: str
) -> None:
    hovered = rect.collidepoint(pygame.mouse.get_pos())
    pygame.draw.rect(surface, (100, 100, 110) if hovered else BUTTON_BG, rect)
    pygame.draw.rect(surface, DIALOG_BORDER, rect, 1)
    text = font.render(caption, True, TEXT)
    surface.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))


def draw_checkbox(
    surface: pygame.Surface,
    font: pygame.font.Font,
    rect: pygame.Rect,
    label: str,
    checked: bool,
    selected: bool = False,
    inset: int = 0,
) -> None:
    """复选框：一个小方框加说明文字，整行（rect）都是它的热区。

    勾没勾上只看 checked；selected 只改颜色，表示键盘光标停在这一行。
    """
    box = pygame.Rect(rect.left + inset, rect.centery - 8, 16, 16)
    pygame.draw.rect(surface, (62, 62, 72) if selected else (48, 48, 54), box)
    pygame.draw.rect(surface, HIGHLIGHT if selected else (86, 86, 94), box, 1)
    if checked:
        pygame.draw.lines(
            surface,
            HIGHLIGHT if selected else TEXT,
            False,
            [
                (box.left + 3, box.centery),
                (box.centerx, box.bottom - 4),
                (box.right - 3, box.top + 4),
            ],
            2,
        )
    text = font.render(label, True, HIGHLIGHT if selected else TEXT)
    surface.blit(text, (box.right + 8, rect.centery - text.get_height() // 2))


def stepper_rects(cell: pygame.Rect) -> tuple:
    """字段右侧的「减 / 加」两个小方块。"""
    step = 18
    right = pygame.Rect(cell.right - step - 2, cell.top + 1, step, cell.height - 2)
    left = pygame.Rect(right.left - step - 2, cell.top + 1, step, cell.height - 2)
    return left, right


def place_panel(surface: pygame.Surface, panel: pygame.Rect) -> pygame.Rect:
    """居中摆放，并夹在信息栏与状态栏之间。"""
    panel.center = (surface.get_width() // 2, surface.get_height() // 2)
    panel.top = max(HEADER + 4, min(panel.top, surface.get_height() - FOOTER - panel.height - 4))
    panel.left = max(MARGIN, min(panel.left, surface.get_width() - MARGIN - panel.width))
    return panel


def draw_panel(surface: pygame.Surface, panel: pygame.Rect) -> None:
    shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 130))
    surface.blit(shade, (0, 0))
    pygame.draw.rect(surface, DIALOG_BG, panel)
    pygame.draw.rect(surface, DIALOG_BORDER, panel, 1)
