"""顶部信息栏、工具栏、文件/视图菜单和右键新建菜单。"""

import pygame
from typing import TYPE_CHECKING

from core.constants import (
    BUTTON_BG,
    CREATE_MENU_WIDTH,
    DIALOG_BORDER,
    DIM_TEXT,
    FILE_MENU_ITEMS,
    FILE_MENU_WIDTH,
    FOOTER,
    HEADER,
    HEADER_BG,
    HEADER_LINE,
    HIGHLIGHT,
    MARGIN,
    ROW_HEIGHT,
    TEXT,
    TOOLBAR_HEIGHT,
    TOOLBAR_ITEMS,
    TOOL_ORDER,
    TOOL_SPECS,
    VIEW_MENU_WIDTH,
)
from core.helpers import display_path
from view.layout import Layout
from view.widgets import draw_checkbox

if TYPE_CHECKING:
    from editing.editor import Editor

TOOLBAR_GAP = 8


def _toolbar_visible(when: str, editor: Editor) -> bool:
    if when == "game" and editor.game_path is None:
        return False
    if when == "level" and not editor.level_in_view:
        return False
    return True


def toolbar_rects(editor: Editor, window_width: int) -> list:
    """工具栏按钮：左边从 MARGIN 往后排，右边贴着窗口右边排（靠后的更靠右）。"""
    items = [item for item in TOOLBAR_ITEMS if _toolbar_visible(item[3], editor)]
    left_items = [item for item in items if item[4] == "left"]
    right_items = [item for item in items if item[4] == "right"]

    rects = []
    x = MARGIN
    for label, action, width, _, _ in left_items:
        rects.append((pygame.Rect(x, HEADER - 34, width, TOOLBAR_HEIGHT), label, action))
        x += width + TOOLBAR_GAP
    total = sum(width + TOOLBAR_GAP for _, _, width, _, _ in right_items)
    x = window_width - MARGIN - total + TOOLBAR_GAP
    for label, action, width, _, _ in right_items:
        rects.append((pygame.Rect(x, HEADER - 34, width, TOOLBAR_HEIGHT), label, action))
        x += width + TOOLBAR_GAP
    return rects


def _menu_items(when_ok: bool, items: list) -> list:
    return [(label, action) for label, action, when in items if when == "always" or when_ok]


def file_menu_rects(editor: Editor, window_width: int) -> list:
    """工具栏「文件」按钮下面的菜单：每行是 (矩形, 动作, 标题)。"""
    anchor = next(rect for rect, _, action in toolbar_rects(editor, window_width) if action == "files")
    items = _menu_items(editor.game_path is not None, FILE_MENU_ITEMS)
    return [
        (
            pygame.Rect(anchor.left, anchor.bottom + 2 + index * ROW_HEIGHT, FILE_MENU_WIDTH, ROW_HEIGHT),
            action,
            label,
        )
        for index, (label, action) in enumerate(items)
    ]


