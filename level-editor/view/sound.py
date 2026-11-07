"""游戏配置的「声音库」页：列出所有声音，导入、试听、删除；以及选 BGM 的下拉。

声音库是 game.json 的 sound_library：键就是名字，条目只有一个路径（相对 game.json）。
音乐链接和声音对象都只存键，所以这一页是全游戏唯一管声音文件的地方；导入只记路径，
不复制文件。被关卡或音乐引用的声音不许删，免得链接悬空。

「选择…」不弹文件框：它在本页下面摊开声音库里的键，选完写回对应的那一格。
"""

from typing import TYPE_CHECKING

import pygame

from core.constants import (
    BUTTON_HEIGHT,
    DIALOG_BG,
    DIALOG_BORDER,
    DIM_TEXT,
    HIGHLIGHT,
    MARGIN,
    ROW_HEIGHT,
    TEXT,
)
from core.sound import key_label
from view.widgets import draw_button, draw_scrollbar

if TYPE_CHECKING:
    from editing.editor import Editor

SOUND_ROW_HEIGHT = 26
SOUND_ROW_GAP = 4
SOUND_SCROLLBAR = 10

SOUND_MENU_ROWS = 8            # 下拉一次最多露几行，多了用滚轮翻
SOUND_MENU_MIN_WIDTH = 220


def sound_library_height(top_offset: int) -> int:
    """声音库页固定这么高：五行加上面的按钮和最下面一行按钮。"""
    return top_offset + 32 + 5 * (SOUND_ROW_HEIGHT + SOUND_ROW_GAP) + 46


def sound_library_geometry(
    surface: pygame.Surface, editor: "Editor", panel: pygame.Rect, top: int
) -> dict:
    """声音库页：导入按钮、列表、底下的试听与删除。"""
    left = panel.left + MARGIN
    width = panel.width - 2 * MARGIN
    import_rect = pygame.Rect(left, top, 110, 24)
    hint = pygame.Rect(left + 118, top, max(0, width - 118), 24)
    list_top = top + 32
    list_bottom = panel.bottom - 12 - BUTTON_HEIGHT - 10
    area = pygame.Rect(
        left, list_top, width - SOUND_SCROLLBAR - 6, max(24, list_bottom - list_top)
    )
    items = editor.sound_library_items()
    step = SOUND_ROW_HEIGHT + SOUND_ROW_GAP
    content = max(0, len(items) * step - SOUND_ROW_GAP)
    scroll = max(
        0.0, min(float(editor.sound_library_scroll), max(0.0, content - area.height))
    )
    editor.sound_library_scroll = scroll
    rows = []
    for index, (key, value) in enumerate(items):
        y = area.top + index * step - round(scroll)
        if y + SOUND_ROW_HEIGHT <= area.top or y >= area.bottom:
            continue
        rect = pygame.Rect(area.left, y, area.width, SOUND_ROW_HEIGHT).clip(area)
        if rect.height > 0:
            rows.append({"rect": rect, "key": key, "path": editor.sound_library_path(key)})
    button_y = panel.bottom - 12 - BUTTON_HEIGHT
    preview = pygame.Rect(left, button_y, 110, BUTTON_HEIGHT)
    delete = pygame.Rect(preview.right + 8, button_y, 110, BUTTON_HEIGHT)
    return {
        "area": area,
        "import": import_rect,
        "hint": hint,
        "rows": rows,
        "content": content,
        "scroll": scroll,
        "preview": preview,
        "delete": delete,
    }


