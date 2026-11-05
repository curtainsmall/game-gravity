"""鼠标命中的分发：工具栏、新建菜单、详细面板、关卡设置。"""

from typing import TYPE_CHECKING

import pygame

from view.chrome import create_menu_rects, toolbar_rects
from view.modals import settings_geometry
from view.panel import (
    detail_button_rects,
    detail_pick_rect,
    detail_row_rects,
    detail_slot_rect,
)
from view.widgets import stepper_rects

if TYPE_CHECKING:
    from editing.editor import Editor


def handle_toolbar(editor: Editor, position: tuple) -> str | None:
    for rect, _, action in toolbar_rects():
        if not rect.collidepoint(position):
            continue
        if action == "new":
            editor.new_level()
        elif action == "open":
            editor.open_level()
        elif action == "save":
            editor.save()
        elif action == "undo":
            editor.undo()
        elif action == "settings":
            editor.open_settings()
        return action
    return None


def handle_create_menu(editor: Editor, position: tuple, window_size: tuple) -> bool:
    for rect, tool in create_menu_rects(editor.menu_origin, window_size):
        if rect.collidepoint(position):
            editor.start_creating(tool)
            return True
    return False


def handle_detail_click(surface: pygame.Surface, editor: Editor, position: tuple) -> None:
    """只处理落在面板里的点击；画布那边的点击照常走编辑流程。"""
    delete_rect, close_rect = detail_button_rects(surface)
    if delete_rect.collidepoint(position):
        kind, entry = editor.dialog["kind"], editor.dialog["entry"]
        editor.delete_entry(kind, entry)
        return
    if close_rect.collidepoint(position):
        editor.close_dialog()
        return
    pick_rect = detail_pick_rect(surface, editor)
    if pick_rect is not None and pick_rect.collidepoint(position):
        editor.blur_name()
        editor.begin_pick_offset()
        return
    name_rect = detail_slot_rect(surface, editor, "name")
    if name_rect is not None and name_rect.collidepoint(position):
        editor.focus_name()
        return
    for rect, index in detail_row_rects(surface, editor):
        if not rect.collidepoint(position):
            continue
        editor.blur_name()
        editor.blur_number()
        editor.dialog_field = index
        left, right = stepper_rects(rect)
        if left.collidepoint(position):
            editor.adjust_dialog(-1)
        elif right.collidepoint(position):
            editor.adjust_dialog(1)
        return


def handle_settings_click(surface: pygame.Surface, editor: Editor, position: tuple) -> None:
    panel, name_rect, width_rect, height_rect, jump_rect, apply_rect, cancel_rect = (
        settings_geometry(surface)
    )
    if apply_rect.collidepoint(position):
        editor.close_settings(True)
        return
    if cancel_rect.collidepoint(position):
        editor.close_settings(False)
        return
    if name_rect.collidepoint(position):
        editor.settings_field = 0
        return
    for field, rect in ((1, width_rect), (2, height_rect), (3, jump_rect)):
        if not rect.collidepoint(position):
            continue
        editor.settings_field = field
        left, right = stepper_rects(rect)
        if left.collidepoint(position):
            editor.adjust_settings(-1)
        elif right.collidepoint(position):
            editor.adjust_settings(1)
        return
    if not panel.collidepoint(position):
        editor.close_settings(False)