def draw_file_menu(surface: pygame.Surface, editor: Editor, font: pygame.font.Font) -> None:
    rects = file_menu_rects(editor, surface.get_width())
    border = rects[0][0].unionall([rect for rect, _, _ in rects])
    pygame.draw.rect(surface, BUTTON_BG, border)
    pygame.draw.rect(surface, DIALOG_BORDER, border, 1)
    mouse = pygame.mouse.get_pos()
    for rect, _, label in rects:
        if rect.collidepoint(mouse):
            pygame.draw.rect(surface, (100, 100, 110), rect)
        text = font.render(label, True, TEXT)
        surface.blit(text, (rect.left + 6, rect.centery - text.get_height() // 2))


def handle_file_menu_click(editor: Editor, position: tuple, window_width: int) -> bool:
    """点菜单里的一行就执行那个动作；返回点是否落在菜单里。"""
    for rect, action, _ in file_menu_rects(editor, window_width):
        if not rect.collidepoint(position):
            continue
        editor.file_menu_open = False
        if action == "open_game":
            editor.request_open_game()
        elif action == "levels":
            editor.open_level_select()
        return True
    return False


def view_menu_rects(editor: Editor, window_width: int) -> list:
    """工具栏「视图」按钮下方的菜单：每行是 (矩形, 设置键, 标题)。

    这里的东西只影响编辑器自己的显示，不进关卡数据、不写盘。调试显示和游戏里那个
    开关是一回事：关掉就只看背景和贴图（发布后的样子），打开则连翻转带一起画出来；
    「显示贴图」关掉时贴图不画也点不中，方便看底下的方块和机关。
    """
    anchor = next(rect for rect, _, action in toolbar_rects(editor, window_width) if action == "view")
    items = [
        ("background", "显示背景"),
        ("textures", "显示贴图"),
        ("grid", "显示网格"),
        ("debug", "调试显示"),
    ]
    return [
        (
            pygame.Rect(
                anchor.left,
                anchor.bottom + 2 + index * ROW_HEIGHT,
                VIEW_MENU_WIDTH,
                ROW_HEIGHT,
            ),
            key,
            label,
        )
        for index, (key, label) in enumerate(items)
    ]


def draw_view_menu(surface: pygame.Surface, editor: Editor, font: pygame.font.Font) -> None:
    rects = view_menu_rects(editor, surface.get_width())
    border = rects[0][0].unionall([rect for rect, _, _ in rects])
    pygame.draw.rect(surface, BUTTON_BG, border)
    pygame.draw.rect(surface, DIALOG_BORDER, border, 1)
    mouse = pygame.mouse.get_pos()
    for rect, key, label in rects:
        if rect.collidepoint(mouse):
            pygame.draw.rect(surface, (100, 100, 110), rect)
        draw_checkbox(
            surface, font, rect, label, bool(editor.view_settings.get(key, True)), inset=6
        )


def handle_view_menu_click(editor: Editor, position: tuple, window_width: int) -> bool:
    """点菜单里的一行就切换那个视图开关；返回点是否落在菜单里。"""
    for rect, key, _ in view_menu_rects(editor, window_width):
        if rect.collidepoint(position):
            editor.view_settings[key] = not editor.view_settings.get(key, True)
            return True
    return False


def create_menu_rects(origin: tuple, window_size: tuple) -> list:
    """右键弹出的新建菜单：以光标为左上角，越界时往里收。"""
    height = len(TOOL_ORDER) * ROW_HEIGHT
    left = max(MARGIN, min(origin[0], window_size[0] - MARGIN - CREATE_MENU_WIDTH))
    top = max(HEADER, min(origin[1], window_size[1] - FOOTER - height))
    return [
        (pygame.Rect(left, top + index * ROW_HEIGHT, CREATE_MENU_WIDTH, ROW_HEIGHT), tool)
        for index, tool in enumerate(TOOL_ORDER)
    ]


def draw_header(surface: pygame.Surface, editor: Editor, layout: Layout, font: pygame.font.Font) -> None:
    # 半透明底板：信息行和工具栏压在画布上也看得清，又不会把画布完全挡住
    bar = pygame.Surface((surface.get_width(), HEADER), pygame.SRCALPHA)
    bar.fill(HEADER_BG)
    surface.blit(bar, (0, 0))
    pygame.draw.line(surface, HEADER_LINE, (0, HEADER - 1), (surface.get_width(), HEADER - 1))

    marker = " *" if editor.dirty else ""
    zoom_text = "游戏比例" if layout.zoom is None else f"{layout.tile:.1f}px/格"
    game_text = display_path(editor.game_path) if editor.game_path else "（尚未打开游戏配置）"
    if not editor.level_in_view:
        level_text = "（视图内没有关卡）"
    else:
        level_text = display_path(editor.path) if editor.path else "新关卡（未保存）"
    head = f"游戏 {game_text}   关卡 {level_text}{marker}   缩放：{zoom_text}"
    if editor.level_in_view:
        jump, speed, overridden = editor.player_stats()
        suffix = "（关卡覆盖）" if overridden else ""
        head += (
            f"   尺寸 {editor.level.width}×{editor.level.height}"
            f"   跳高：{jump:g}{suffix}   速度：{speed:g}{suffix}"
            f"   撤销 {len(editor.undo_stack)} 步"
        )
    surface.blit(font.render(head, True, TEXT), (MARGIN, 8))

    if editor.creating:
        mode = font.render(
            f"新建模式：{TOOL_SPECS[editor.tool][0]}；左键绘制，右键退出。", True, HIGHLIGHT
        )
        surface.blit(mode, (surface.get_width() - MARGIN - mode.get_width(), 8))
        hint = "左键拖出矩形或单击放置；右键退出新建；滚轮缩放；中键平移。"
    elif editor.game_path is None:
        hint = "请打开或新建游戏配置文件（game.json）。"
    elif not editor.level_in_view:
        hint = "请从「文件」菜单里选择关卡，或新建关卡。"
    else:
        hint = (
            "右键新建对象；左键设置；Delete 删除；R 旋转贴图；Ctrl+D 复制贴图；"
            "滚轮缩放；中键平移；Shift 吸附；Ctrl 加选或等比缩放；Alt 穿透。"
        )
    surface.blit(font.render(hint, True, DIM_TEXT), (MARGIN, 30))

    for rect, label, action in toolbar_rects(editor, surface.get_width()):
        pygame.draw.rect(surface, BUTTON_BG, rect)
        pygame.draw.rect(surface, DIALOG_BORDER, rect, 1)
        text = font.render(label, True, TEXT)
        surface.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))


def draw_create_menu(surface: pygame.Surface, editor: Editor, font: pygame.font.Font) -> None:
    mouse = pygame.mouse.get_pos()
    rects = create_menu_rects(editor.menu_origin, surface.get_size())
    for rect, tool in rects:
        pygame.draw.rect(surface, (100, 100, 110) if rect.collidepoint(mouse) else BUTTON_BG, rect)
        surface.blit(font.render(TOOL_SPECS[tool][0], True, TEXT), (rect.left + 10, rect.top + 2))
    border = rects[0][0].unionall([rect for rect, _ in rects])
    pygame.draw.rect(surface, DIALOG_BORDER, border, 1)
