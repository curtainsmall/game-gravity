"""右侧面板的「对象列表」页：这一关有哪些对象一目了然，还能按种类筛。

列表最上面固定是「全局」组（玩家动画 / 玩家音效，来自 game.json，不能删），
往下才是这一关的对象。列表和画布用同一份对象清单（Editor.go_list_objects），
所以看得见、点得中的东西才会列出来；点一行就在画布上选中它。筛选用列表顶上那个
「类型」下拉，菜单里只列这一关里真有的种类和个数。列表和筛选都只属于编辑器当前
这一关，不写进关卡文件。
"""

from typing import TYPE_CHECKING

import pygame

from core.constants import (
    DIALOG_BG,
    DIALOG_BORDER,
    DIM_TEXT,
    DOCK_TAB_HEIGHT,
    HIGHLIGHT,
    KIND_GLOBAL_HEADER,
    KIND_TITLES,
    ROW_HEIGHT,
    TEXT,
)
from view.panel import detail_panel_rect
from view.widgets import draw_scrollbar

if TYPE_CHECKING:
    from editing.editor import Editor

GO_LIST_PAD = 8                 # 面板内容和边框之间的空
GO_LIST_TITLE_HEIGHT = 20
GO_LIST_GAP = 6                 # 标题、筛选、列表之间
GO_LIST_FILTER_HEIGHT = ROW_HEIGHT


def go_list_geometry(surface: pygame.Surface, editor: "Editor") -> dict:
    """对象列表页里的标题、筛选按钮、列表行和展开的筛选菜单。"""
    panel = detail_panel_rect(surface)
    left = panel.left + GO_LIST_PAD
    width = panel.width - 2 * GO_LIST_PAD
    title = pygame.Rect(
        left, panel.top + DOCK_TAB_HEIGHT + 8, width, GO_LIST_TITLE_HEIGHT
    )
    filter_rect = pygame.Rect(left, title.bottom + GO_LIST_GAP, width, GO_LIST_FILTER_HEIGHT)
    list_top = filter_rect.bottom + GO_LIST_GAP
    area = pygame.Rect(
        left, list_top, width, max(ROW_HEIGHT, panel.bottom - GO_LIST_GAP - list_top)
    )
    items = editor.go_list_items()
    content = len(items) * ROW_HEIGHT
    scroll = max(
        0.0, min(float(editor.go_list_scroll), max(0.0, content - area.height))
    )
    editor.go_list_scroll = scroll
    rows = []
    for index, (kind, entry) in enumerate(items):
        y = area.top + index * ROW_HEIGHT - round(scroll)
        if y + ROW_HEIGHT <= area.top or y >= area.bottom:
            continue
        rect = pygame.Rect(area.left, y, area.width, ROW_HEIGHT - 1).clip(area)
        if rect.height > 0:
            rows.append({"rect": rect, "kind": kind, "entry": entry})
    popup, popup_rows = _filter_popup(panel, filter_rect, editor)
    return {
        "panel": panel,
        "title": title,
        "filter": filter_rect,
        "area": area,
        "rows": rows,
        "items": items,
        "content": content,
        "scroll": scroll,
        "popup": popup,
        "popup_rows": popup_rows,
    }


def _filter_popup(panel: pygame.Rect, anchor: pygame.Rect, editor: "Editor") -> tuple:
    """筛选下拉：贴在筛选按钮下面，放不下就往上收；没展开就是 (None, [])。"""
    if not editor.go_list_menu:
        return None, []
    options = [("全部", "")] + [
        (f"{KIND_TITLES.get(kind, '对象')}（{count}）", kind)
        for kind, count in editor.go_list_counts()
    ]
    height = len(options) * ROW_HEIGHT + 2
    top = anchor.bottom + 2
    if top + height > panel.bottom - GO_LIST_GAP:
        top = max(panel.top + DOCK_TAB_HEIGHT + GO_LIST_GAP, anchor.top - 2 - height)
    popup = pygame.Rect(anchor.left, top, anchor.width, height)
    rows = [
        (
            pygame.Rect(
                popup.left,
                popup.top + 1 + index * ROW_HEIGHT,
                popup.width - 2,
                ROW_HEIGHT,
            ),
            label,
            value,
        )
        for index, (label, value) in enumerate(options)
    ]
    return popup, rows


