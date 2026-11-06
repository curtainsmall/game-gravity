"""鼠标命中的分发：工具栏、关卡列表、新建菜单、详细面板、各种设置浮层。"""

from typing import TYPE_CHECKING

import pygame

from core.constants import ROW_HEIGHT
from view.chrome import create_menu_rects, toolbar_rects
from view.modals import (
    game_settings_geometry,
    level_select_geometry,
    settings_geometry,
    sound_geometry,
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


def handle_toolbar(editor: Editor, position: tuple, window_width: int) -> str | None:
    for rect, _, action in toolbar_rects(editor, window_width):
        if not rect.collidepoint(position):
            continue
        if action == "files":
            editor.file_menu_open = not editor.file_menu_open
            editor.view_menu_open = False
        elif action == "game_settings":
            editor.open_game_settings()
        elif action == "save":
            editor.save()
        elif action == "undo":
            editor.undo()
        elif action == "settings":
            editor.open_settings()
        elif action == "sound":
            editor.open_sound()
        elif action == "view":
            editor.view_menu_open = not editor.view_menu_open
            editor.file_menu_open = False
        return action
    return None


def handle_level_select_click(
    surface: pygame.Surface, editor: Editor, position: tuple
) -> None:
    """关卡列表浮层：点一行就切过去，另有「新建关卡」和「关闭」。"""
    files = editor.level_files()
    panel, area, rows_visible, create_rect, close_rect = level_select_geometry(surface, len(files))
    if create_rect.collidepoint(position):
        editor.create_level()
        return
    if close_rect.collidepoint(position) or not panel.collidepoint(position):
        editor.level_select_open = False
        return
    if not area.collidepoint(position):
        return
    scroll = max(0, min(editor.level_select_scroll, max(0, len(files) - rows_visible)))
    row = (position[1] - area.top) // ROW_HEIGHT
    index = scroll + int(row)
    if 0 <= index < len(files):
        editor.choose_level(files[index])


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
        if editor.dialog_checkbox(index) is not None:
            # 复选框：点整行就地勾上或取消
            editor.adjust_dialog(1)
            return
        if editor.toggle_dropdown(index):
            return
        left, right = stepper_rects(rect)
        if left.collidepoint(position):
            editor.adjust_dialog(-1)
        elif right.collidepoint(position):
            editor.adjust_dialog(1)
        return


def handle_settings_click(surface: pygame.Surface, editor: Editor, position: tuple) -> None:
    """关卡设置浮层：切页签、点字段、浏览图片/曲子、试听、应用/取消。"""
    geometry = settings_geometry(surface, editor.settings_tab)
    if geometry["apply"].collidepoint(position):
        editor.close_settings(True)
        return
    if geometry["cancel"].collidepoint(position):
        editor.close_settings(False)
        return
    for rect, index in geometry["tabs"]:
        if rect.collidepoint(position):
            editor.select_settings_tab(index)
            return
    if geometry["browse"] is not None and geometry["browse"].collidepoint(position):
        editor.pick_background()
        return
    if geometry["audio_browse"] is not None and geometry["audio_browse"].collidepoint(position):
        editor.pick_level_audio()
        return
    if geometry["audio_preview"] is not None and geometry["audio_preview"].collidepoint(position):
        editor.preview_level_audio()
        return
    for field, rect in geometry["rows"].items():
        if not rect.collidepoint(position):
            continue
        editor.settings_field = field
        if field == 9:                      # 循环播放：点整行切换
            editor.adjust_settings(1)
            return
        left, right = stepper_rects(rect)
        if left.collidepoint(position):
            editor.adjust_settings(-1)
        elif right.collidepoint(position):
            editor.adjust_settings(1)
        return
    if not geometry["panel"].collidepoint(position):
        editor.close_settings(False)


def handle_game_settings_click(
    surface: pygame.Surface, editor: Editor, position: tuple
) -> None:
    """游戏配置浮层：点哪一格就编辑哪一格，改完点「应用」写进 game.json。

    版权卡片上，名字行尾的「−」删掉那个名字，卡片底下的「＋」加一个空名字。
    """
    (
        panel,
        title_rect,
        _,
        jump_rect,
        speed_rect,
        _,
        _,
        layouts,
        _,
        add_rect,
        remove_rect,
        apply_rect,
        cancel_rect,
    ) = game_settings_geometry(surface, editor.game_cards, editor.game_card_scroll)
    if apply_rect.collidepoint(position):
        editor.close_game_settings(True)
        return
    if cancel_rect.collidepoint(position):
        editor.close_game_settings(False)
        return
    if add_rect.collidepoint(position):
        editor.add_credit_card()
        return
    if remove_rect.collidepoint(position):
        editor.remove_credit_card()
        return
    if title_rect.collidepoint(position):
        editor.game_field = 0
        return
    for field, rect in ((1, jump_rect), (2, speed_rect)):
        if not rect.collidepoint(position):
            continue
        editor.game_field = field
        left, right = stepper_rects(rect)
        if left.collidepoint(position):
            editor.adjust_game_number(-1)
        elif right.collidepoint(position):
            editor.adjust_game_number(1)
        return
    cells = editor.game_cells()
    for layout in layouts:
        index = layout["index"]
        for line, rect in enumerate(layout["minus"]):
            if rect.collidepoint(position):
                editor.remove_credit_name(index, line)
                return
        if layout["plus"].collidepoint(position):
            editor.add_credit_name(index)
            return
        if layout["job"].collidepoint(position):
            editor.game_field = cells.index(("job", index))
            return
        for line, rect in enumerate(layout["names"]):
            if rect.collidepoint(position):
                editor.game_field = cells.index(("name", index, line))
                return
    if not panel.collidepoint(position):
        editor.close_game_settings(False)


def handle_sound_click(surface: pygame.Surface, editor: Editor, position: tuple) -> None:
    """声音浮层：切页签、改这一页的字段、浏览、试听、应用/取消。

    玩家那一页还没有内容，点它只有页签和按钮有用。
    """
    geometry = sound_geometry(surface, editor.sound_tabs or [], editor.sound_index)
    panel = geometry["panel"]
    if geometry["apply"].collidepoint(position):
        editor.close_sound(True)
        return
    if geometry["cancel"].collidepoint(position):
        editor.close_sound(False)
        return
    for rect, index in geometry["tabs"]:
        if rect.collidepoint(position):
            editor.select_sound_tab(index)
            return
    if editor.sound_available():
        if geometry["path"].collidepoint(position):
            editor.sound_focus = 0
            return
        if geometry["browse"].collidepoint(position):
            editor.pick_audio()
            return
        if geometry["preview"].collidepoint(position):
            editor.preview_sound()
            return
        if geometry["loop"].collidepoint(position):
            editor.toggle_sound_loop()
            return
        for field, rect in ((2, geometry["fade_in"]), (3, geometry["fade_out"])):
            if not rect.collidepoint(position):
                continue
            editor.sound_focus = field
            left, right = stepper_rects(rect)
            if left.collidepoint(position):
                editor.adjust_sound_value(-1)
            elif right.collidepoint(position):
                editor.adjust_sound_value(1)
            return
    if not panel.collidepoint(position):
        editor.close_sound(False)


def handle_switch_click(surface: pygame.Surface, editor: Editor, position: tuple) -> None:
    """有没保存的修改时要走开的确认：保存并切换 / 不保存切换 / 取消。"""
    panel, save_rect, discard_rect, cancel_rect = switch_geometry(surface)
    if save_rect.collidepoint(position):
        editor.resolve_pending_switch(True)
    elif discard_rect.collidepoint(position):
        editor.resolve_pending_switch(False)
    elif cancel_rect.collidepoint(position) or not panel.collidepoint(position):
        editor.resolve_pending_switch(None)
