"""一帧的绘制顺序。"""

from typing import TYPE_CHECKING

import pygame

from core.constants import BACKGROUND, FOOTER, MARGIN, STATUS_TEXT
from view.canvas import draw_canvas, draw_ruler
from view.chrome import draw_create_menu, draw_header, draw_view_menu
from view.layout import Layout
from view.modals import (
    draw_game_settings,
    draw_level_select,
    draw_quit_confirm,
    draw_settings,
    draw_startup,
    draw_switch_confirm,
)
from view.panel import draw_detail_panel, draw_selection_panel

if TYPE_CHECKING:
    from editing.editor import Editor


def draw(surface: pygame.Surface, editor: "Editor", font: pygame.font.Font, layout: Layout) -> None:
    surface.fill(BACKGROUND)
    # 视图里没有关卡时画布是空的：连网格和刻度都不画
    if editor.level_in_view:
        draw_canvas(surface, editor, layout)
        draw_ruler(surface, layout, font)
    draw_header(surface, editor, layout, font)
    surface.blit(font.render(editor.status, True, STATUS_TEXT), (MARGIN, surface.get_height() - FOOTER + 6))

    if editor.menu_open:
        draw_create_menu(surface, editor, font)
    if editor.view_menu_open:
        draw_view_menu(surface, editor, font)
    if editor.dialog is not None:
        draw_detail_panel(surface, editor, font)
    elif len(editor.selection) > 1:
        draw_selection_panel(surface, editor, font)
    if editor.settings is not None:
        draw_settings(surface, editor, font)
    if editor.game_settings is not None:
        draw_game_settings(surface, editor, font)
    if editor.startup:
        draw_startup(surface, font)
    if editor.level_select_open:
        draw_level_select(surface, editor, font)
    if editor.pending_switch is not None:
        draw_switch_confirm(surface, editor, font)
    if editor.confirm_quit:
        draw_quit_confirm(surface, editor, font)
