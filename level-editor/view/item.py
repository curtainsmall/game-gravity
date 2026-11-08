"""游戏配置的「物品」页：管理触发源可以解锁的物品（图标 + 说明图一对）。

一个物品就是一对图片：图标给背包格子，说明图给 B 背包右侧的 1:1 区域。
两张图都只记相对 game.json 的路径，不复制文件；被触发源引用着的物品不能删除。
"""

import os

import pygame

from core.constants import (
    BUTTON_HEIGHT,
    DIALOG_BG,
    DIALOG_BORDER,
    DIM_TEXT,
    HIGHLIGHT,
    MARGIN,
    TEXT,
)
from view.widgets import draw_button, draw_scrollbar

ITEM_ROW_HEIGHT = 32
ITEM_ROW_GAP = 4
ITEM_SCROLLBAR = 10
ITEM_THUMB = 22

ITEM_BUTTON = 96
ITEM_BUTTON_GAP = 8


def item_library_height(top_offset: int) -> int:
    """物品页固定这么高：五行加上面的按钮和最下面一行按钮。"""
    return top_offset + 32 + 5 * (ITEM_ROW_HEIGHT + ITEM_ROW_GAP) + 46


def item_library_geometry(
    surface: pygame.Surface, editor, panel: pygame.Rect, top: int
) -> dict:
    """物品页：添加按钮、列表，底下的换图与删除。"""
    left = panel.left + MARGIN
    width = panel.width - 2 * MARGIN
    add = pygame.Rect(left, top, 110, 24)
    hint = pygame.Rect(left + 118, top, max(0, width - 118), 24)
    list_top = top + 32
    list_bottom = panel.bottom - 12 - BUTTON_HEIGHT - 10
    area = pygame.Rect(
        left, list_top, width - ITEM_SCROLLBAR - 6, max(24, list_bottom - list_top)
    )
    items = editor.item_library_items()
    step = ITEM_ROW_HEIGHT + ITEM_ROW_GAP
    content = max(0, len(items) * step - ITEM_ROW_GAP)
    scroll = max(0.0, min(float(editor.item_library_scroll), max(0.0, content - area.height)))
    editor.item_library_scroll = scroll
    rows = []
    for index, (key, entry) in enumerate(items):
        y = area.top + index * step - round(scroll)
        if y + ITEM_ROW_HEIGHT < area.top or y > area.bottom:
            continue
        rows.append(
            {
                "key": key,
                "entry": entry,
                "rect": pygame.Rect(area.left, y, area.width, ITEM_ROW_HEIGHT),
            }
        )
    button_y = panel.bottom - 12 - BUTTON_HEIGHT
    icon = pygame.Rect(left, button_y, ITEM_BUTTON, BUTTON_HEIGHT)
    description = pygame.Rect(
        icon.right + ITEM_BUTTON_GAP, button_y, ITEM_BUTTON, BUTTON_HEIGHT
    )
    delete = pygame.Rect(
        description.right + ITEM_BUTTON_GAP, button_y, 76, BUTTON_HEIGHT
    )
    return {
        "add": add,
        "hint": hint,
        "area": area,
        "rows": rows,
        "content": content,
        "scroll": scroll,
        "empty": not items,
        "icon": icon,
        "description": description,
        "delete": delete,
    }


def draw_item_library(
    surface: pygame.Surface, editor, font: pygame.font.Font, geometry: dict
) -> None:
    draw_button(surface, font, geometry["add"], "添加物品…")
    hint = font.render("图标 + 说明图；被触发源引用着的物品不能删除", True, DIM_TEXT)
    surface.blit(
        hint,
        (geometry["hint"].left, geometry["hint"].centery - hint.get_height() // 2),
    )

    area = geometry["area"]
    pygame.draw.rect(surface, DIALOG_BG, area)
    pygame.draw.rect(surface, DIALOG_BORDER, area, 1)
    if geometry["empty"]:
        text = font.render("还没有物品：点「添加物品…」选两张图。", True, DIM_TEXT)
        surface.blit(text, (area.centerx - text.get_width() // 2, area.centery - 8))
    else:
        previous = surface.get_clip()
        surface.set_clip(previous.clip(area))
        mouse = pygame.mouse.get_pos()
        for row in geometry["rows"]:
            selected = row["key"] == editor.item_selected
            hovered = row["rect"].collidepoint(mouse)
            pygame.draw.rect(
                surface,
                (74, 74, 84) if selected else (100, 100, 110) if hovered else (48, 48, 54),
                row["rect"],
            )
            pygame.draw.rect(
                surface,
                HIGHLIGHT if selected else (86, 86, 94),
                row["rect"],
                1,
            )
            thumb = pygame.Rect(
                row["rect"].left + 6,
                row["rect"].centery - ITEM_THUMB // 2,
                ITEM_THUMB,
                ITEM_THUMB,
            )
            picture = editor.item_picture(row["key"], "icon", ITEM_THUMB)
            if picture is not None:
                surface.blit(picture, thumb)
            else:
                pygame.draw.rect(surface, (120, 120, 120), thumb)
                pygame.draw.rect(surface, (70, 70, 70), thumb, 1)
            name = font.render(row["key"], True, HIGHLIGHT if selected else TEXT)
            surface.blit(
                name,
                (thumb.right + 8, row["rect"].centery - name.get_height() // 2),
                (0, 0, max(1, row["rect"].width - 220), name.get_height()),
            )
            description = os.path.basename(
                str(row["entry"].get("description") or "")
            )
            label = font.render(description, True, DIM_TEXT)
            surface.blit(
                label,
                (
                    row["rect"].right - 8 - label.get_width(),
                    row["rect"].centery - label.get_height() // 2,
                ),
                (0, 0, max(1, row["rect"].width // 2), label.get_height()),
            )
        surface.set_clip(previous)
        draw_scrollbar(surface, area, geometry["content"], geometry["scroll"])

    draw_button(surface, font, geometry["icon"], "换图标…")
    draw_button(surface, font, geometry["description"], "换说明图…")
    draw_button(surface, font, geometry["delete"], "删除")
