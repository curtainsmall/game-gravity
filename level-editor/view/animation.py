"""动画相关的界面：游戏配置里的「动画集」页、单条动画的编辑弹窗、动画对象的链接弹窗。

- 动画集页只列 game.json 动画库里的条目：键名 + 一行帧缩略图，点一行打开编辑弹窗。
- 编辑弹窗：改键名、加/删/拖动帧、改每帧停留时长、循环、预览。
- 链接弹窗：动画对象自己的预设（通用 / 玩家）和每个动作左/右链接；链接的是动画库的键。
"""

import pygame

from core.animation import (
    PLAYER_ACTIONS,
    PRESET_GENERAL,
    PRESET_PLAYER,
    PRESETS,
    holds_of,
    preset_label,
)
from core.constants import (
    BUTTON_HEIGHT,
    DIALOG_BORDER,
    DIM_TEXT,
    HIGHLIGHT,
    MARGIN,
    ROW_HEIGHT,
    TEXT,
)
from core.helpers import resolve_level_path
from view.texture import draw_missing_texture, image_size, load_scaled
from view.widgets import (
    draw_button,
    draw_panel,
    draw_scrollbar,
    place_panel,
)

LIBRARY_ROW_HEIGHT = 28
LIBRARY_ROW_GAP = 4
LIBRARY_SCROLLBAR = 10

EDIT_PANEL_WIDTH = 700
EDIT_PANEL_HEIGHT = 480
EDIT_CELL_WIDTH = 100
EDIT_CELL_HEIGHT = 96
EDIT_THUMB_HEIGHT = 64
EDIT_CELL_GAP = 8
EDIT_DELAY_WIDTH = 64
EDIT_DELAY_HEIGHT = 20

LINK_PANEL_WIDTH = 560
LINK_GENERAL_HEIGHT = 196
LINK_PLAYER_HEIGHT = 340
LINK_ROW_HEIGHT = 28
LINK_POPUP_ROW = 22
LINK_POPUP_ROWS = 8


def library_page_height(top_offset: int) -> int:
    return top_offset + 32 + 5 * (LIBRARY_ROW_HEIGHT + LIBRARY_ROW_GAP) + 46


def library_geometry(
    surface: pygame.Surface, editor, panel: pygame.Rect, top: int
) -> dict:
    """动画集页：新建按钮、动画列表和滚动。"""
    left = panel.left + MARGIN
    width = panel.width - 2 * MARGIN
    new = pygame.Rect(left, top, 96, 24)
    hint = pygame.Rect(left + 104, top, width - 104, 24)
    list_top = top + 32
    list_bottom = panel.bottom - 12 - BUTTON_HEIGHT - 10
    area = pygame.Rect(left, list_top, width - LIBRARY_SCROLLBAR - 6, max(24, list_bottom - list_top))
    items = editor.animation_library_items()
    content = max(0, len(items) * (LIBRARY_ROW_HEIGHT + LIBRARY_ROW_GAP) - LIBRARY_ROW_GAP)
    scroll = max(0.0, min(float(editor.animation_library_scroll), max(0.0, content - area.height)))
    editor.animation_library_scroll = scroll
    rows = []
    for index, (key, clip) in enumerate(items):
        y = area.top + index * (LIBRARY_ROW_HEIGHT + LIBRARY_ROW_GAP) - round(scroll)
        if y + LIBRARY_ROW_HEIGHT < area.top or y > area.bottom:
            continue
        rows.append(
            {
                "key": key,
                "clip": clip,
                "rect": pygame.Rect(area.left, y, area.width, LIBRARY_ROW_HEIGHT),
                "count": len(clip.get("frames") or []),
            }
        )
    return {
        "new": new,
        "hint": hint,
        "area": area,
        "rows": rows,
        "content": content,
        "scroll": scroll,
        "empty": not items,
    }


