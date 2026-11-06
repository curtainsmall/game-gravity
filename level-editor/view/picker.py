"""Alt+点击弹出的「光标下的对象」列表：叠在一起的几层列出来，点一行就选中它。"""

from typing import TYPE_CHECKING

import pygame

from core.constants import (
    DIALOG_BG,
    DIALOG_BORDER,
    DIM_TEXT,
    FOOTER,
    HEADER,
    HIGHLIGHT,
    MARGIN,
    ROW_HEIGHT,
    TEXT,
)

if TYPE_CHECKING:
    from editing.editor import Editor

PICK_MENU_WIDTH = 280
PICK_MENU_GAP = 10      # 离光标的距离
PICK_TITLE_HEIGHT = 20


def pick_menu_layout(surface: pygame.Surface, editor: Editor) -> tuple:
    """菜单的位置：(标题矩形, [(行矩形, 下标)])；没打开就是 (None, [])。

    优先开在光标右下方，贴着窗口边就往里收；行序就是叠放顺序（最上面那行在最上层）。
    """
    menu = editor.pick_menu
    if menu is None:
        return None, []
    count = len(menu["stack"])
    height = PICK_TITLE_HEIGHT + count * ROW_HEIGHT
    x, y = menu["position"]
    left = max(
        MARGIN, min(x + PICK_MENU_GAP, surface.get_width() - MARGIN - PICK_MENU_WIDTH)
    )
    top = max(
        HEADER, min(y + PICK_MENU_GAP, surface.get_height() - FOOTER - height)
    )
    title = pygame.Rect(left, top, PICK_MENU_WIDTH, PICK_TITLE_HEIGHT)
    rows = [
        (
            pygame.Rect(
                left, title.bottom + index * ROW_HEIGHT, PICK_MENU_WIDTH, ROW_HEIGHT
            ),
            index,
        )
        for index in range(count)
    ]
    return title, rows


def pick_menu_rects(surface: pygame.Surface, editor: Editor) -> list:
    """每个对象的行：[(矩形, 下标)]。"""
    return pick_menu_layout(surface, editor)[1]


def pick_menu_hovered(surface: pygame.Surface, editor: Editor) -> int | None:
    """鼠标指着哪一行（画布上给那个对象描边用）。"""
    position = pygame.mouse.get_pos()
    for rect, index in pick_menu_rects(surface, editor):
        if rect.collidepoint(position):
            return index
    return None


def draw_pick_menu(surface: pygame.Surface, editor: Editor, font: pygame.font.Font) -> None:
    title, rows = pick_menu_layout(surface, editor)
    if title is None:
        return
    stack = editor.pick_menu["stack"]
    selected = editor.selection[0] if len(editor.selection) == 1 else None
    border = title.unionall([rect for rect, _ in rows])
    pygame.draw.rect(surface, DIALOG_BG, border)
    pygame.draw.rect(surface, DIALOG_BORDER, border, 1)
    surface.blit(
        font.render("光标下的对象：点一行选中", True, DIM_TEXT), (title.left + 6, title.top + 2)
    )

    mouse = pygame.mouse.get_pos()
    for rect, index in rows:
        kind, entry = stack[index]
        if rect.collidepoint(mouse):
            pygame.draw.rect(surface, (100, 100, 110), rect)
        mark = "•" if selected is not None and entry is selected[1] else " "
        text = font.render(f"{mark} {editor.label_of(kind, entry)}", True, TEXT)
        surface.blit(
            text,
            (rect.left + 6, rect.centery - text.get_height() // 2),
            (0, 0, min(text.get_width(), rect.width - 12), text.get_height()),
        )
