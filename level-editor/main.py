"""关卡编辑器的启动入口与主循环。

运行：uv run python level-editor/main.py
"""

import pygame

from core.constants import (
    DEFAULT_WINDOW,
    HEADER,
    MARGIN,
    MIN_WINDOW,
    PLAYER_SETTINGS_FIELD_COUNT,
    SETTINGS_FIELD_COUNT,
    ZOOM_STEP,
)
from editing.editor import Editor
from editing.handlers import (
    handle_create_menu,
    handle_detail_click,
    handle_dropdown_click,
    handle_player_settings_click,
    handle_settings_click,
    handle_toolbar,
)
from view.chrome import handle_view_menu_click
from view.frame import draw
from view.layout import Layout
from view.modals import quit_geometry, startup_rects
from view.panel import detail_panel_rect, detail_panel_width

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
    panel_open = lambda: editor.dialog is not None or len(editor.selection) > 1
    while running:
        reserved_right = 0 if not panel_open() else detail_panel_width(screen) + MARGIN
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
                reserved_right = 0 if not panel_open() else detail_panel_width(screen) + MARGIN
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
            elif editor.startup:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if editor.request_quit():
                            running = False
                    elif event.key in (pygame.K_RETURN, pygame.K_n):
                        editor.new_level()
                    elif event.key == pygame.K_o:
                        editor.open_level()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for rect, action in startup_rects(screen):
                        if rect.collidepoint(event.pos):
                            editor.new_level() if action == "new" else editor.open_level()
                            break
            elif editor.settings is not None:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        editor.close_settings(False)
                    elif event.key == pygame.K_RETURN:
                        editor.close_settings(True)
                    elif event.key == pygame.K_UP:
                        editor.settings_field = (editor.settings_field - 1) % SETTINGS_FIELD_COUNT
                    elif event.key == pygame.K_DOWN:
                        editor.settings_field = (editor.settings_field + 1) % SETTINGS_FIELD_COUNT
                    elif event.key == pygame.K_LEFT:
                        editor.adjust_settings(-1)
                    elif event.key == pygame.K_RIGHT:
                        editor.adjust_settings(1)
                    elif event.key == pygame.K_BACKSPACE:
                        editor.erase_settings_char()
                    else:
                        editor.type_settings(event.unicode)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    handle_settings_click(screen, editor, event.pos)
            elif editor.player_settings is not None:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        editor.close_player_settings(False)
                    elif event.key == pygame.K_RETURN:
                        editor.close_player_settings(True)
                    elif event.key == pygame.K_UP:
                        editor.player_settings_field = (
                            editor.player_settings_field - 1
                        ) % PLAYER_SETTINGS_FIELD_COUNT
                    elif event.key == pygame.K_DOWN:
                        editor.player_settings_field = (
                            editor.player_settings_field + 1
                        ) % PLAYER_SETTINGS_FIELD_COUNT
                    elif event.key == pygame.K_LEFT:
                        editor.adjust_player_settings(-1)
                    elif event.key == pygame.K_RIGHT:
                        editor.adjust_player_settings(1)
                    elif event.key == pygame.K_BACKSPACE:
                        editor.erase_player_settings_char()
                    else:
                        editor.type_player_settings(event.unicode)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    handle_player_settings_click(screen, editor, event.pos)
            elif editor.view_menu_open:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    editor.view_menu_open = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1 and handle_view_menu_click(editor, event.pos):
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
                        handle_toolbar(editor, event.pos)
            elif event.type == pygame.MOUSEMOTION:
                sync_modifiers(editor)
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
                if editor.dropdown_field is not None and event.button == 1:
                    if handle_dropdown_click(screen, editor, event.pos):
                        continue
                    # 列表已经收起：点在面板里就继续走面板，点在画布上就只是收起列表
                    if not (panel_open() and detail_panel_rect(screen).collidepoint(event.pos)):
                        continue
                if panel_open() and detail_panel_rect(screen).collidepoint(event.pos):
                    if event.button == 1:
                        handle_detail_click(screen, editor, event.pos)
                    continue
                if event.button == 1 and handle_toolbar(editor, event.pos):
                    continue
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
                    # 对象上按下就是拖（移动/缩放）；空地上按下就拉框选
                    if not editor.begin_object_grab(event.pos, layout):
                        editor.begin_marquee(event.pos, layout)
            elif event.type == pygame.MOUSEBUTTONUP:
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
                if ctrl and event.key == pygame.K_z:
                    editor.undo()
                elif ctrl and event.key == pygame.K_s:
                    editor.save()
                elif ctrl and event.key == pygame.K_o:
                    editor.open_level()
                elif ctrl and event.key == pygame.K_n:
                    editor.new_level()
                elif event.key == pygame.K_ESCAPE:
                    if editor.dropdown_field is not None:
                        editor.close_dropdown()
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
                elif event.key == pygame.K_DELETE:
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
                elif editor.dialog is not None and event.key == pygame.K_DOWN:
                    editor.move_dialog_field(1)
                elif editor.dialog is not None and event.key == pygame.K_LEFT:
                    editor.adjust_dialog(-1)
                elif editor.dialog is not None and event.key == pygame.K_RIGHT:
                    editor.adjust_dialog(1)

        draw(screen, editor, font, layout)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    run()
