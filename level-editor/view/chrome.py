"""顶部信息栏、工具栏和右键新建菜单。"""

import pygame
from typing import TYPE_CHECKING

from core.constants import (
    BUTTON_BG,
    CREATE_MENU_WIDTH,
    DIALOG_BORDER,
    DIM_TEXT,
    FOOTER,
    HEADER,
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

if TYPE_CHECKING:
    from editing.editor import Editor


def toolbar_rects() -> list:
    rects = []
    x = MARGIN
    for label, action, width in TOOLBAR_ITEMS:
        rects.append((pygame.Rect(x, HEADER - 34, width, TOOLBAR_HEIGHT), label, action))
        x += width + 8
    return rects


def view_menu_rects() -> list:
    """工具栏「视图」按钮下方的菜单：每行是 (矩形, 设置键, 标题)。

    这里的东西只影响编辑器自己的显示，不进关卡数据、不写盘。
    """
    anchor = next(rect for rect, _, action in toolbar_rects() if action == "view")
    items = [("background", "显示背景")]
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
    rects = view_menu_rects()
    border = rects[0][0].unionall([rect for rect, _, _ in rects])
    pygame.draw.rect(surface, BUTTON_BG, border)
    pygame.draw.rect(surface, DIALOG_BORDER, border, 1)
    mouse = pygame.mouse.get_pos()
    for rect, key, label in rects:
        if rect.collidepoint(mouse):
            pygame.draw.rect(surface, (100, 100, 110), rect)
        mark = "[x]" if editor.view_settings.get(key, True) else "[ ]"
        text = font.render(f"{mark} {label}", True, TEXT)
        surface.blit(text, (rect.left + 6, rect.centery - text.get_height() // 2))


def handle_view_menu_click(editor: Editor, position: tuple) -> bool:
    """点菜单里的一行就切换那个视图开关；返回点是否落在菜单里。"""
    for rect, key, _ in view_menu_rects():
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
    marker = " *" if editor.dirty else ""
    zoom_text = "游戏比例" if layout.zoom is None else f"{layout.tile:.1f}px/格"
    head = (
        f"{display_path(editor.path)}{marker}   缩放: {zoom_text}   "
        f"尺寸 {editor.level.width}×{editor.level.height}   "
        f"跳高: {editor.level.jump_height}   速度: {editor.level.move_speed:g}   "
        f"撤销 {len(editor.undo_stack)} 步"
    )
    surface.blit(font.render(head, True, TEXT), (MARGIN, 8))

    if editor.creating:
        mode = font.render(
            f"新建中：{TOOL_SPECS[editor.tool][0]}   左键画，右键退出", True, HIGHLIGHT
        )
        surface.blit(mode, (surface.get_width() - MARGIN - mode.get_width(), 8))
        hint = "左键拖出矩形 / 单击放置   右键 退出新建   滚轮缩放   中键平移"
    else:
        hint = (
            "右键 新建对象   左键 设置   数字直接敲   Delete 删除   滚轮缩放   中键平移   "
            "Shift 吸附   Ctrl 加选/等比   Alt 穿透"
        )
    surface.blit(font.render(hint, True, DIM_TEXT), (MARGIN, 30))

    for rect, label, action in toolbar_rects():
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
