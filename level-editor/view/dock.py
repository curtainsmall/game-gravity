"""右侧常驻面板：顶上两个标签「属性」和「对象列表」，共用同一块地方。

属性页跟着选中项走（一个对象列属性、多选列清单、没选就提示），对象列表页把这一关
的所有对象列出来、按种类筛。两个页都只在视图里有关卡时出现；「视图」菜单里的
「侧栏」关掉时整块面板收起，画布铺满整个宽度。标签在面板最上面，最后画，压在
两个页自己的内容上面。
"""

from typing import TYPE_CHECKING

import pygame

from core.constants import (
    DIALOG_BG,
    DIALOG_BORDER,
    DIM_TEXT,
    DOCK_TAB_HEIGHT,
    HIGHLIGHT,
    MARGIN,
    TEXT,
)
from view.objects import draw_go_list
from view.panel import detail_panel_rect, detail_panel_width_for, draw_property_tab

if TYPE_CHECKING:
    from editing.editor import Editor

PANEL_TABS = (("properties", "属性"), ("objects", "对象列表"))


def dock_visible(editor: "Editor") -> bool:
    """右侧面板露不露出来：视图里有关卡，并且「视图」菜单里没把侧栏关掉。"""
    return bool(editor.level_in_view and editor.view_settings.get("dock", True))


def dock_reserved(editor: "Editor", window_width: int) -> int:
    """面板给画布右边留出多宽（含面板和画布之间那道缝）。"""
    if not dock_visible(editor):
        return 0
    return detail_panel_width_for(window_width) + MARGIN


def dock_tabs(surface: pygame.Surface) -> list:
    """面板顶上的两个标签：[(矩形, 页名, 文字)]。"""
    panel = detail_panel_rect(surface)
    width = panel.width // 2
    return [
        (
            pygame.Rect(panel.left + index * width, panel.top, width, DOCK_TAB_HEIGHT),
            key,
            label,
        )
        for index, (key, label) in enumerate(PANEL_TABS)
    ]


def dock_tab_at(surface: pygame.Surface, position: tuple) -> str | None:
    """点上落在哪个标签上；没点中就是 None。"""
    for rect, key, _ in dock_tabs(surface):
        if rect.collidepoint(position):
            return key
    return None


def draw_dock(
    surface: pygame.Surface, editor: "Editor", font: pygame.font.Font
) -> None:
    panel = detail_panel_rect(surface)
    pygame.draw.rect(surface, DIALOG_BG, panel)
    pygame.draw.rect(surface, DIALOG_BORDER, panel, 1)
    if editor.panel_tab == "objects":
        draw_go_list(surface, editor, font)
    else:
        draw_property_tab(surface, editor, font)
    _draw_tabs(surface, editor, font)


def _draw_tabs(
    surface: pygame.Surface, editor: "Editor", font: pygame.font.Font
) -> None:
    for rect, key, label in dock_tabs(surface):
        selected = key == editor.panel_tab
        pygame.draw.rect(surface, (62, 62, 72) if selected else (36, 36, 42), rect)
        pygame.draw.rect(surface, HIGHLIGHT if selected else DIALOG_BORDER, rect, 1)
        text = font.render(label, True, HIGHLIGHT if selected else TEXT)
        surface.blit(
            text,
            (
                rect.centerx - text.get_width() // 2,
                rect.centery - text.get_height() // 2,
            ),
        )