def draw_go_list(
    surface: pygame.Surface, editor: "Editor", font: pygame.font.Font
) -> None:
    geometry = go_list_geometry(surface, editor)

    title = font.render("对象列表", True, TEXT)
    surface.blit(title, (geometry["title"].left, geometry["title"].top))
    count = font.render(f"本关 {len(editor.go_list_objects())} 个 · 全局 2 项", True, DIM_TEXT)
    surface.blit(
        count,
        (geometry["title"].right - count.get_width(), geometry["title"].top),
    )

    _draw_filter(surface, font, editor, geometry["filter"])
    _draw_rows(surface, font, editor, geometry)
    draw_scrollbar(surface, geometry["area"], geometry["content"], geometry["scroll"])

    popup = geometry["popup"]
    if popup is None:
        return
    pygame.draw.rect(surface, DIALOG_BG, popup)
    pygame.draw.rect(surface, DIALOG_BORDER, popup, 1)
    mouse = pygame.mouse.get_pos()
    for rect, label, value in geometry["popup_rows"]:
        if rect.collidepoint(mouse):
            pygame.draw.rect(surface, (100, 100, 110), rect)
        mark = "●" if value == editor.go_list_filter else " "
        text = font.render(f"{mark} {label}", True, TEXT)
        surface.blit(
            text,
            (rect.left + 6, rect.centery - text.get_height() // 2),
            (0, 0, max(1, rect.width - 10), text.get_height()),
        )


def _draw_filter(
    surface: pygame.Surface,
    font: pygame.font.Font,
    editor: "Editor",
    rect: pygame.Rect,
) -> None:
    """筛选按钮：左边写当前筛的种类，右边一个小三角。"""
    open_ = editor.go_list_menu
    pygame.draw.rect(surface, (62, 62, 72) if open_ else (48, 48, 54), rect)
    pygame.draw.rect(surface, HIGHLIGHT if open_ else (86, 86, 94), rect, 1)
    text = font.render(f"类型：{editor.go_list_filter_label()}", True, TEXT)
    surface.blit(
        text,
        (rect.left + 6, rect.centery - text.get_height() // 2),
        (0, 0, max(1, rect.width - 22), text.get_height()),
    )
    center_x = rect.right - 10
    pygame.draw.polygon(
        surface,
        TEXT,
        [
            (center_x - 4, rect.centery - 2),
            (center_x + 4, rect.centery - 2),
            (center_x, rect.centery + 4),
        ],
    )


def _draw_rows(
    surface: pygame.Surface, font: pygame.font.Font, editor: "Editor", geometry: dict
) -> None:
    """列表本身：一行一个对象，选中的那行高亮；内容多了裁掉并画滚动条。"""
    area = geometry["area"]
    pygame.draw.rect(surface, (44, 44, 50), area)
    pygame.draw.rect(surface, (70, 70, 78), area, 1)
    if not geometry["items"]:
        text = "没有这种类型的对象。" if editor.go_list_filter else "这一关还没有对象。"
        message = font.render(text, True, DIM_TEXT)
        surface.blit(
            message,
            (
                area.centerx - message.get_width() // 2,
                area.top + 10,
            ),
        )
        return
    previous = surface.get_clip()
    surface.set_clip(previous.clip(area))
    selected_entries = [entry for _, entry in editor.selection]
    for row in geometry["rows"]:
        header = row["kind"] == KIND_GLOBAL_HEADER
        selected = (
            not header
            and any(row["entry"] is entry for entry in selected_entries)
        )
        pygame.draw.rect(
            surface, (62, 62, 72) if selected else (48, 48, 54), row["rect"]
        )
        pygame.draw.rect(
            surface, HIGHLIGHT if selected else (86, 86, 94), row["rect"], 1
        )
        label = font.render(
            editor.go_list_label(row["kind"], row["entry"]),
            True,
            DIM_TEXT if header else (HIGHLIGHT if selected else TEXT),
        )
        surface.blit(
            label,
            (
                row["rect"].left + 6,
                row["rect"].centery - label.get_height() // 2,
            ),
            (0, 0, max(1, row["rect"].width - 12), label.get_height()),
        )
    surface.set_clip(previous)
