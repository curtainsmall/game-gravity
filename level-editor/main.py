"""关卡编辑器的启动入口与主循环。

运行：uv run python level-editor/main.py
"""

import pygame

from core.constants import (
    DEFAULT_WINDOW,
    HEADER,
    MARGIN,
    MIN_WINDOW,
    ZOOM_STEP,
)
from editing.editor import Editor
from editing.handlers import (
    handle_animation_edit_drag_motion,
    handle_animation_edit_drag_release,
    handle_animation_link_click,
    handle_create_menu,
    handle_dock_click,
    handle_dropdown_click,
    handle_game_settings_click,
    handle_level_select_click,
    handle_pick_menu_click,
    handle_settings_click,
    handle_sound_link_click,
    handle_switch_click,
    handle_toolbar,
)
from view.chrome import handle_file_menu_click, handle_view_menu_click
from view.dock import dock_reserved, dock_visible
from view.frame import draw
from view.layout import Layout
from view.modals import quit_geometry, startup_rects
from view.panel import detail_panel_rect

MODIFIER_KEYS = (pygame.K_LCTRL, pygame.K_RCTRL, pygame.K_LSHIFT, pygame.K_RSHIFT)


def sync_modifiers(editor: Editor) -> None:
    """把 Shift / Ctrl / Alt 的当前状态同步给编辑器。"""
    mods = pygame.key.get_mods()
    editor.snapping = bool(mods & pygame.KMOD_SHIFT)
    editor.keep_ratio = bool(mods & pygame.KMOD_CTRL)
    editor.click_through = bool(mods & pygame.KMOD_ALT)


