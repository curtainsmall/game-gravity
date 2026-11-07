"""过场编辑页：级联、声音，以及每张图一张卡片（和制作名单一样的卡片）。

关卡设置和游戏配置共用这一页，只是「跟随」的叫法不同（跟随本关 / 跟随制作名单）。
"""

import pygame

from core import cutscene as cutscene_data
from core.constants import (
    BUTTON_BG,
    BUTTON_HEIGHT,
    DIALOG_BORDER,
    DIM_TEXT,
    HIGHLIGHT,
    MARGIN,
    ROW_HEIGHT,
    TEXT,
)
from view.widgets import (
    draw_button,
    draw_checkbox,
    draw_scrollbar,
    draw_stepper,
    stepper_rects,
)

CARD_HEIGHT = 62
CARD_GAP = 6
CARD_PAD = 6
CARD_ICON = 20
CARD_ICON_GAP = 4
SOUND_ROW_STEP = 30
SOUND_BOX_WIDTH = 110
SOUND_BOX_GAP = 6
FIELD_HEIGHT = ROW_HEIGHT + 2


def _custom(editor) -> bool:
    return (
        editor.cutscene is not None
        and editor.cutscene["sound_mode"] == cutscene_data.SOUND_MODE_CUSTOM
    )


def cutscene_page_height(editor, top_offset: int) -> int:
    """过场页想要的面板高度；top_offset 是内容顶到面板顶的距离。"""
    count = len(editor.cutscene["pictures"]) if editor.cutscene else 0
    label_top = 120 if _custom(editor) else 60
    cards = max(1, count) * (CARD_HEIGHT + CARD_GAP)
    return top_offset + label_top + 24 + cards + 46


def cutscene_geometry(
    surface: pygame.Surface, editor, panel: pygame.Rect, top: int
) -> dict:
    """过场页：级联、声音两块在上面，图片卡片在下面（多了用滚轮翻）。"""
    state = editor.cutscene or cutscene_data.new_state()
    scope = editor.cutscene_scope
    left = panel.left + MARGIN
    width = panel.width - 2 * MARGIN

    cascade = pygame.Rect(left, top, 320, FIELD_HEIGHT)
    sound_y = top + SOUND_ROW_STEP
    sound_modes = {}
    x = left + 52
    for mode in cutscene_data.SOUND_ORDER:
        sound_modes[mode] = pygame.Rect(x, sound_y, SOUND_BOX_WIDTH, FIELD_HEIGHT)
        x += SOUND_BOX_WIDTH + SOUND_BOX_GAP

    sound_path = sound_browse = sound_preview = None
    sound_loop = sound_fade_in = sound_fade_out = None
    custom = state["sound_mode"] == cutscene_data.SOUND_MODE_CUSTOM
    if custom:
        row_y = top + 60
        sound_preview = pygame.Rect(left + width - 66, row_y, 66, FIELD_HEIGHT)
        sound_browse = pygame.Rect(sound_preview.left - 6 - 66, row_y, 66, FIELD_HEIGHT)
        sound_path = pygame.Rect(left, row_y, sound_browse.left - 6 - left, FIELD_HEIGHT)
        controls_y = top + 90
        sound_loop = pygame.Rect(left, controls_y, 150, FIELD_HEIGHT)
        fade_width = (width - 166 - 16) // 2
        sound_fade_in = pygame.Rect(left + 166, controls_y, fade_width, FIELD_HEIGHT)
        sound_fade_out = pygame.Rect(
            left + 166 + fade_width + 16, controls_y, fade_width, FIELD_HEIGHT
        )

    label_top = top + (120 if custom else 60)
    cards_top = label_top + 24
    add_y = panel.bottom - 12 - BUTTON_HEIGHT
    cards_area = pygame.Rect(left, cards_top, width, max(0, add_y - 8 - cards_top))
    row_step = CARD_HEIGHT + CARD_GAP
    count = len(state["pictures"])
    content_height = max(0.0, count * row_step - CARD_GAP)
    scroll = max(
        0.0, min(float(editor.cutscene_scroll), max(0.0, content_height - cards_area.height))
    )
    editor.cutscene_scroll = scroll
    editor.cutscene_area_height = float(cards_area.height)
    editor.cutscene_card_step = float(row_step)

    cards = []
    top = cards_area.top - round(scroll)
    for index in range(count):
        card = pygame.Rect(left, top + index * row_step, width, CARD_HEIGHT)
        remove = pygame.Rect(
            card.right - CARD_PAD - CARD_ICON, card.top + CARD_PAD, CARD_ICON, CARD_ICON
        )
        down = pygame.Rect(
            remove.left - CARD_ICON_GAP - CARD_ICON, card.top + CARD_PAD, CARD_ICON, CARD_ICON
        )
        up = pygame.Rect(
            down.left - CARD_ICON_GAP - CARD_ICON, card.top + CARD_PAD, CARD_ICON, CARD_ICON
        )
        browse = pygame.Rect(up.left - 6 - 66, card.top + CARD_PAD, 66, FIELD_HEIGHT)
        path = pygame.Rect(
            card.left + CARD_PAD,
            card.top + CARD_PAD,
            browse.left - 6 - (card.left + CARD_PAD),
            FIELD_HEIGHT,
        )
        field_y = card.top + CARD_PAD + 28
        field_width = (width - CARD_PAD * 2 - 16) // 3
        fade_in = pygame.Rect(card.left + CARD_PAD, field_y, field_width, FIELD_HEIGHT)
        hold = pygame.Rect(fade_in.right + 8, field_y, field_width, FIELD_HEIGHT)
        fade_out = pygame.Rect(hold.right + 8, field_y, field_width, FIELD_HEIGHT)
        cards.append(
            {
                "index": index,
                "card": card,
                "path": path,
                "browse": browse,
                "up": up,
                "down": down,
                "remove": remove,
                "fade_in": fade_in,
                "hold": hold,
                "fade_out": fade_out,
            }
        )

    return {
        "panel": panel,
        "cascade": cascade,
        "sound_modes": sound_modes,
        "scope": scope,
        "sound_path": sound_path,
        "sound_browse": sound_browse,
        "sound_preview": sound_preview,
        "sound_loop": sound_loop,
        "sound_fade_in": sound_fade_in,
        "sound_fade_out": sound_fade_out,
        "label_top": label_top,
        "cards_area": cards_area,
        "cards": cards,
        "visible": max(1, round(cards_area.height / row_step)),
        "scroll": scroll,
        "content_height": content_height,
        "count": count,
        "add": pygame.Rect(left, add_y, 110, BUTTON_HEIGHT),
    }


