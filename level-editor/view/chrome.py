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
        f"跳高: {editor.level.jump_height}   撤销 {len(editor.undo_stack)} 步"
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
            "Ctrl-Z/S/O/N 撤销/保存/打开/新建"
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