def run() -> None:
    pygame.init()
    pygame.display.set_caption("level editor")
    screen = pygame.display.set_mode(DEFAULT_WINDOW, pygame.RESIZABLE)
    font = pygame.font.SysFont("microsoftyahei", 14)
    clock = pygame.time.Clock()
    editor = Editor()

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        reserved_right = dock_reserved(editor, screen.get_width())
        layout = Layout(
            screen.get_size(),
            editor.zoom,
            editor.pan_x,
            editor.pan_y,
            reserved_right,
            cols=editor.level.width,
            rows=editor.level.height,
        )
        editor.pan_x, editor.pan_y = layout.pan_x, layout.pan_y

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if editor.request_quit():
                    running = False
            elif event.type == pygame.VIDEORESIZE:
                size = (max(MIN_WINDOW[0], event.w), max(MIN_WINDOW[1], event.h))
                screen = pygame.display.set_mode(size, pygame.RESIZABLE)
                reserved_right = dock_reserved(editor, size[0])
                layout = Layout(
                    size,
                    editor.zoom,
                    editor.pan_x,
                    editor.pan_y,
                    reserved_right,
                    cols=editor.level.width,
                    rows=editor.level.height,
                )
                editor.pan_x, editor.pan_y = layout.pan_x, layout.pan_y
            elif editor.confirm_quit:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_n):
                        editor.confirm_quit = False
                    elif event.key in (pygame.K_RETURN, pygame.K_y):
                        running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    panel, quit_rect, cancel_rect = quit_geometry(screen)
                    if quit_rect.collidepoint(event.pos):
                        running = False
                    elif cancel_rect.collidepoint(event.pos) or not panel.collidepoint(event.pos):
                        editor.confirm_quit = False
            elif editor.save_notice:
                # 存完的一句提示（缺起点/终点）：任何键或点击都关掉它，保存早就完成了
                if event.type == pygame.KEYDOWN or (
                    event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                ):
                    editor.close_save_notice()
            elif editor.startup:
                # 启动窗：先要一份 game.json（新建或打开），之后才有游戏和关卡
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if editor.request_quit():
                            running = False
                    elif event.key in (pygame.K_RETURN, pygame.K_n):
                        editor.create_game()
                    elif event.key == pygame.K_o:
                        editor.open_game()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for rect, action in startup_rects(screen):
                        if rect.collidepoint(event.pos):
                            editor.create_game() if action == "create" else editor.open_game()
                            break
            elif editor.sound_link is not None:
                # 声音对象的链接弹窗：Esc 取消、回车确定，滚轮翻声音下拉
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    editor.close_sound_link(False)
                elif event.type == pygame.KEYDOWN and event.key in (
                    pygame.K_RETURN,
                    pygame.K_KP_ENTER,
                ):
                    editor.close_sound_link(True)
                elif event.type == pygame.MOUSEWHEEL:
                    editor.scroll_sound_link_popup(-event.y)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    handle_sound_link_click(screen, editor, event.pos)
            elif editor.animation_link is not None:
                # 动画对象的链接弹窗：Esc 取消、回车确定，滚轮翻下拉列表
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    editor.close_animation_link(False)
                elif event.type == pygame.KEYDOWN and event.key in (
                    pygame.K_RETURN,
                    pygame.K_KP_ENTER,
                ):
                    editor.close_animation_link(True)
                elif event.type == pygame.MOUSEWHEEL:
                    editor.scroll_animation_link_popup(-event.y)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    handle_animation_link_click(screen, editor, event.pos)
            elif editor.level_select_open:
                # 关卡列表：点一行切过去，另有「新建关卡」「关闭」，滚轮上下滚
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        editor.level_select_open = False
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        editor.create_level()
                    elif event.key == pygame.K_UP:
                        editor.scroll_level_select(-1)
                    elif event.key == pygame.K_DOWN:
                        editor.scroll_level_select(1)
                elif event.type == pygame.MOUSEWHEEL:
                    editor.scroll_level_select(-event.y)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    handle_level_select_click(screen, editor, event.pos)
            elif editor.settings is not None:
                # 关卡设置：Tab 切常规/玩家/声音/过场，↑↓ 选字段，←→ 调值，敲字改路径，
                # 过场页的图片卡片用滚轮上下滚
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if editor.sound_menu is not None:
                            editor.close_sound_menu()
                        else:
                            editor.close_settings(False)
                    elif event.key == pygame.K_RETURN:
                        if editor.sound_menu is not None:
                            editor.close_sound_menu()
                        else:
                            editor.close_settings(True)
                    elif event.key == pygame.K_TAB:
                        step = -1 if event.mod & pygame.KMOD_SHIFT else 1
                        editor.switch_settings_tab(step)
                    elif event.key == pygame.K_UP:
                        editor.move_settings_field(-1)
                    elif event.key == pygame.K_DOWN:
                        editor.move_settings_field(1)
                    elif event.key == pygame.K_LEFT:
                        editor.adjust_settings(-1)
                    elif event.key == pygame.K_RIGHT:
                        editor.adjust_settings(1)
                    elif event.key == pygame.K_BACKSPACE:
                        editor.erase_settings_char()
                    else:
                        editor.type_settings(event.unicode)
                elif event.type == pygame.MOUSEWHEEL:
                    if editor.sound_menu is not None:
                        editor.scroll_sound_menu(-event.y)
                    else:
                        editor.scroll_cutscene(-event.y)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    handle_settings_click(screen, editor, event.pos)
            elif editor.game_settings is not None:
                # 游戏配置：Tab 切页；动画集里点「新建动画」或点一行开编辑弹窗；
                # 弹窗里 Esc 取消、回车确定、点秒数改停留时长、滚轮翻格子。
                if event.type == pygame.KEYDOWN and editor.animation_edit is not None:
                    if event.key == pygame.K_ESCAPE:
                        if editor.animation_delay_active():
                            editor.cancel_animation_delay()
                        else:
                            editor.close_animation_edit(False)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if editor.animation_delay_active():
                            editor.commit_animation_delay()
                        elif editor.animation_edit["name_focus"]:
                            editor.blur_animation_name()
                        else:
                            editor.close_animation_edit(True)
                    elif event.key == pygame.K_BACKSPACE:
                        if editor.animation_delay_active():
                            editor.erase_animation_delay_char()
                        elif editor.animation_edit["name_focus"]:
                            editor.erase_animation_name_char()
                    elif event.key == pygame.K_DELETE:
                        editor.remove_animation_frame()
                    elif event.key == pygame.K_LEFT:
                        editor.adjust_animation_hold(-1)
                    elif event.key == pygame.K_RIGHT:
                        editor.adjust_animation_hold(1)
                    elif event.key == pygame.K_UP:
                        editor.move_animation_frame(-1)
                    elif event.key == pygame.K_DOWN:
                        editor.move_animation_frame(1)
                    elif event.unicode and event.unicode.isprintable():
                        if editor.animation_delay_active():
                            editor.type_animation_delay(event.unicode)
                        elif editor.animation_edit["name_focus"]:
                            editor.type_animation_name(event.unicode)
                    continue
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if editor.sound_menu is not None:
                            editor.close_sound_menu()
                        else:
                            editor.close_game_settings(False)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if editor.sound_menu is not None:
                            editor.close_sound_menu()
                        else:
                            editor.close_game_settings(True)
                    elif event.key == pygame.K_TAB:
                        step = -1 if event.mod & pygame.KMOD_SHIFT else 1
                        editor.switch_game_tab(step)
                    elif event.key == pygame.K_UP:
                        editor.move_game_field(-1)
                    elif event.key == pygame.K_DOWN:
                        editor.move_game_field(1)
                    elif event.key == pygame.K_LEFT:
                        editor.adjust_game_number(-1)
                    elif event.key == pygame.K_RIGHT:
                        editor.adjust_game_number(1)
                    elif event.key == pygame.K_BACKSPACE:
                        editor.erase_game_settings_char()
                    elif event.unicode and event.unicode.isprintable():
                        editor.type_game_settings(event.unicode)
                elif event.type == pygame.MOUSEWHEEL:
                    if editor.sound_menu is not None:
                        editor.scroll_sound_menu(-event.y)
                    elif editor.game_sound_library_tab():
                        editor.scroll_sound_library(-event.y)
                    else:
                        editor.scroll_game_cards(-event.y)
                elif (
                    event.type == pygame.MOUSEMOTION
                    and editor.animation_edit is not None
                    and editor.animation_edit["drag"] is not None
                ):
                    # 拖动帧：按着左键就更新插入点，松手在外不算
                    if event.buttons[0]:
                        handle_animation_edit_drag_motion(screen, editor, event.pos)
                    else:
                        editor.cancel_animation_frame_drag()
                elif (
                    event.type == pygame.MOUSEBUTTONUP
                    and event.button == 1
                    and editor.animation_edit is not None
                    and editor.animation_edit["drag"] is not None
                ):
                    handle_animation_edit_drag_release(editor)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    handle_game_settings_click(screen, editor, event.pos)
            elif editor.pending_switch is not None:
                # 有没保存的修改时走开：Y 保存并切换，N 不保存切换，Esc 取消
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_y):
                        editor.resolve_pending_switch(True)
                    elif event.key == pygame.K_n:
                        editor.resolve_pending_switch(False)
                    elif event.key == pygame.K_ESCAPE:
                        editor.resolve_pending_switch(None)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    handle_switch_click(screen, editor, event.pos)
            elif editor.file_menu_open:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    editor.file_menu_open = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1 and handle_file_menu_click(
                        editor, event.pos, screen.get_width()
                    ):
                        continue
                    editor.file_menu_open = False
            elif editor.view_menu_open:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    editor.view_menu_open = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1 and handle_view_menu_click(
                        editor, event.pos, screen.get_width()
                    ):
                        continue
                    editor.view_menu_open = False
            elif event.type in (pygame.KEYDOWN, pygame.KEYUP) and event.key in MODIFIER_KEYS:
                # 修饰键按下/松开也算一次变化：用最近的鼠标位置把拖动重算一遍
                sync_modifiers(editor)
                editor.refresh_grab(layout)
            elif editor.menu_open:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    editor.menu_open = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
                    if event.button == 1 and handle_create_menu(
                        editor, event.pos, screen.get_size(), layout
                    ):
                        continue
                    editor.menu_open = False
                    if event.button == 1:
                        handle_toolbar(editor, event.pos, screen.get_width())
            elif event.type == pygame.MOUSEMOTION:
                sync_modifiers(editor)
                if not editor.level_in_view:
                    continue
                if dock_visible(editor) and detail_panel_rect(screen).collidepoint(
                    event.pos
                ):
                    editor.hovered = None       # 光标在右侧面板上：画布不跟着悬停
                    continue
                if editor.object_grab is not None:
                    editor.update_object_grab(event.pos, layout)
                    continue
                if editor.marquee_start is not None:
                    editor.update_marquee(event.pos, layout)
                    continue
                editor.update_hover(event.pos, layout)
                if editor.pan_drag is not None:
                    start_x, start_y, start_pan_x, start_pan_y = editor.pan_drag
                    editor.pan_x = start_pan_x - (event.pos[0] - start_x)
                    editor.pan_y = start_pan_y - (event.pos[1] - start_y)
                elif editor.drag_start is not None:
                    editor.drag_to(event.pos, layout)
            elif event.type == pygame.MOUSEWHEEL:
                if not editor.level_in_view:
                    continue
                if dock_visible(editor) and detail_panel_rect(screen).collidepoint(
                    pygame.mouse.get_pos()
                ):
                    if editor.panel_tab == "objects":
                        editor.scroll_go_list(-event.y)     # 对象列表页：滚列表
                    elif editor.dialog is not None:
                        editor.scroll_detail(-event.y)      # 属性页：滚面板
                    continue
                if event.y:
                    factor = ZOOM_STEP if event.y > 0 else 1.0 / ZOOM_STEP
                    new_tile = min(max(layout.tile * factor, layout.min_tile), layout.max_tile)
                    anchor_x, anchor_y = pygame.mouse.get_pos()
                    canvas_x = (anchor_x - layout.left) / layout.tile
                    canvas_y = (anchor_y - layout.top) / layout.tile
                    editor.zoom = new_tile
                    editor.pan_x = MARGIN - anchor_x + canvas_x * new_tile
                    editor.pan_y = HEADER - anchor_y + canvas_y * new_tile
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button in (4, 5):
                    continue
                # 筛选菜单开着时点别处：先把它收起来，再照常处理这次点击
                if (
                    dock_visible(editor)
                    and editor.go_list_menu
                    and not detail_panel_rect(screen).collidepoint(event.pos)
                ):
                    editor.close_go_list_menu()
                if editor.dropdown_field is not None and event.button == 1:
                    if handle_dropdown_click(screen, editor, event.pos):
                        continue
                    # 列表已经收起：点在面板里就继续走面板，点在画布上就只是收起列表
                    if not (
                        dock_visible(editor)
                        and detail_panel_rect(screen).collidepoint(event.pos)
                    ):
                        continue
                if editor.pick_menu is not None:
                    if event.button == 1 and handle_pick_menu_click(screen, editor, event.pos):
                        continue
                    editor.close_pick_menu()
                if dock_visible(editor) and detail_panel_rect(screen).collidepoint(event.pos):
                    if event.button == 1:
                        handle_dock_click(screen, editor, event.pos)
                    continue
                if event.button == 1 and handle_toolbar(
                    editor, event.pos, screen.get_width()
                ):
                    continue
                if not editor.level_in_view:
                    continue                    # 视图里没有关卡：画布什么都不接
                if event.button == 2:
                    editor.pan_drag = (event.pos[0], event.pos[1], editor.pan_x, editor.pan_y)
                    continue
                sync_modifiers(editor)
                if event.button == 3:
                    if editor.creating:
                        if editor.drag_start is None:
                            editor.stop_creating()
                    elif event.pos[1] >= HEADER:
                        editor.open_create_menu(event.pos)
                elif event.button == 1 and editor.creating:
                    editor.press_canvas(event.pos, layout)
                elif event.button == 1:
                    editor.update_hover(event.pos, layout)
                    # Alt+点击：叠着多个对象时先列出它们，让用户挑一个
                    if editor.click_through and editor.open_pick_menu(event.pos, layout):
                        continue
                    # 对象上按下就是拖（移动/缩放）；空地上按下就拉框选
                    if not editor.begin_object_grab(event.pos, layout):
                        editor.begin_marquee(event.pos, layout)
            elif event.type == pygame.MOUSEBUTTONUP:
                if not editor.level_in_view:
                    continue
                if event.button == 2:
                    editor.pan_drag = None
                elif event.button == 1 and editor.object_grab is not None:
                    editor.end_object_grab()
                elif event.button == 1 and editor.marquee_start is not None:
                    editor.finish_marquee(layout)
                elif event.button == 1 and editor.drag_start is not None:
                    editor.finish_drag()
            elif event.type == pygame.KEYDOWN:
                ctrl = bool(event.mod & pygame.KMOD_CTRL)
                if editor.pick_menu is not None and event.key == pygame.K_ESCAPE:
                    editor.close_pick_menu()
                elif ctrl and event.key == pygame.K_z:
                    if editor.level_in_view:
                        editor.undo()
                elif ctrl and event.key == pygame.K_s:
                    if editor.level_in_view:
                        editor.save()
                elif ctrl and event.key == pygame.K_o:
                    editor.request_open_game()
                elif ctrl and event.key == pygame.K_n:
                    editor.create_level()
                elif ctrl and event.key == pygame.K_d:
                    if editor.level_in_view:
                        editor.duplicate_selection()
                elif event.key == pygame.K_ESCAPE:
                    if editor.dropdown_field is not None:
                        editor.close_dropdown()
                    elif editor.go_list_menu:
                        editor.close_go_list_menu()
                    elif editor.name_focused:
                        editor.blur_name()
                    elif editor.selection:
                        editor.clear_selection()
                    elif editor.request_quit():
                        running = False
                elif editor.name_focused:
                    # 名称输入中：只吃 Enter / 退格 / 可打印字符，其余键都不触发其它操作
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        editor.blur_name()
                    elif event.key == pygame.K_BACKSPACE:
                        editor.erase_name_char()
                    elif event.unicode and event.unicode.isprintable():
                        editor.type_name(event.unicode)
                elif event.key == pygame.K_r and editor.level_in_view:
                    # R：选中的贴图朝向顺时针转一格
                    editor.rotate_selection_cw()
                elif event.key == pygame.K_DELETE and editor.level_in_view:
                    if editor.selection:
                        editor.delete_selection()
                    elif editor.hovered is not None:
                        kind, entry = editor.hovered
                        editor.delete_entry(kind, entry)
                elif editor.dialog is not None and event.unicode and (
                    event.unicode.isdigit() or event.unicode in "-."
                ):
                    # 数字字段：直接敲数字输入（可以带小数点和负号），点加减或按方向键仍是半格一步
                    editor.type_dialog_number(event.unicode)
                elif editor.dialog is not None and event.key == pygame.K_BACKSPACE:
                    editor.erase_dialog_number()
                elif editor.dialog is not None and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    editor.blur_number()
                elif editor.dialog is not None and event.key == pygame.K_UP:
                    editor.move_dialog_field(-1)
                    editor.keep_detail_focus_visible(screen)
                elif editor.dialog is not None and event.key == pygame.K_DOWN:
                    editor.move_dialog_field(1)
                    editor.keep_detail_focus_visible(screen)
                elif editor.dialog is not None and event.key == pygame.K_LEFT:
                    editor.adjust_dialog(-1)
                elif editor.dialog is not None and event.key == pygame.K_RIGHT:
                    editor.adjust_dialog(1)

        # 动画集里的预览和画布上的动画对象各走各的
        editor.advance_animation_edit(dt)
        editor.advance_animation_objects(dt)

        draw(screen, editor, font, layout)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    run()