def _selected(editor, cell: tuple) -> bool:
    cells = editor.cutscene_cells()
    return editor.cutscene_field < len(cells) and cells[editor.cutscene_field] == cell


def _draw_cell(
    surface: pygame.Surface,
    font: pygame.font.Font,
    rect: pygame.Rect,
    text: str,
    selected: bool,
) -> None:
    """一格可编辑文本：选中时高亮、末尾带光标，长了就截断。"""
    pygame.draw.rect(surface, (62, 62, 72) if selected else (48, 48, 54), rect)
    pygame.draw.rect(surface, HIGHLIGHT if selected else (86, 86, 94), rect, 1)
    label = f"{text}|" if selected else text
    rendered = font.render(label, True, HIGHLIGHT if selected else TEXT)
    clip = max(1, rect.width - 12)
    surface.blit(
        rendered,
        (rect.left + 6, rect.centery - rendered.get_height() // 2),
        (0, 0, min(rendered.get_width(), clip), rendered.get_height()),
    )


def _draw_icon(surface: pygame.Surface, font: pygame.font.Font, rect: pygame.Rect, glyph: str) -> None:
    """卡片右上角的小方按钮：↑ ↓ −。"""
    pygame.draw.rect(surface, (80, 80, 90), rect)
    pygame.draw.rect(surface, (150, 150, 160), rect, 1)
    text = font.render(glyph, True, TEXT)
    surface.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))


