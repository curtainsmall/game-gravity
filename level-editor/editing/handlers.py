"""鼠标命中的分发：工具栏、关卡列表、新建菜单、详细面板、各种设置浮层。"""

from typing import TYPE_CHECKING

import pygame

from core.constants import ROW_HEIGHT
from view.chrome import create_menu_rects, toolbar_rects
from view.modals import (
    game_settings_geometry,
    level_select_geometry,
    player_settings_geometry,
    settings_geometry,
    switch_geometry,
)
from view.panel import (
    detail_button_rects,
    detail_image_rect,
    detail_row_rects,
    detail_slot_rect,
    dropdown_rects,
    selection_panel_buttons,
)
from view.widgets import stepper_rects

if TYPE_CHECKING:
    from editing.editor import Editor


def handle_toolbar(editor: Editor, position: tuple) -> str | None:
    for rect, _, action in toolbar_rects(editor):
        if not rect.collidepoint(position):
            continue
        if action == "open_game":
            editor.request_open_game()
        elif action == "game_settings":
            editor.open_game_settings()
        elif action == "save":
            editor.save()
        elif action == "levels":
            editor.open_level_select()
        elif action == "undo":
            editor.undo()
        elif action == "settings":
            editor.open_settings()
        elif action == "player_settings":
            editor.open_player_settings()
        elif action == "view":
            editor.view_menu_open = not editor.view_menu_open
        return action
    return None


def handle_level_select_click(
    surface: pygame.Surface, editor: Editor, position: tuple
) -> None:
    """关卡列表浮层：点一行就切过去，另有「新建关卡」和「关闭」。"""
    folders = editor.level_folders()
    panel, area, rows_visible, create_rect, close_rect = level_select_geometry(surface, len(folders))
    if create_rect.collidepoint(position):
        editor.create_level()
        return
    if close_rect.collidepoint(position) or not panel.collidepoint(position):
        editor.level_select_open = False
        return
    if not area.collidepoint(position):
        return
    scroll = max(0, min(editor.level_select_scroll, max(0, len(folders) - rows_visible)))
    row = (position[1] - area.top) // ROW_HEIGHT
    index = scroll + int(row)
    if 0 <= index < len(folders):
        editor.choose_level(folders[index])


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
        editor.settings_field = 5
        return
    for field, rect in (
        (1, width_rect),
        (2, height_rect),
        (3, flip_up_rect),
        (4, flip_down_rect),
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


def handle_player_settings_click(
    surface: pygame.Surface, editor: Editor, position: tuple
) -> None:
    """玩家设置浮层：跳高、移动速度，加减和「应用 / 取消」都在这里。"""
    panel, jump_rect, speed_rect, _, apply_rect, cancel_rect = player_settings_geometry(surface)
    if apply_rect.collidepoint(position):
        editor.close_player_settings(True)
        return
    if cancel_rect.collidepoint(position):
        editor.close_player_settings(False)
        return
    for field, rect in ((0, jump_rect), (1, speed_rect)):
        if not rect.collidepoint(position):
            continue
        editor.player_settings_field = field
        left, right = stepper_rects(rect)
        if left.collidepoint(position):
            editor.adjust_player_settings(-1)
        elif right.collidepoint(position):
            editor.adjust_player_settings(1)
        return
    if not panel.collidepoint(position):
        editor.close_player_settings(False)


def handle_game_settings_click(
    surface: pygame.Surface, editor: Editor, position: tuple
) -> None:
    """游戏设置浮层：点哪一格就编辑哪一格，改完点「应用」写进 game.json。"""
    (
        panel,
        title_rect,
        _,
        job_rects,
        name_rects,
        add_rect,
        remove_rect,
        apply_rect,
        cancel_rect,
    ) = game_settings_geometry(surface, len(editor.game_rows))
    if apply_rect.collidepoint(position):
        editor.close_game_settings(True)
        return
    if cancel_rect.collidepoint(position):
        editor.close_game_settings(False)
        return
    if add_rect.collidepoint(position):
        editor.add_credit_row()
        return
    if remove_rect.collidepoint(position):
        editor.remove_credit_row()
        return
    if title_rect.collidepoint(position):
        editor.game_field = 0
        return
    for index, rect in enumerate(job_rects):
        if rect.collidepoint(position):
            editor.game_field = 1 + 2 * index
            return
    for index, rect in enumerate(name_rects):
        if rect.collidepoint(position):
            editor.game_field = 2 + 2 * index
            return
    if not panel.collidepoint(position):
        editor.close_game_settings(False)


def handle_switch_click(surface: pygame.Surface, editor: Editor, position: tuple) -> None:
    """有没保存的修改时要走开的确认：保存并切换 / 不保存切换 / 取消。"""
    panel, save_rect, discard_rect, cancel_rect = switch_geometry(surface)
    if save_rect.collidepoint(position):
        editor.resolve_pending_switch(True)
    elif discard_rect.collidepoint(position):
        editor.resolve_pending_switch(False)
    elif cancel_rect.collidepoint(position) or not panel.collidepoint(position):
        editor.resolve_pending_switch(None)
