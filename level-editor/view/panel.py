"""右侧详细面板：槽位几何、绘制与命中。"""

import pygame
from typing import TYPE_CHECKING

from core.constants import (
    BUTTON_BG,
    DETAIL_PANEL_WIDTH,
    DIALOG_BG,
    DIALOG_BORDER,
    FOOTER,
    HEADER,
    HIGHLIGHT,
    KIND_HAS_NAME,
    KIND_MOVABLE,
    KIND_TEXTURE,
    MARGIN,
    ROW_HEIGHT,
    TEXT,
)
from view.widgets import draw_button, draw_stepper, stepper_rects

if TYPE_CHECKING:
    from editing.editor import Editor


def detail_panel_width(surface: pygame.Surface) -> int:
    return min(DETAIL_PANEL_WIDTH, max(180, surface.get_width() // 3))


def detail_panel_rect(surface: pygame.Surface) -> pygame.Rect:
    """右侧常驻的详细设置面板，和画布之间留一道 MARGIN 的缝。"""
    width = detail_panel_width(surface)
    return pygame.Rect(
        surface.get_width() - MARGIN - width,
        HEADER,
        width,
        surface.get_height() - HEADER - FOOTER,
    )


def detail_slots(surface: pygame.Surface, editor: Editor) -> list:
    """面板从上到下的槽位：('name', None) / ('row', 字段下标) / ('pick', None) / ('image', None)。

    有名字的对象最上面是名称输入框；可移动方块的「纵向偏移」下面插一个
    「选择目标位置」按钮；贴图的「图片」下面插一个「选择图片」按钮。
    """
    panel = detail_panel_rect(surface)
    count = len(editor.dialog_rows())
    kind = editor.dialog["kind"] if editor.dialog else None
    slots = []
    if kind in KIND_HAS_NAME:
        slots.append(("name", None))
    for index in range(count):
        slots.append(("row", index))
        if kind == KIND_MOVABLE and index == 5:
            slots.append(("pick", None))
        if kind == KIND_TEXTURE and index == 4:
            slots.append(("image", None))
    top = panel.top + 28
    bottom = panel.bottom - 34
    height = min(ROW_HEIGHT, max(16, (bottom - top) // max(1, len(slots))))
    return [
        (
            pygame.Rect(panel.left + 10, top + position * height, panel.width - 20, height - 2),
            slot_kind,
            index,
        )
        for position, (slot_kind, index) in enumerate(slots)
    ]


def detail_row_rects(surface: pygame.Surface, editor: Editor) -> list:
    return [(rect, index) for rect, kind, index in detail_slots(surface, editor) if kind == "row"]


def detail_slot_rect(surface: pygame.Surface, editor: Editor, wanted: str) -> pygame.Rect | None:
    for rect, kind, _ in detail_slots(surface, editor):
        if kind == wanted:
            return rect
    return None


def detail_pick_rect(surface: pygame.Surface, editor: Editor) -> pygame.Rect | None:
    return detail_slot_rect(surface, editor, "pick")


def detail_image_rect(surface: pygame.Surface, editor: Editor) -> pygame.Rect | None:
    return detail_slot_rect(surface, editor, "image")


def detail_button_rects(surface: pygame.Surface) -> tuple:
    panel = detail_panel_rect(surface)
    y = panel.bottom - 32
    delete_rect = pygame.Rect(panel.left + 10, y, min(110, panel.width - 86), ROW_HEIGHT)
    close_rect = pygame.Rect(panel.right - 10 - 66, y, 66, ROW_HEIGHT)
    return delete_rect, close_rect


def draw_detail_panel(surface: pygame.Surface, editor: Editor, font: pygame.font.Font) -> None:
    panel = detail_panel_rect(surface)
    pygame.draw.rect(surface, DIALOG_BG, panel)
    pygame.draw.rect(surface, DIALOG_BORDER, panel, 1)
    surface.blit(font.render(editor.dialog_title(), True, TEXT), (panel.left + 10, panel.top + 8))

    rows = editor.dialog_rows()
    for rect, index in detail_row_rects(surface, editor):
        label, value = rows[index]
        selected = index == editor.dialog_field
        typing = selected and editor.number_buffer is not None
        if typing:
            # 正在键盘输入：显示输入框内容加光标，而不是已生效的值
            value = f"{editor.number_buffer}|"
        pygame.draw.rect(surface, (62, 62, 72) if selected else (48, 48, 54), rect)
        pygame.draw.rect(surface, HIGHLIGHT if selected else (86, 86, 94), rect, 1)
        left, right = stepper_rects(rect)
        text = font.render(f"{label}: {value}", True, HIGHLIGHT if selected else TEXT)
        clip = max(1, left.left - rect.left - 8)
        surface.blit(
            text,
            (rect.left + 6, rect.centery - text.get_height() // 2),
            (0, 0, min(text.get_width(), clip), text.get_height()),
        )
        draw_stepper(surface, left, -1)
        draw_stepper(surface, right, 1)

    pick_rect = detail_pick_rect(surface, editor)
    if pick_rect is not None:
        if editor.picking_offset:
            pygame.draw.rect(surface, HIGHLIGHT, pick_rect)
            color = (20, 20, 20)
        else:
            hovered = pick_rect.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(surface, (100, 100, 110) if hovered else BUTTON_BG, pick_rect)
            pygame.draw.rect(surface, DIALOG_BORDER, pick_rect, 1)
            color = TEXT
        text = font.render("选择目标位置", True, color)
        surface.blit(text, (pick_rect.left + 8, pick_rect.centery - text.get_height() // 2))

    name_rect = detail_slot_rect(surface, editor, "name")
    if name_rect is not None:
        focused = editor.name_focused
        pygame.draw.rect(surface, (62, 62, 72) if focused else (48, 48, 54), name_rect)
        pygame.draw.rect(surface, HIGHLIGHT if focused else (86, 86, 94), name_rect, 1)
        name = editor.dialog["entry"].get("name", "")
        caret = "|" if focused else ""
        text = font.render(f"名称: {name if name else '（空）'}{caret}", True, HIGHLIGHT if focused else TEXT)
        clip = max(1, name_rect.width - 12)
        surface.blit(
            text,
            (name_rect.left + 6, name_rect.centery - text.get_height() // 2),
            (0, 0, min(text.get_width(), clip), text.get_height()),
        )

    delete_rect, close_rect = detail_button_rects(surface)
    draw_button(surface, font, delete_rect, "删除对象")
    draw_button(surface, font, close_rect, "关闭")

    image_rect = detail_image_rect(surface, editor)
    if image_rect is not None:
        hovered = image_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surface, (100, 100, 110) if hovered else BUTTON_BG, image_rect)
        pygame.draw.rect(surface, DIALOG_BORDER, image_rect, 1)
        text = font.render("选择图片", True, TEXT)
        surface.blit(text, (image_rect.left + 8, image_rect.centery - text.get_height() // 2))