def draw_cutscene_page(
    surface: pygame.Surface, editor, font: pygame.font.Font, geometry: dict
) -> None:
    state = editor.cutscene or cutscene_data.new_state()
    draw_checkbox(
        surface,
        font,
        geometry["cascade"],
        "级联（下一张的淡入和上一张的淡出重叠）",
        bool(state["cascade"]),
        _selected(editor, ("cascade",)),
    )

    sound_y = geometry["sound_modes"][cutscene_data.SOUND_ORDER[0]].top
    surface.blit(font.render("声音", True, DIM_TEXT), (geometry["cascade"].left, sound_y + 2))
    for mode, rect in geometry["sound_modes"].items():
        active = state["sound_mode"] == mode
        pygame.draw.rect(surface, (80, 80, 90) if active else BUTTON_BG, rect)
        pygame.draw.rect(surface, HIGHLIGHT if active else DIALOG_BORDER, rect, 1)
        label = font.render(
            cutscene_data.sound_mode_label(geometry["scope"], mode),
            True,
            HIGHLIGHT if active else TEXT,
        )
        surface.blit(label, (rect.centerx - label.get_width() // 2, rect.centery - label.get_height() // 2))

    if geometry["sound_path"] is not None:
        bgm = state["sound"]["bgm"]
        _draw_cell(
            surface,
            font,
            geometry["sound_path"],
            f"过场音乐：{bgm or '（无）'}",
            _selected(editor, ("sound_bgm",)),
        )
        draw_button(surface, font, geometry["sound_browse"], "浏览…")
        draw_button(surface, font, geometry["sound_preview"], "试听")
        loop_rect = geometry["sound_loop"]
        pygame.draw.rect(surface, (48, 48, 54), loop_rect)
        pygame.draw.rect(
            surface,
            HIGHLIGHT if _selected(editor, ("sound_loop",)) else (86, 86, 94),
            loop_rect,
            1,
        )
        draw_checkbox(
            surface,
            font,
            loop_rect,
            "循环播放",
            bool(state["sound"]["loop"]),
            _selected(editor, ("sound_loop",)),
            inset=6,
        )
        for field, rect, title, cell in (
            ("fade_in", geometry["sound_fade_in"], "淡入", ("sound_fade_in",)),
            ("fade_out", geometry["sound_fade_out"], "淡出", ("sound_fade_out",)),
        ):
            _draw_cell(
                surface,
                font,
                rect,
                f"{title}（秒）：{state['sound'][field]}",
                _selected(editor, cell),
            )
            left, right = stepper_rects(rect)
            draw_stepper(surface, left, -1)
            draw_stepper(surface, right, 1)

    label = "图片（每张图一张卡片；顺序就是播放顺序）"
    if geometry["content_height"] > geometry["cards_area"].height:
        label += "   滚轮上下滚动"
    surface.blit(
        font.render(label, True, DIM_TEXT), (geometry["cards_area"].left, geometry["label_top"] + 2)
    )
    if geometry["count"] == 0:
        surface.blit(
            font.render("还没有图片，点「添加图片」", True, DIM_TEXT),
            (geometry["cards_area"].left + 6, geometry["cards_area"].top + 6),
        )
    previous_clip = surface.get_clip()
    surface.set_clip(geometry["cards_area"])
    for layout in geometry["cards"]:
        picture = state["pictures"][layout["index"]]
        pygame.draw.rect(surface, (58, 58, 66), layout["card"])
        pygame.draw.rect(surface, (110, 110, 120), layout["card"], 1)
        _draw_cell(
            surface,
            font,
            layout["path"],
            f"路径：{picture['path'] or '（空）'}",
            _selected(editor, ("path", layout["index"])),
        )
        draw_button(surface, font, layout["browse"], "浏览…")
        _draw_icon(surface, font, layout["up"], "↑")
        _draw_icon(surface, font, layout["down"], "↓")
        _draw_icon(surface, font, layout["remove"], "−")
        for field, rect, title in (
            ("fade_in", layout["fade_in"], "淡入"),
            ("hold", layout["hold"], "停留"),
            ("fade_out", layout["fade_out"], "淡出"),
        ):
            _draw_cell(
                surface,
                font,
                rect,
                f"{title}（秒）：{picture[field]}",
                _selected(editor, (field, layout["index"])),
            )
            left, right = stepper_rects(rect)
            draw_stepper(surface, left, -1)
            draw_stepper(surface, right, 1)
    surface.set_clip(previous_clip)
    draw_scrollbar(surface, geometry["cards_area"], geometry["content_height"], geometry["scroll"])

    draw_button(surface, font, geometry["add"], "添加图片")
