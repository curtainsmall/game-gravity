"""鼠标命中的分发：工具栏、关卡列表、新建菜单、详细面板、各种设置浮层。"""

from typing import TYPE_CHECKING

import pygame

from core.constants import ROW_HEIGHT
from core.animation import PRESET_GENERAL, PRESET_PLAYER
from view.animation import animation_edit_geometry, animation_link_geometry
from view.chrome import create_menu_rects, toolbar_rects
from view.modals import (
    game_settings_geometry,
    level_select_geometry,
    level_select_scroll,
    settings_geometry,
    switch_geometry,
)
from view.panel import (
    detail_button_rects,
    detail_image_rect,
    detail_panel_rect,
    detail_row_rects,
    detail_slot_rect,
    detail_viewport,
    dropdown_rects,
    field_rect,
    selection_panel_buttons,
    trigger_geometry,
)
from view.picker import pick_menu_rects
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
    scroll = level_select_scroll(editor, len(files), area)
    index = int((position[1] - area.top + scroll) // ROW_HEIGHT)
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
    same = field_rect(surface, editor, field)
    if same is not None and same.collidepoint(position):
        editor.close_dropdown()
        return True
    editor.close_dropdown()
    return False


def handle_pick_menu_click(surface: pygame.Surface, editor: Editor, position: tuple) -> bool:
    """取对象列表：点中一行就选中它并吃掉点击；点别处只把列表关掉，点击继续照常处理。"""
    for rect, index in pick_menu_rects(surface, editor):
        if rect.collidepoint(position):
            editor.choose_pick(index)
            return True
    editor.close_pick_menu()
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
    delete_rect, close_rect, copy_rect = detail_button_rects(surface, editor)
    if copy_rect is not None and copy_rect.collidepoint(position):
        editor.duplicate_selection()
        return
    if delete_rect.collidepoint(position):
        kind, entry = editor.dialog["kind"], editor.dialog["entry"]
        editor.delete_entry(kind, entry)
        return
    if close_rect.collidepoint(position):
        editor.close_dialog()
        return
    if not detail_viewport(detail_panel_rect(surface)).collidepoint(position):
        return                      # 内容区外面（底部按钮那条、标题）不参与命中
    image_rect = detail_image_rect(surface, editor)
    if image_rect is not None and image_rect.collidepoint(position):
        editor.blur_name()
        editor.blur_number()
        editor.pick_texture_image()
        return
    anim_link = detail_slot_rect(surface, editor, "anim_link")
    if anim_link is not None and anim_link.collidepoint(position):
        editor.blur_name()
        editor.blur_number()
        if editor.dialog is not None:
            editor.open_animation_link(editor.dialog["entry"])
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
        if not editor.dialog_focusable(index):
            return                      # 纯显示的行（贴图路径）点不中
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

    trigger = trigger_geometry(surface, editor)
    if trigger is None:
        return
    if trigger["add"].collidepoint(position):
        editor.add_trigger_card()
        return
    for layout in trigger["cards"]:
        if layout["minus"].collidepoint(position):
            editor.remove_trigger_card(layout["index"])
            return
        for part in ("source", "behavior", "mode"):
            if not layout[part].collidepoint(position):
                continue
            editor.blur_name()
            editor.blur_number()
            field = editor.trigger_field(layout["index"], part)
            editor.dialog_field = field
            editor.toggle_dropdown(field)
            return


def handle_cutscene_click(editor: Editor, position: tuple, page: dict) -> None:
    """过场页：级联、声音的三种模式与自定曲子，以及每张图片卡片上的按钮和格子。

    点中哪一格就把光标挪过去；时间格子上的加减和卡片右上角的 ↑ ↓ − 各管各的。
    """
    if page["cascade"].collidepoint(position):
        editor.set_cutscene_cascade()
        return
    for mode, rect in page["sound_modes"].items():
        if rect.collidepoint(position):
            editor.set_cutscene_sound_mode(mode)
            return
    if page["sound_browse"] is not None and page["sound_browse"].collidepoint(position):
        editor.pick_cutscene_sound()
        return
    if page["sound_preview"] is not None and page["sound_preview"].collidepoint(position):
        editor.preview_cutscene_sound()
        return
    if page["sound_path"] is not None and page["sound_path"].collidepoint(position):
        editor.set_cutscene_field(("sound_bgm",))
        return
    if page["sound_loop"] is not None and page["sound_loop"].collidepoint(position):
        editor.set_cutscene_field(("sound_loop",))
        editor.adjust_cutscene(1)       # 循环：点整格切换
        return
    for cell, rect in (
        (("sound_fade_in",), page["sound_fade_in"]),
        (("sound_fade_out",), page["sound_fade_out"]),
    ):
        if rect is None or not rect.collidepoint(position):
            continue
        editor.set_cutscene_field(cell)
        left, right = stepper_rects(rect)
        if left.collidepoint(position):
            editor.adjust_cutscene(-1)
        elif right.collidepoint(position):
            editor.adjust_cutscene(1)
        return
    if page["add"].collidepoint(position):
        editor.add_cutscene_picture()
        return
    if not page["cards_area"].collidepoint(position):
        return                      # 滚动区外面的那半张卡片点不中
    for layout in page["cards"]:
        index = layout["index"]
        if layout["browse"].collidepoint(position):
            editor.pick_cutscene_image(index)
            return
        if layout["up"].collidepoint(position):
            editor.move_cutscene_picture(index, -1)
            return
        if layout["down"].collidepoint(position):
            editor.move_cutscene_picture(index, 1)
            return
        if layout["remove"].collidepoint(position):
            editor.remove_cutscene_picture(index)
            return
        if layout["path"].collidepoint(position):
            editor.set_cutscene_field(("path", index))
            return
        for cell, rect in (
            (("fade_in", index), layout["fade_in"]),
            (("hold", index), layout["hold"]),
            (("fade_out", index), layout["fade_out"]),
        ):
            if not rect.collidepoint(position):
                continue
            editor.set_cutscene_field(cell)
            left, right = stepper_rects(rect)
            if left.collidepoint(position):
                editor.adjust_cutscene(-1)
            elif right.collidepoint(position):
                editor.adjust_cutscene(1)
            return


def handle_settings_click(surface: pygame.Surface, editor: Editor, position: tuple) -> None:
    """关卡设置浮层：切页签、点字段、浏览图片/曲子、试听、应用/取消。"""
    geometry = settings_geometry(surface, editor)
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
    if editor.settings_cutscene_tab():
        handle_cutscene_click(editor, position, geometry["cutscene"])
        if not geometry["panel"].collidepoint(position):
            editor.close_settings(False)
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


def handle_library_click(editor: Editor, position: tuple, page: dict) -> None:
    """动画集页：点「新建动画」或点一行打开编辑弹窗。"""
    if page["new"].collidepoint(position):
        editor.open_animation_edit(None)
        return
    for row in page["rows"]:
        if row["rect"].collidepoint(position):
            editor.select_animation_key(row["key"])
            editor.open_animation_edit(row["key"])
            return


def handle_animation_edit_click(
    surface: pygame.Surface, editor: Editor, position: tuple
) -> None:
    """单条动画的编辑弹窗：改名字、帧、时长、循环、预览、删除、确定/取消。"""
    if editor.animation_edit is None:
        return
    editor.commit_animation_delay()
    geometry = animation_edit_geometry(surface, editor)
    if geometry.get("panel") is None:
        return
    if geometry["name"].collidepoint(position):
        editor.focus_animation_name()
        return
    editor.blur_animation_name()
    for cell in geometry["cells"]:
        if cell["delay"].collidepoint(position):
            editor.begin_animation_delay_edit(cell["index"])
            return
    if geometry["add"].collidepoint(position):
        editor.add_animation_frames()
        return
    if geometry["remove"].collidepoint(position):
        editor.remove_animation_frame()
        return
    if geometry["preview"].collidepoint(position):
        editor.toggle_animation_edit_preview()
        return
    if geometry["delete"].collidepoint(position):
        original = editor.animation_edit["original"]
        if original:
            editor.delete_animation(original)
        else:
            editor.close_animation_edit(False)
        return
    if geometry["ok"].collidepoint(position):
        editor.close_animation_edit(True)
        return
    if geometry["cancel"].collidepoint(position):
        editor.close_animation_edit(False)
        return
    for cell in geometry["cells"]:
        if cell["thumb"].collidepoint(position):
            editor.select_animation_frame(cell["index"])
            editor.begin_animation_frame_drag(cell["index"], position)
            return


def handle_animation_edit_drag_motion(
    surface: pygame.Surface, editor: Editor, position: tuple
) -> None:
    """编辑弹窗里拖动帧：按格子区的位置换算插入点。"""
    if editor.animation_edit is None or editor.animation_edit["drag"] is None:
        return
    editor.update_animation_frame_drag(position, animation_edit_geometry(surface, editor))


def handle_animation_edit_drag_release(editor: Editor) -> None:
    editor.finish_animation_frame_drag()


def handle_animation_link_click(
    surface: pygame.Surface, editor: Editor, position: tuple
) -> None:
    """动画对象的链接弹窗：预设下拉、动作左右下拉、确定/取消。"""
    link = editor.animation_link
    if link is None:
        return
    geometry = animation_link_geometry(surface, editor)
    if geometry["popup"] is not None:
        for rect, _, value in geometry["popup_rects"]:
            if rect.collidepoint(position):
                if link["dropdown"] == "preset":
                    editor.set_animation_link_preset(value)
                else:
                    editor.choose_animation_link(value)
                return
        editor.close_animation_link_dropdown()
        return
    if geometry["preset"].collidepoint(position):
        editor.toggle_animation_link_dropdown("preset")
        return
    for row in geometry["rows"]:
        if row["kind"] == "general":
            if row["loop"].collidepoint(position):
                editor.toggle_animation_link_loop((PRESET_GENERAL, "", ""))
                return
            if row["field"].collidepoint(position):
                editor.toggle_animation_link_dropdown((PRESET_GENERAL, "", ""))
                return
        else:
            if row["left_loop"].collidepoint(position):
                editor.toggle_animation_link_loop(
                    (PRESET_PLAYER, row["action"], "left")
                )
                return
            if row["right_loop"].collidepoint(position):
                editor.toggle_animation_link_loop(
                    (PRESET_PLAYER, row["action"], "right")
                )
                return
            if row["left"].collidepoint(position):
                editor.toggle_animation_link_dropdown(
                    (PRESET_PLAYER, row["action"], "left")
                )
                return
            if row["right"].collidepoint(position):
                editor.toggle_animation_link_dropdown(
                    (PRESET_PLAYER, row["action"], "right")
                )
                return
    if geometry["ok"].collidepoint(position):
        editor.close_animation_link(True)
        return
    if geometry["cancel"].collidepoint(position) or not geometry["panel"].collidepoint(position):
        editor.close_animation_link(False)


def handle_game_settings_click(
    surface: pygame.Surface, editor: Editor, position: tuple
) -> None:
    """游戏配置浮层：切页签、点格子、浏览/试听、增删职位，最后应用或取消。

    制作名单卡片上，名字行尾的「−」删掉那个名字，卡片底下的「＋」加一个空名字。
    """
    geometry = game_settings_geometry(surface, editor)
    panel = geometry["panel"]
    if editor.animation_edit is not None:
        handle_animation_edit_click(surface, editor, position)
        return
    # 正在改某一帧的时长：点到别的任何地方就先把它收下
    if editor.animation_delay_active():
        page = geometry["animation"]
        hit = page is not None and any(
            delay["rect"].collidepoint(position) for delay in page["delays"]
        )
        if not hit:
            editor.commit_animation_delay()
    if geometry["apply"].collidepoint(position):
        editor.close_game_settings(True)
        return
    if geometry["cancel"].collidepoint(position):
        editor.close_game_settings(False)
        return
    for rect, index in geometry["tabs"]:
        if rect.collidepoint(position):
            editor.select_game_tab(index)
            return

    if editor.game_cutscene_tab():
        handle_cutscene_click(editor, position, geometry["cutscene"])
        if not panel.collidepoint(position):
            editor.close_game_settings(False)
        return
    if editor.game_animation_tab():
        handle_library_click(editor, position, geometry["animation"])
        if not panel.collidepoint(position):
            editor.close_game_settings(False)
        return

    cells = editor.game_cells()
    if editor.game_tab == 0:
        for background in geometry["backgrounds"]:
            if background["browse"].collidepoint(position):
                editor.pick_game_background(background["key"])
                return
            if background["text"].collidepoint(position):
                editor.game_field = cells.index((f"{background['key']}_bg",))
                return
        for cell, rect in (
            (("title",), geometry["rows"]["title"]),
            (("jump",), geometry["rows"]["jump"]),
            (("speed",), geometry["rows"]["speed"]),
        ):
            if not rect.collidepoint(position):
                continue
            editor.game_field = cells.index(cell)
            left, right = stepper_rects(rect)
            if left.collidepoint(position):
                editor.adjust_game_number(-1)
            elif right.collidepoint(position):
                editor.adjust_game_number(1)
            return
    elif editor.game_tab == 2:
        if geometry["add"].collidepoint(position):
            editor.add_credit_card()
            return
        if geometry["remove"].collidepoint(position):
            editor.remove_credit_card()
            return
        if not geometry["cards_area"].collidepoint(position):
            return                  # 卡片区外面（藏在滚动区外的那部分）点不中
        for layout in geometry["layouts"]:
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
    else:
        for scene in geometry["scenes"]:
            key = scene["key"]
            if scene["browse"].collidepoint(position):
                editor.pick_game_audio(key)
                return
            if scene["preview"].collidepoint(position):
                editor.preview_game_audio(key)
                return
            if scene["path"].collidepoint(position):
                editor.game_field = cells.index(("bgm", key))
                return
            if scene["loop"].collidepoint(position):
                editor.game_field = cells.index(("loop", key))
                editor.adjust_game_number(1)
                return
            for field, rect in (
                ("fade_in", scene["fade_in"]),
                ("fade_out", scene["fade_out"]),
            ):
                if not rect.collidepoint(position):
                    continue
                editor.game_field = cells.index((field, key))
                left, right = stepper_rects(rect)
                if left.collidepoint(position):
                    editor.adjust_game_number(-1)
                elif right.collidepoint(position):
                    editor.adjust_game_number(1)
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
