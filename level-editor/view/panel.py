"""右侧详细面板：槽位几何、绘制与命中。"""

import pygame
from typing import TYPE_CHECKING

from core.constants import (
    BUTTON_BG,
    DETAIL_PANEL_WIDTH,
    DIALOG_BG,
    DIALOG_BORDER,
    DIM_TEXT,
    FOOTER,
    HEADER,
    HIGHLIGHT,
    KIND_HAS_NAME,
    KIND_TEXTURE,
    MARGIN,
    ROW_HEIGHT,
    TEXT,
)
from view.widgets import draw_button, draw_checkbox, draw_stepper, stepper_rects

if TYPE_CHECKING:
    from editing.editor import Editor

TRIGGER_LABEL_HEIGHT = 18
TRIGGER_CARD_HEIGHT = ROW_HEIGHT * 2     # 一行来源 / 行为，一行「仅触发一次」
TRIGGER_CARD_GAP = 2
TRIGGER_ADD_WIDTH = 140


def trigger_geometry(surface: pygame.Surface, editor: "Editor") -> dict | None:
    """属性行下面的触发器区：标题、每张卡片（来源 / 行为 / − / 仅触发一次）和「添加」按钮。

    这个种类不接触发器时返回 None；卡片顺着属性行往下排，数量多了会顶到底部按钮。
    """
    cards = editor.trigger_cards()
    if cards is None:
        return None
    panel = detail_panel_rect(surface)
    slots = detail_slots(surface, editor)
    top = slots[-1][0].bottom + 10 if slots else panel.top + 28
    label = pygame.Rect(
        panel.left + 10, top, panel.width - 20, TRIGGER_LABEL_HEIGHT
    )
    layouts = []
    y = label.bottom + 2
    for index in range(len(cards)):
        card = pygame.Rect(panel.left + 10, y, panel.width - 20, TRIGGER_CARD_HEIGHT)
        line = pygame.Rect(card.left, card.top + 1, card.width, ROW_HEIGHT - 2)
        minus = pygame.Rect(line.right - 18, line.top, 18, line.height)
        behavior_width = min(110, max(70, card.width // 3))
        behavior = pygame.Rect(
            minus.left - 6 - behavior_width, line.top, behavior_width, line.height
        )
        source = pygame.Rect(
            line.left, line.top, behavior.left - 6 - line.left, line.height
        )
        once = pygame.Rect(card.left, line.bottom + 2, card.width, ROW_HEIGHT - 2)
        layouts.append(
            {
                "index": index,
                "rect": card,
                "source": source,
                "behavior": behavior,
                "once": once,
                "minus": minus,
            }
        )
        y += TRIGGER_CARD_HEIGHT + TRIGGER_CARD_GAP
    add = pygame.Rect(panel.left + 10, y + 2, TRIGGER_ADD_WIDTH, ROW_HEIGHT)
    return {
        "label": label,
        "cards": layouts,
        "add": add,
    }


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
    """面板从上到下的槽位：('name', None) / ('row', 字段下标) / ('image', None)。

    有名字的对象最上面是名称输入框；贴图的「图片」下面插一个「选择图片」按钮。
    """
    panel = detail_panel_rect(surface)
    count = len(editor.dialog_rows())
    kind = editor.dialog["kind"] if editor.dialog else None
    slots = []
    if kind in KIND_HAS_NAME:
        slots.append(("name", None))
    for index in range(count):
        slots.append(("row", index))
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


def detail_image_rect(surface: pygame.Surface, editor: Editor) -> pygame.Rect | None:
    return detail_slot_rect(surface, editor, "image")


def field_rect(surface: pygame.Surface, editor: Editor, field: int) -> pygame.Rect | None:
    """某个字段的矩形：属性行，或者触发卡片上的下拉格子。"""
    for rect, index in detail_row_rects(surface, editor):
        if index == field:
            return rect
    trigger = trigger_geometry(surface, editor)
    if trigger is None:
        return None
    for layout in trigger["cards"]:
        if field == editor.trigger_field(layout["index"], "source"):
            return layout["source"]
        if field == editor.trigger_field(layout["index"], "behavior"):
            return layout["behavior"]
    return None


def dropdown_rects(surface: pygame.Surface, editor: Editor) -> list:
    """展开中的下拉列表：[(矩形, 显示文字, 值)]；没展开就是空列表。

    优先往字段下面展开，下面放不下就往上面展开，再放不下就按能放下的条数截断。
    """
    field = editor.dropdown_field
    if field is None:
        return []
    options = editor.dialog_options(field)
    if not options:
        return []
    row_rect = field_rect(surface, editor, field)
    if row_rect is None:
        return []

    item_height = ROW_HEIGHT - 2
    limit = surface.get_height() - FOOTER
    below = max(0, (limit - row_rect.bottom - 2) // item_height)
    above = max(0, (row_rect.top - HEADER - 2) // item_height)
    if below >= len(options) or below >= above:
        shown = min(len(options), max(1, below))
        top = row_rect.bottom + 2
    else:
        shown = min(len(options), max(1, above))
        top = row_rect.top - 2 - shown * item_height
    return [
        (
            pygame.Rect(row_rect.left, top + index * item_height, row_rect.width, item_height),
            label,
            value,
        )
        for index, (label, value) in enumerate(options[:shown])
    ]


def detail_button_rects(surface: pygame.Surface, editor: Editor) -> tuple:
    """属性面板底部的按钮：删除 / 关闭；贴图多一个「复制」。

    复制和关闭靠右，删除占剩下的位置并最多 110 宽；面板窄的时候删除缩到刚好放得下
    两个字，三个按钮不会叠在一起。
    """
    panel = detail_panel_rect(surface)
    y = panel.bottom - 32
    close_rect = pygame.Rect(panel.right - 10 - 66, y, 66, ROW_HEIGHT)
    texture = editor.dialog is not None and editor.dialog["kind"] == KIND_TEXTURE
    if not texture:
        delete_rect = pygame.Rect(panel.left + 10, y, min(110, panel.width - 86), ROW_HEIGHT)
        return delete_rect, close_rect, None
    copy_rect = pygame.Rect(close_rect.left - 8 - 56, y, 56, ROW_HEIGHT)
    room = copy_rect.left - 8 - (panel.left + 10)
    delete_rect = pygame.Rect(panel.left + 10, y, min(110, max(44, room)), ROW_HEIGHT)
    return delete_rect, close_rect, copy_rect


def selection_panel_buttons(surface: pygame.Surface) -> tuple:
    """多选面板底部的两个按钮：删除全部 / 取消。"""
    panel = detail_panel_rect(surface)
    y = panel.bottom - 32
    delete_rect = pygame.Rect(panel.left + 10, y, min(110, panel.width - 86), ROW_HEIGHT)
    close_rect = pygame.Rect(panel.right - 10 - 66, y, 66, ROW_HEIGHT)
    return delete_rect, close_rect


def draw_selection_panel(surface: pygame.Surface, editor: Editor, font: pygame.font.Font) -> None:
    """多选面板：只列对象清单和数量，不给属性。"""
    panel = detail_panel_rect(surface)
    pygame.draw.rect(surface, DIALOG_BG, panel)
    pygame.draw.rect(surface, DIALOG_BORDER, panel, 1)
    count = len(editor.selection)
    surface.blit(
        font.render(f"已选择 {count} 个对象", True, TEXT), (panel.left + 10, panel.top + 8)
    )

    top = panel.top + 34
    row = ROW_HEIGHT - 2
    visible = max(1, (panel.bottom - 76 - top) // row)
    for index, (kind, entry) in enumerate(editor.selection[:visible]):
        rect = pygame.Rect(panel.left + 8, top + index * row, panel.width - 16, row - 1)
        pygame.draw.rect(surface, (48, 48, 54), rect)
        text = font.render(editor.label_of(kind, entry), True, TEXT)
        surface.blit(
            text,
            (rect.left + 6, rect.centery - text.get_height() // 2),
            (0, 0, min(text.get_width(), rect.width - 10), text.get_height()),
        )
    if count > visible:
        more = font.render(f"…还有 {count - visible} 个", True, DIM_TEXT)
        surface.blit(more, (panel.left + 10, top + visible * row + 2))

    delete_rect, close_rect = selection_panel_buttons(surface)
    draw_button(surface, font, delete_rect, "删除全部")
    draw_button(surface, font, close_rect, "取消")


def _option_label(editor: Editor, field: int, value) -> str:
    """下拉字段当前值对应的显示文字；值不在选项里就退回原样。"""
    for label, option in editor.dialog_options(field) or []:
        if option == value:
            return label
    return str(value or "")


def _draw_trigger_cell(
    surface: pygame.Surface,
    font: pygame.font.Font,
    rect: pygame.Rect,
    text: str,
    selected: bool,
) -> None:
    """触发卡片上的一个下拉格子：文字靠左，右边一个小三角表示可以点开。"""
    pygame.draw.rect(surface, (62, 62, 72) if selected else (48, 48, 54), rect)
    pygame.draw.rect(surface, HIGHLIGHT if selected else (86, 86, 94), rect, 1)
    rendered = font.render(text, True, HIGHLIGHT if selected else TEXT)
    clip = max(1, rect.width - 20)
    surface.blit(
        rendered,
        (rect.left + 6, rect.centery - rendered.get_height() // 2),
        (0, 0, min(rendered.get_width(), clip), rendered.get_height()),
    )
    center_x = rect.right - 9
    pygame.draw.polygon(
        surface,
        HIGHLIGHT if selected else TEXT,
        [
            (center_x - 4, rect.centery - 2),
            (center_x + 4, rect.centery - 2),
            (center_x, rect.centery + 3),
        ],
    )


def _draw_minus(surface: pygame.Surface, font: pygame.font.Font, rect: pygame.Rect) -> None:
    """卡片右端的小方按钮：删掉这张卡片。"""
    pygame.draw.rect(surface, (80, 80, 90), rect)
    pygame.draw.rect(surface, (150, 150, 160), rect, 1)
    text = font.render("−", True, TEXT)
    surface.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))


def draw_trigger_section(
    surface: pygame.Surface, font: pygame.font.Font, editor: Editor, geometry: dict
) -> None:
    """触发器区：标题、每张卡片的来源 / 行为 / −，以及底下的添加按钮。"""
    label = geometry["label"]
    surface.blit(font.render("触发器", True, DIM_TEXT), (label.left, label.top))
    hint = font.render("来源 → 行为", True, DIM_TEXT)
    surface.blit(hint, (label.right - hint.get_width(), label.top))

    cards = editor.trigger_cards() or []
    for layout in geometry["cards"]:
        card = cards[layout["index"]]
        source_field = editor.trigger_field(layout["index"], "source")
        behavior_field = editor.trigger_field(layout["index"], "behavior")
        once_field = editor.trigger_field(layout["index"], "once")
        _draw_trigger_cell(
            surface,
            font,
            layout["source"],
            card.get("source") or "无",
            editor.dialog_field == source_field,
        )
        _draw_trigger_cell(
            surface,
            font,
            layout["behavior"],
            _option_label(editor, behavior_field, card.get("behavior")),
            editor.dialog_field == behavior_field,
        )
        _draw_minus(surface, font, layout["minus"])
        selected = editor.dialog_field == once_field
        pygame.draw.rect(surface, (62, 62, 72) if selected else (48, 48, 54), layout["once"])
        pygame.draw.rect(surface, HIGHLIGHT if selected else (86, 86, 94), layout["once"], 1)
        draw_checkbox(
            surface,
            font,
            layout["once"],
            "仅触发一次",
            bool(card.get("once", False)),
            selected,
            inset=6,
        )
    draw_button(surface, font, geometry["add"], "＋ 添加触发器")


def draw_detail_panel(surface: pygame.Surface, editor: Editor, font: pygame.font.Font) -> None:
    panel = detail_panel_rect(surface)
    pygame.draw.rect(surface, DIALOG_BG, panel)
    pygame.draw.rect(surface, DIALOG_BORDER, panel, 1)
    surface.blit(font.render(editor.dialog_title(), True, TEXT), (panel.left + 10, panel.top + 8))

    rows = editor.dialog_rows()
    for rect, index in detail_row_rects(surface, editor):
        label, value = rows[index]
        selected = index == editor.dialog_field
        checked = editor.dialog_checkbox(index)
        pygame.draw.rect(surface, (62, 62, 72) if selected else (48, 48, 54), rect)
        pygame.draw.rect(surface, HIGHLIGHT if selected else (86, 86, 94), rect, 1)
        if checked is not None:
            # 「是 / 否」的项画成复选框：整行点一下就勾上或取消
            draw_checkbox(surface, font, rect, label, checked, selected, inset=6)
            continue
        typing = selected and editor.number_buffer is not None
        if typing:
            # 正在键盘输入：显示输入框内容加光标，而不是已生效的值
            value = f"{editor.number_buffer}|"
        left, right = stepper_rects(rect)
        text = font.render(f"{label}：{value}", True, HIGHLIGHT if selected else TEXT)
        options = editor.dialog_options(index)
        is_number = editor.dialog_number_value(index) is not None
        # 只有数字字段让出右边的加减按钮；下拉和纯显示的行用满整行
        clip = max(1, left.left - rect.left - 8) if (options is not None or is_number) else rect.width - 12
        surface.blit(
            text,
            (rect.left + 6, rect.centery - text.get_height() // 2),
            (0, 0, min(text.get_width(), clip), text.get_height()),
        )
        if options is not None:
            # 选择型字段：右边画个向下的小三角，点开是一列选项
            pygame.draw.polygon(
                surface,
                HIGHLIGHT if selected else TEXT,
                [
                    (right.centerx - 4, right.centery - 2),
                    (right.centerx + 4, right.centery - 2),
                    (right.centerx, right.centery + 3),
                ],
            )
        elif is_number:
            draw_stepper(surface, left, -1)
            draw_stepper(surface, right, 1)
        # 纯显示的行（比如贴图路径）不画加减、也点不中

    name_rect = detail_slot_rect(surface, editor, "name")
    if name_rect is not None:
        focused = editor.name_focused
        pygame.draw.rect(surface, (62, 62, 72) if focused else (48, 48, 54), name_rect)
        pygame.draw.rect(surface, HIGHLIGHT if focused else (86, 86, 94), name_rect, 1)
        name = editor.dialog["entry"].get("name", "")
        caret = "|" if focused else ""
        text = font.render(f"名称：{name if name else '（空）'}{caret}", True, HIGHLIGHT if focused else TEXT)
        clip = max(1, name_rect.width - 12)
        surface.blit(
            text,
            (name_rect.left + 6, name_rect.centery - text.get_height() // 2),
            (0, 0, min(text.get_width(), clip), text.get_height()),
        )

    trigger = trigger_geometry(surface, editor)
    if trigger is not None:
        draw_trigger_section(surface, font, editor, trigger)

    delete_rect, close_rect, copy_rect = detail_button_rects(surface, editor)
    texture = editor.dialog is not None and editor.dialog["kind"] == KIND_TEXTURE
    draw_button(surface, font, delete_rect, "删除" if texture else "删除对象")
    if copy_rect is not None:
        draw_button(surface, font, copy_rect, "复制")
    draw_button(surface, font, close_rect, "关闭")

    image_rect = detail_image_rect(surface, editor)
    if image_rect is not None:
        hovered = image_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surface, (100, 100, 110) if hovered else BUTTON_BG, image_rect)
        pygame.draw.rect(surface, DIALOG_BORDER, image_rect, 1)
        text = font.render("选择图片", True, TEXT)
        surface.blit(text, (image_rect.left + 8, image_rect.centery - text.get_height() // 2))

    # 展开的下拉列表画在最上面，盖住下面的行和按钮
    if editor.dropdown_field is None:
        return
    current = editor.dialog_option_value(editor.dropdown_field)
    for rect, label, value in dropdown_rects(surface, editor):
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surface, (100, 100, 110) if hovered else DIALOG_BG, rect)
        pygame.draw.rect(surface, DIALOG_BORDER, rect, 1)
        mark = "•" if value == current else " "
        text = font.render(f"{mark} {label}", True, TEXT)
        surface.blit(
            text,
            (rect.left + 6, rect.centery - text.get_height() // 2),
            (0, 0, min(text.get_width(), rect.width - 10), text.get_height()),
        )