def draw_library_page(
    surface: pygame.Surface, editor, font: pygame.font.Font, geometry: dict
) -> None:
    draw_button(surface, font, geometry["new"], "新建动画")
    hint = font.render("点一行编辑；被动画对象引用着的动画不能改名或删除", True, DIM_TEXT)
    surface.blit(hint, (geometry["hint"].left, geometry["hint"].centery - hint.get_height() // 2))

    area = geometry["area"]
    pygame.draw.rect(surface, (44, 44, 50), area)
    pygame.draw.rect(surface, (70, 70, 78), area, 1)
    if geometry["empty"]:
        text = font.render("还没有动画：点「新建动画」开始。", True, DIM_TEXT)
        surface.blit(text, (area.centerx - text.get_width() // 2, area.centery - 8))
        return

    previous = surface.get_clip()
    surface.set_clip(previous.clip(area))
    mouse = pygame.mouse.get_pos()
    for row in geometry["rows"]:
        hovered = row["rect"].collidepoint(mouse)
        pygame.draw.rect(surface, (100, 100, 110) if hovered else (48, 48, 54), row["rect"])
        pygame.draw.rect(surface, (86, 86, 94), row["rect"], 1)
        name = font.render(row["key"], True, HIGHLIGHT if hovered else TEXT)
        surface.blit(
            name,
            (row["rect"].left + 8, row["rect"].centery - name.get_height() // 2),
            (0, 0, row["rect"].width - 120, name.get_height()),
        )
        count = font.render(f"共 {row['count']} 帧", True, DIM_TEXT)
        surface.blit(
            count,
            (row["rect"].right - 8 - count.get_width(), row["rect"].centery - count.get_height() // 2),
        )
    surface.set_clip(previous)
    draw_scrollbar(surface, area, geometry["content"], geometry["scroll"])


# ---- 单条动画的编辑弹窗 ---------------------------------------------
def animation_edit_geometry(surface: pygame.Surface, editor) -> dict:
    edit = editor.animation_edit
    width = min(EDIT_PANEL_WIDTH, max(360, surface.get_width() - 2 * MARGIN))
    panel = place_panel(surface, pygame.Rect(0, 0, width, EDIT_PANEL_HEIGHT))
    if edit is None:
        return {"panel": panel}
    left = panel.left + 16
    width = panel.width - 32
    title = pygame.Rect(left, panel.top + 10, width, 24)
    name = pygame.Rect(left, title.bottom + 8, width, 24)
    button_y = panel.bottom - 12 - BUTTON_HEIGHT
    controls_y = button_y - 8 - 24
    grid = pygame.Rect(
        left, name.bottom + 10, width - LIBRARY_SCROLLBAR - 6, max(24, controls_y - 10 - (name.bottom + 10))
    )
    columns = max(1, (grid.width + EDIT_CELL_GAP) // (EDIT_CELL_WIDTH + EDIT_CELL_GAP))
    frames = edit["frames"]
    holds = [animation_hold(value) for value in holds_of({"frames": frames, "holds": edit["holds"]})]
    rows = (len(frames) + columns - 1) // columns if frames else 0
    content = max(0, rows * (EDIT_CELL_HEIGHT + EDIT_CELL_GAP) - EDIT_CELL_GAP)
    scroll = max(0.0, min(float(edit["scroll"]), max(0.0, content - grid.height)))
    edit["scroll"] = scroll
    cells = []
    for index, frame in enumerate(frames):
        column = index % columns
        row = index // columns
        thumb = pygame.Rect(
            grid.left + column * (EDIT_CELL_WIDTH + EDIT_CELL_GAP),
            grid.top + row * (EDIT_CELL_HEIGHT + EDIT_CELL_GAP) - round(scroll),
            EDIT_CELL_WIDTH,
            EDIT_THUMB_HEIGHT,
        )
        if thumb.bottom < grid.top or thumb.top > grid.bottom:
            continue
        delay = pygame.Rect(
            thumb.centerx - EDIT_DELAY_WIDTH // 2,
            thumb.bottom + 4,
            EDIT_DELAY_WIDTH,
            EDIT_DELAY_HEIGHT,
        )
        cells.append({"index": index, "frame": frame, "thumb": thumb, "delay": delay, "hold": holds[index]})
    add = pygame.Rect(left, controls_y, 26, 24)
    remove = pygame.Rect(add.right + 4, controls_y, 26, 24)
    preview = pygame.Rect(remove.right + 10, controls_y, 82, 24)
    delete = pygame.Rect(left, button_y, 96, BUTTON_HEIGHT)
    ok = pygame.Rect(panel.right - 16 - 76, button_y, 76, BUTTON_HEIGHT)
    cancel = pygame.Rect(ok.left - 8 - 76, button_y, 76, BUTTON_HEIGHT)
    return {
        "panel": panel,
        "title": title,
        "name": name,
        "grid": grid,
        "cells": cells,
        "columns": columns,
        "cell_width": EDIT_CELL_WIDTH,
        "cell_height": EDIT_CELL_HEIGHT,
        "cell_gap": EDIT_CELL_GAP,
        "count": len(frames),
        "content": content,
        "scroll": scroll,
        "add": add,
        "remove": remove,
        "preview": preview,
        "delete": delete,
        "ok": ok,
        "cancel": cancel,
    }


def animation_hold(value: float) -> float:
    return max(0.01, min(10.0, float(value)))


def draw_animation_edit(
    surface: pygame.Surface, editor, font: pygame.font.Font
) -> None:
    edit = editor.animation_edit
    if edit is None:
        return
    geometry = animation_edit_geometry(surface, editor)
    panel = geometry["panel"]
    draw_panel(surface, panel)
    title = font.render(
        "编辑动画（预览中）" if edit["previewing"] else "编辑动画",
        True,
        TEXT,
    )
    surface.blit(title, (geometry["title"].left, geometry["title"].top))

    name_rect = geometry["name"]
    focused = edit["name_focus"]
    pygame.draw.rect(surface, (62, 62, 72) if focused else (48, 48, 54), name_rect)
    pygame.draw.rect(surface, HIGHLIGHT if focused else (86, 86, 94), name_rect, 1)
    caret = "|" if focused else ""
    name_text = font.render(f"名称：{edit['name']}{caret}", True, HIGHLIGHT if focused else TEXT)
    surface.blit(
        name_text,
        (name_rect.left + 6, name_rect.centery - name_text.get_height() // 2),
        (0, 0, max(1, name_rect.width - 12), name_text.get_height()),
    )

    grid = geometry["grid"]
    pygame.draw.rect(surface, (44, 44, 50), grid)
    pygame.draw.rect(surface, (70, 70, 78), grid, 1)
    previous = surface.get_clip()
    surface.set_clip(previous.clip(grid))
    shown = editor.animation_edit_shown_frame()
    for cell in geometry["cells"]:
        highlight = cell["index"] == shown
        _draw_frame(surface, cell["thumb"], edit, cell["index"], editor.media_base_dir, highlight)
        _draw_delay(surface, font, cell, edit["delay"])
        number = font.render(str(cell["index"] + 1), True, DIM_TEXT)
        surface.blit(number, (cell["thumb"].left + 2, cell["thumb"].top + 1))
    if not geometry["cells"]:
        hint = font.render(
            "还没有帧：点「＋」选图片或 GIF。" if not edit["frames"] else "",
            True,
            DIM_TEXT,
        )
        surface.blit(hint, (grid.centerx - hint.get_width() // 2, grid.centery - 8))
    drag = edit["drag"]
    if drag is not None and drag["moved"]:
        x, top = _edit_drag_marker(geometry, drag["slot"])
        pygame.draw.line(surface, HIGHLIGHT, (x, top), (x, top + EDIT_THUMB_HEIGHT), 3)
    surface.set_clip(previous)
    draw_scrollbar(surface, grid, geometry["content"], geometry["scroll"])

    draw_button(surface, font, geometry["add"], "＋")
    draw_button(surface, font, geometry["remove"], "−")
    draw_button(surface, font, geometry["preview"], "停止预览" if edit["previewing"] else "预览")
    hint = font.render("循环在动画对象的链接上设置", True, DIM_TEXT)
    surface.blit(hint, (geometry["preview"].right + 10, geometry["preview"].centery - 8))
    draw_button(surface, font, geometry["delete"], "删除动画")
    draw_button(surface, font, geometry["ok"], "确定")
    draw_button(surface, font, geometry["cancel"], "取消")

    count = font.render(f"共 {len(edit['frames'])} 帧", True, DIM_TEXT)
    surface.blit(
        count,
        (
            geometry["panel"].right - 16 - count.get_width(),
            geometry["preview"].centery - 8,
        ),
    )


def _edit_drag_marker(geometry: dict, slot: int) -> tuple:
    grid = geometry["grid"]
    columns = max(1, geometry["columns"])
    row = slot // columns
    column = slot % columns
    x = grid.left + column * (EDIT_CELL_WIDTH + EDIT_CELL_GAP) - EDIT_CELL_GAP // 2
    x = max(grid.left + 2, min(x, grid.right - 2))
    top = grid.top + row * (EDIT_CELL_HEIGHT + EDIT_CELL_GAP) - round(geometry["scroll"]) + 2
    top = max(grid.top + 2, min(top, grid.bottom - EDIT_THUMB_HEIGHT - 2))
    return x, top


def _draw_frame(
    surface: pygame.Surface,
    rect: pygame.Rect,
    clip: dict,
    index: int,
    base_dir: str | None,
    selected: bool,
) -> None:
    pygame.draw.rect(surface, (40, 40, 46), rect)
    frames = clip.get("frames") or []
    path = resolve_level_path(frames[index], base_dir) if 0 <= index < len(frames) else None
    image = None
    if path is not None:
        size = image_size(path)
        if size is not None:
            image = load_scaled(path, _fit_within(size, rect.size), True)
    if image is None:
        draw_missing_texture(surface, rect)
    else:
        surface.blit(image, image.get_rect(center=rect.center))
    pygame.draw.rect(surface, HIGHLIGHT if selected else (86, 86, 94), rect, 2 if selected else 1)


def _fit_within(size: tuple, box: tuple) -> tuple:
    """等比缩放到 box 里，宽高都不超过它。"""
    width, height = size
    if width <= 0 or height <= 0:
        return max(1, box[0]), max(1, box[1])
    scale = min(box[0] / width, box[1] / height)
    return max(1, round(width * scale)), max(1, round(height * scale))


def _draw_delay(
    surface: pygame.Surface, font: pygame.font.Font, cell: dict, delay: dict | None
) -> None:
    rect = cell["delay"]
    active = delay is not None and delay["index"] == cell["index"]
    pygame.draw.rect(surface, (62, 62, 72) if active else (48, 48, 54), rect)
    pygame.draw.rect(surface, HIGHLIGHT if active else (86, 86, 94), rect, 1)
    text = delay["text"] if active else f"{cell['hold']:g}s"
    rendered = font.render(text, True, TEXT if active else DIM_TEXT)
    surface.blit(
        rendered,
        (rect.left + 5, rect.centery - rendered.get_height() // 2),
        (0, 0, max(1, rect.width - 10), rendered.get_height()),
    )


# ---- 动画对象的链接弹窗 ---------------------------------------------
def animation_link_geometry(surface: pygame.Surface, editor) -> dict:
    link = editor.animation_link
    height = LINK_GENERAL_HEIGHT if link is not None and link["preset"] == PRESET_GENERAL else LINK_PLAYER_HEIGHT
    panel = place_panel(surface, pygame.Rect(0, 0, LINK_PANEL_WIDTH, height))
    left = panel.left + 16
    width = panel.width - 32
    title = pygame.Rect(left, panel.top + 10, width, 24)
    preset = pygame.Rect(left, title.bottom + 8, 220, 24)
    rows_top = preset.bottom + 12
    button_y = panel.bottom - 12 - BUTTON_HEIGHT
    rows = []
    if link is not None:
        if link["preset"] == PRESET_GENERAL:
            y = rows_top
            label = pygame.Rect(left, y, 70, 24)
            field = pygame.Rect(left + 78, y, width - 78, 24)
            rows.append({"kind": "general", "label": label, "field": field})
        else:
            for action, action_text in PLAYER_ACTIONS:
                y = rows_top + len(rows) * LINK_ROW_HEIGHT
                label = pygame.Rect(left, y, 64, 24)
                left_field = pygame.Rect(left + 72, y, 200, 24)
                right_field = pygame.Rect(left_field.right + 8, y, 200, 24)
                rows.append(
                    {
                        "kind": "player",
                        "action": action,
                        "label": label,
                        "left": left_field,
                        "right": right_field,
                    }
                )
    hint = pygame.Rect(left, rows_top + (1 if link is not None and link["preset"] == PRESET_GENERAL else len(rows)) * LINK_ROW_HEIGHT + 8, width, 20)
    ok = pygame.Rect(panel.right - 16 - 76, button_y, 76, BUTTON_HEIGHT)
    cancel = pygame.Rect(ok.left - 8 - 76, button_y, 76, BUTTON_HEIGHT)
    geometry = {
        "panel": panel,
        "title": title,
        "preset": preset,
        "rows": rows,
        "hint": hint,
        "ok": ok,
        "cancel": cancel,
        "popup": None,
        "popup_rects": [],
    }
    if link is not None and link["dropdown"] is not None:
        anchor = _link_field_rect(geometry, link["dropdown"])
        if anchor is not None:
            options = (
                [(label, value) for value, label in PRESETS]
                if link["dropdown"] == "preset"
                else editor.animation_link_options()
            )
            geometry.update(_popup_geometry(panel, anchor, options, int(link.get("dropdown_scroll") or 0)))
    return geometry


def _link_field_rect(geometry: dict, field) -> pygame.Rect | None:
    if field == "preset":
        return geometry["preset"]
    for row in geometry["rows"]:
        if row["kind"] == "general":
            return row["field"]
        if isinstance(field, tuple) and field[0] == PRESET_PLAYER and row["kind"] == "player":
            if row["action"] == field[1]:
                return row["left"] if field[2] == "left" else row["right"]
    return None


def _popup_geometry(
    panel: pygame.Rect, anchor: pygame.Rect, options: list, scroll: int
) -> dict:
    visible = min(LINK_POPUP_ROWS, len(options))
    height = max(1, visible) * LINK_POPUP_ROW + 2
    top = anchor.bottom + 2
    if top + height > panel.bottom - 8:
        top = max(panel.top + 8, anchor.top - 2 - height)
    popup = pygame.Rect(anchor.left, top, anchor.width, height)
    scroll = max(0, min(scroll, max(0, len(options) - visible)))
    rects = []
    for row in range(visible):
        index = scroll + row
        if index >= len(options):
            break
        label, value = options[index]
        rects.append((pygame.Rect(popup.left, popup.top + 1 + row * LINK_POPUP_ROW, popup.width - 2, LINK_POPUP_ROW), label, value))
    return {"popup": popup, "popup_rects": rects, "popup_scroll": scroll}


def draw_animation_link(
    surface: pygame.Surface, editor, font: pygame.font.Font
) -> None:
    link = editor.animation_link
    if link is None:
        return
    geometry = animation_link_geometry(surface, editor)
    panel = geometry["panel"]
    draw_panel(surface, panel)
    title = font.render("动画对象：预设与链接", True, TEXT)
    surface.blit(title, (geometry["title"].left, geometry["title"].top))
    draw_button(surface, font, geometry["preset"], f"预设：{preset_label(link['preset'])}")
    triangle = geometry["preset"].right - 12
    middle = geometry["preset"].centery
    pygame.draw.polygon(
        surface,
        TEXT,
        [(triangle - 4, middle - 2), (triangle + 4, middle - 2), (triangle, middle + 4)],
    )

    for row in geometry["rows"]:
        label = font.render(
            "动画" if row["kind"] == "general" else dict(PLAYER_ACTIONS)[row["action"]],
            True,
            TEXT,
        )
        surface.blit(label, (row["label"].left, row["label"].centery - label.get_height() // 2))
        if row["kind"] == "general":
            value = link["links"].get(PRESET_GENERAL, {})
            key = value.get("clip", "")
            _draw_key_field(surface, font, row["field"], key or "（未选择）", bool(key))
        else:
            pair = link["links"].get(PRESET_PLAYER, {}).get(row["action"], {})
            left_value = pair.get("left", {})
            right_value = pair.get("right", {})
            left_key = str(left_value.get("clip") or "")
            right_key = str(right_value.get("clip") or "")
            _draw_key_field(
                surface, font, row["left"], f"左：{left_key or '（未选择）'}", bool(left_key)
            )
            _draw_key_field(
                surface, font, row["right"], f"右：{right_key or '（未选择）'}", bool(right_key)
            )

    hint_text = (
        "链接一个剪辑；通用预设播一遍就停。"
        if link["preset"] == PRESET_GENERAL
        else "「左」「右」各链接一个剪辑；起跳、落地播一遍，其余动作循环。"
    )
    hint = font.render(hint_text, True, DIM_TEXT)
    surface.blit(
        hint,
        (geometry["hint"].left, geometry["hint"].centery - hint.get_height() // 2),
    )
    draw_button(surface, font, geometry["ok"], "确定")
    draw_button(surface, font, geometry["cancel"], "取消")

    if geometry["popup"] is not None:
        pygame.draw.rect(surface, (36, 36, 42), geometry["popup"])
        pygame.draw.rect(surface, DIALOG_BORDER, geometry["popup"], 1)
        current_preset = link["preset"]
        current_field = (
            animation_link_current(link, link["dropdown"])
            if link["dropdown"] != "preset"
            else current_preset
        )
        for rect, label, value in geometry["popup_rects"]:
            hovered = rect.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(surface, (80, 80, 90) if hovered else (48, 48, 54), rect)
            pygame.draw.rect(surface, (86, 86, 94), rect, 1)
            text = f"● {label}" if value == current_field else label
            rendered = font.render(text, True, HIGHLIGHT if value == current_field else TEXT)
            surface.blit(
                rendered,
                (rect.left + 6, rect.centery - rendered.get_height() // 2),
                (0, 0, max(1, rect.width - 10), rendered.get_height()),
            )


def animation_link_current(link: dict, field) -> str:
    if field == "preset":
        return str(link["preset"])
    if not isinstance(field, tuple):
        return ""
    preset, action, side = field
    if preset == PRESET_GENERAL:
        return str((link["links"].get(PRESET_GENERAL) or {}).get("clip") or "")
    pair = (link["links"].get(PRESET_PLAYER) or {}).get(action)
    pair = pair if isinstance(pair, dict) else {}
    value = pair.get(side)
    if isinstance(value, dict):
        return str(value.get("clip") or "")
    return str(value or "")


def _draw_key_field(
    surface: pygame.Surface,
    font: pygame.font.Font,
    rect: pygame.Rect,
    text: str,
    chosen: bool,
) -> None:
    pygame.draw.rect(surface, (48, 48, 54), rect)
    pygame.draw.rect(surface, (86, 86, 94), rect, 1)
    rendered = font.render(text, True, TEXT if chosen else DIM_TEXT)
    surface.blit(
        rendered,
        (rect.left + 6, rect.centery - rendered.get_height() // 2),
        (0, 0, max(1, rect.width - 24), rendered.get_height()),
    )
    # 右边的小三角，表示可以点开下拉
    middle = rect.centery
    tip = rect.right - 11
    pygame.draw.polygon(
        surface,
        TEXT,
        [(tip - 4, middle - 2), (tip + 4, middle - 2), (tip, middle + 4)],
    )
