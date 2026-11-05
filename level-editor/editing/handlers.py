"""鼠标命中的分发：工具栏、新建菜单、详细面板、关卡设置。"""

from typing import TYPE_CHECKING

import pygame

from view.chrome import create_menu_rects, toolbar_rects
from view.modals import settings_geometry
from view.panel import (
    detail_button_rects,
    detail_image_rect,
    detail_pick_rect,
    detail_row_rects,
    detail_slot_rect,
    dropdown_rects,
    selection_panel_buttons,
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
        elif action == "view":
            editor.view_menu_open = not editor.view_menu_open
        return action
    return None


def handle_create_menu(editor: Editor, position: tuple, window_size: tuple, layout) -> bool:
    for rect, tool in create_menu_rects(editor.menu_origin, window_size):
        if rect.collidepoint(position):
            editor.start_creating(tool, layout)
            return True
    return False


def handle_dropdown_click(surface: pygame.Surface, editor: Editor, position: tuple) -> bool:
    """下拉列表展开时的点击：点中某项就选它；再点同一个字段收起；点别处也收起。"""
    field = editor.dropdown_field
    if field is None:
        return False
    for rect, _, value in dropdown_rects(surface, editor):
        if rect.collidepoint(position):
            editor.choose_dropdown(value)
            return True
    # 再点一次同一个字段：收起，并且把这次点击吃掉，免得面板又把它展开
    for rect, index in detail_row_rects(surface, editor):
        if index == field and rect.collidepoint(position):
            editor.close_dropdown()
            return True
    editor.close_dropdown()
    return False


def handle_detail_click(surface: pygame.Surface, editor: Editor, position: tuple) -> None:
    """只处理落在面板里的点击；画布那边的点击照常走编辑流程。"""
    if editor.dialog is None:
        # 多选面板：只有「删除全部」和「取消」两个按钮
        delete_rect, close_rect = selection_panel_buttons(surface)
        if delete_rect.collidepoint(position):
            editor.delete_selection()
        elif close_rect.collidepoint(position):
            editor.clear_selection()
        return
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
    image_rect = detail_image_rect(surface, editor)
    if image_rect is not None and image_rect.collidepoint(position):
        editor.blur_name()
        editor.blur_number()
        editor.pick_texture_image()
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
        if editor.toggle_dropdown(index):
            return
        left, right = stepper_rects(rect)
        if left.collidepoint(position):
            editor.adjust_dialog(-1)
        elif right.collidepoint(position):
            editor.adjust_dialog(1)
        return


def handle_settings_click(surface: pygame.Surface, editor: Editor, position: tuple) -> None:
    (
        panel,
        name_rect,
        width_rect,
        height_rect,
        jump_rect,
        speed_rect,
        flip_up_rect,
        flip_down_rect,
        background_rect,
        browse_rect,
        apply_rect,
        cancel_rect,
    ) = settings_geometry(surface)
    if apply_rect.collidepoint(position):
        editor.close_settings(True)
        return
    if cancel_rect.collidepoint(position):
        editor.close_settings(False)
        return
    if name_rect.collidepoint(position):
        editor.settings_field = 0
        return
    if browse_rect.collidepoint(position):
        editor.pick_background()
        return
    if background_rect.collidepoint(position):
        editor.settings_field = 7
        return
    for field, rect in (
        (1, width_rect),
        (2, height_rect),
        (3, jump_rect),
        (4, speed_rect),
        (5, flip_up_rect),
        (6, flip_down_rect),
    ):
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