def draw_sound_library(
    surface: pygame.Surface, editor: "Editor", font: pygame.font.Font, geometry: dict
) -> None:
    draw_button(surface, font, geometry["import"], "导入声音…")
    hint = font.render(
        "点一行选中；导入只记相对路径，不复制文件。", True, DIM_TEXT
    )
    surface.blit(
        hint,
        (
            geometry["hint"].left,
            geometry["hint"].centery - hint.get_height() // 2,
        ),
    )

    area = geometry["area"]
    pygame.draw.rect(surface, (44, 44, 50), area)
    pygame.draw.rect(surface, (70, 70, 78), area, 1)
    if not geometry["rows"] and not geometry["content"]:
        empty = font.render("还没有声音：点「导入声音…」开始。", True, DIM_TEXT)
        surface.blit(empty, (area.centerx - empty.get_width() // 2, area.top + 10))
    previous = surface.get_clip()
    surface.set_clip(previous.clip(area))
    for row in geometry["rows"]:
        selected = row["key"] == editor.sound_selected
        pygame.draw.rect(surface, (62, 62, 72) if selected else (48, 48, 54), row["rect"])
        pygame.draw.rect(
            surface, HIGHLIGHT if selected else (86, 86, 94), row["rect"], 1
        )
        label = font.render(row["key"], True, HIGHLIGHT if selected else TEXT)
        surface.blit(
            label,
            (row["rect"].left + 6, row["rect"].centery - label.get_height() // 2),
            (0, 0, max(1, row["rect"].width - 12), label.get_height()),
        )
        name = font.render(
            _file_name(row["path"]), True, DIM_TEXT
        )
        surface.blit(
            name,
            (
                row["rect"].right - 8 - name.get_width(),
                row["rect"].centery - name.get_height() // 2,
            ),
            (0, 0, max(1, row["rect"].width // 2), name.get_height()),
        )
    surface.set_clip(previous)
    draw_scrollbar(surface, area, geometry["content"], geometry["scroll"])

    draw_button(surface, font, geometry["preview"], "试听 / 停止")
    draw_button(surface, font, geometry["delete"], "删除")


def _file_name(path: str | None) -> str:
    if not path:
        return ""
    return path.replace("\\", "/").rsplit("/", 1)[-1]


# ---- 选 BGM 的下拉 ---------------------------------------------------
def sound_menu_options(editor: "Editor") -> list:
    """下拉的选项：「（无）」加上声音库里的每一个键。"""
    options = [("（无）", "")]
    for key in sorted(editor.sound_library):
        options.append((key_label(editor.sound_library, key), key))
    return options


def sound_menu_geometry(
    editor: "Editor", anchor: pygame.Rect | None, window: pygame.Rect
) -> dict | None:
    """「选择…」下面摊开的声音列表：贴在按钮下面，放不下就往上翻。"""
    if editor.sound_menu is None or anchor is None:
        return None
    options = sound_menu_options(editor)
    visible = min(SOUND_MENU_ROWS, len(options))
    height = visible * ROW_HEIGHT + 2
    top = anchor.bottom + 2
    if top + height > window.bottom - 4:
        top = max(window.top + 4, anchor.top - 2 - height)
    width = max(anchor.width, SOUND_MENU_MIN_WIDTH)
    left = max(window.left + 4, min(anchor.left, window.right - 4 - width))
    popup = pygame.Rect(left, top, width, height)
    scroll = max(
        0,
        min(
            int(editor.sound_menu.get("scroll") or 0),
            max(0, len(options) - visible),
        ),
    )
    editor.sound_menu["scroll"] = scroll
    rows = [
        (
            pygame.Rect(
                popup.left, popup.top + 1 + index * ROW_HEIGHT, popup.width - 2, ROW_HEIGHT
            ),
            label,
            value,
        )
        for index, (label, value) in enumerate(options[scroll : scroll + visible])
    ]
    return {"popup": popup, "rows": rows, "total": len(options), "scroll": scroll}


def draw_sound_menu(
    surface: pygame.Surface, editor: "Editor", font: pygame.font.Font, menu: dict | None
) -> None:
    if menu is None:
        return
    pygame.draw.rect(surface, DIALOG_BG, menu["popup"])
    pygame.draw.rect(surface, DIALOG_BORDER, menu["popup"], 1)
    current = editor.sound_menu_value()
    mouse = pygame.mouse.get_pos()
    for rect, label, value in menu["rows"]:
        if rect.collidepoint(mouse):
            pygame.draw.rect(surface, (100, 100, 110), rect)
        mark = "●" if value == current else " "
        text = font.render(f"{mark} {label}", True, TEXT)
        surface.blit(
            text,
            (rect.left + 6, rect.centery - text.get_height() // 2),
            (0, 0, max(1, rect.width - 10), text.get_height()),
        )
