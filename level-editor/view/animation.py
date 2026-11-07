"""游戏配置里的「玩家动画」页：五个动作各有一条左右分开的帧动画。

上面一行是动作页签（站立 / 移动 / 上升 / 下落 / 翻转）；下面一行是方向下拉框、
循环开关和「＋ / − / 预览」；再下面是这一侧帧的缩略图格子，每格一张图、下面一个
停留时长（秒）。点缩略图选中一帧，按住拖动换顺序；点时长框直接敲数字，回车落下。
哪一侧空着都不用管：游戏里会用另一侧镜像，预览也照这个样子放（见 core.animation.resolved）。
GIF 加进来时由导入那一步拆成同名文件夹里的一串 PNG（见 editing.anim_import）。
"""

import pygame

from core.animation import (
    DEFAULT_HOLD,
    PLAYER_ANIMATIONS,
    PLAYER_SIDES,
    SIDE_NAMES,
    holds_of,
    resolved,
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
    draw_checkbox,
    draw_panel,
    draw_scrollbar,
    place_panel,
)

ANIMATION_TAB_HEIGHT = 24
ANIMATION_TAB_GAP = 4
ANIMATION_TAB_WIDTH = 72
ANIMATION_ROW_GAP = 6           # 页签与第二行、第二行与格子区之间的空隙
ANIMATION_CONTROLS_HEIGHT = 24
SIDE_BUTTON_WIDTH = 118
LOOP_WIDTH = 76
SMALL_BUTTON_WIDTH = 26
PREVIEW_BUTTON_WIDTH = 62

CELL_WIDTH = 100
CELL_HEIGHT = 100
CELL_GAP = 8
THUMB_HEIGHT = 64
DELAY_HEIGHT = 20
DELAY_WIDTH = 64
SCROLLBAR_WIDTH = 10            # 格子区右边留出来给滚动条

ANIMATION_HEAD_HEIGHT = (
    ANIMATION_TAB_HEIGHT + ANIMATION_ROW_GAP + ANIMATION_CONTROLS_HEIGHT + ANIMATION_ROW_GAP
)
ANIMATION_GRID_ROWS = 3         # 面板默认留三行格子的高度

PREVIEW_PANEL_WIDTH = 420
PREVIEW_PANEL_HEIGHT = 430
PREVIEW_IMAGE_HEIGHT = 250

TOOLTIP_MAX_WIDTH = 340
TOOLTIP_PAD = 6
TOOLTIP_LINE_GAP = 2


def animation_page_height(top_offset: int) -> int:
    grid = ANIMATION_GRID_ROWS * CELL_HEIGHT + (ANIMATION_GRID_ROWS - 1) * CELL_GAP
    foot = CELL_GAP + ROW_HEIGHT + ANIMATION_ROW_GAP + BUTTON_HEIGHT + 12
    return top_offset + ANIMATION_HEAD_HEIGHT + grid + foot


def animation_geometry(
    surface: pygame.Surface, editor, panel: pygame.Rect, top: int
) -> dict:
    """玩家动画页的几何：动作页签、方向与开关、格子区和预览用的那一套。"""
    left = panel.left + MARGIN
    width = panel.width - 2 * MARGIN

    tabs = []
    x = left
    for index, (_, label) in enumerate(PLAYER_ANIMATIONS):
        tabs.append(
            (pygame.Rect(x, top, ANIMATION_TAB_WIDTH, ANIMATION_TAB_HEIGHT), index, label)
        )
        x += ANIMATION_TAB_WIDTH + ANIMATION_TAB_GAP

    controls_top = top + ANIMATION_TAB_HEIGHT + ANIMATION_ROW_GAP
    side = pygame.Rect(left, controls_top, SIDE_BUTTON_WIDTH, ANIMATION_CONTROLS_HEIGHT)
    loop = pygame.Rect(
        side.right + 8, controls_top, LOOP_WIDTH, ANIMATION_CONTROLS_HEIGHT
    )
    preview = pygame.Rect(
        left + width - PREVIEW_BUTTON_WIDTH, controls_top, PREVIEW_BUTTON_WIDTH, ANIMATION_CONTROLS_HEIGHT
    )
    remove = pygame.Rect(
        preview.left - 6 - SMALL_BUTTON_WIDTH,
        controls_top + 1,
        SMALL_BUTTON_WIDTH,
        ANIMATION_CONTROLS_HEIGHT - 2,
    )
    add = pygame.Rect(
        remove.left - 4 - SMALL_BUTTON_WIDTH,
        controls_top + 1,
        SMALL_BUTTON_WIDTH,
        ANIMATION_CONTROLS_HEIGHT - 2,
    )

    grid_top = top + ANIMATION_HEAD_HEIGHT
    hint_top = panel.bottom - 12 - BUTTON_HEIGHT - 6 - ROW_HEIGHT
    grid = pygame.Rect(left, grid_top, width - SCROLLBAR_WIDTH, max(24, hint_top - 8 - grid_top))
    hint = pygame.Rect(left, hint_top, width, ROW_HEIGHT)

    clip = editor.animation_clip()
    frames = clip["frames"]
    holds = holds_of(clip)

    columns = max(1, (grid.width + CELL_GAP) // (CELL_WIDTH + CELL_GAP))
    rows = (len(frames) + columns - 1) // columns if frames else 0
    content_height = max(0, rows * (CELL_HEIGHT + CELL_GAP) - CELL_GAP)
    scroll = max(0.0, min(float(editor.animation_scroll), max(0.0, content_height - grid.height)))
    editor.animation_scroll = scroll

    cells = []
    delays = []
    for index, frame in enumerate(frames):
        column = index % columns
        row = index // columns
        thumb = pygame.Rect(
            grid.left + column * (CELL_WIDTH + CELL_GAP),
            grid.top + row * (CELL_HEIGHT + CELL_GAP) - round(scroll),
            CELL_WIDTH,
            THUMB_HEIGHT,
        )
        if thumb.bottom < grid.top or thumb.top > grid.bottom:
            continue
        delay = pygame.Rect(
            thumb.centerx - DELAY_WIDTH // 2,
            thumb.bottom + 4,
            DELAY_WIDTH,
            DELAY_HEIGHT,
        )
        cells.append({"index": index, "frame": frame, "rect": thumb, "delay": delay,
                      "hold": holds[index]})
        delays.append({"index": index, "rect": delay})

    side_menu = [
        (
            pygame.Rect(
                side.left,
                side.bottom + 2 + index * ANIMATION_CONTROLS_HEIGHT,
                side.width,
                ANIMATION_CONTROLS_HEIGHT,
            ),
            name,
            label,
        )
        for index, (name, label) in enumerate(PLAYER_SIDES)
    ]

    return {
        "tabs": tabs,
        "side": side,
        "side_menu": side_menu,
        "side_menu_open": bool(editor.animation_side_menu_open),
        "loop": loop,
        "add": add,
        "remove": remove,
        "preview": preview,
        "grid": grid,
        "grid_columns": columns,
        "cell_width": CELL_WIDTH,
        "cell_height": CELL_HEIGHT,
        "cell_gap": CELL_GAP,
        "content_height": content_height,
        "scroll": scroll,
        "hint": hint,
        "cells": cells,
        "delays": delays,
        "count": len(frames),
    }


def _wrap_path(font: pygame.font.Font, text: str, width: int) -> list:
    """路径优先按 / 折行，单段还是太长再按字符切。"""
    lines = []
    line = ""
    for part in str(text).split("/"):
        piece = part if not line else "/" + part
        if line and font.size(line + piece)[0] > width:
            lines.append(line)
            line = part
        else:
            line += piece
    lines.append(line)
    chunks = []
    for line in lines:
        chunk = ""
        for character in line:
            if chunk and font.size(chunk + character)[0] > width:
                chunks.append(chunk)
                chunk = character
            else:
                chunk += character
        chunks.append(chunk)
    return chunks


def draw_tooltip(
    surface: pygame.Surface, font: pygame.font.Font, text: str, mouse: tuple
) -> None:
    """在鼠标旁边画一小块说明；靠右边或下边时自动往里挪。"""
    lines = _wrap_path(font, text, TOOLTIP_MAX_WIDTH)
    rendered = [font.render(line, True, TEXT) for line in lines]
    width = max(image.get_width() for image in rendered) + TOOLTIP_PAD * 2
    height = (
        sum(image.get_height() + TOOLTIP_LINE_GAP for image in rendered)
        - TOOLTIP_LINE_GAP
        + TOOLTIP_PAD * 2
    )
    left = mouse[0] + 14
    top = mouse[1] + 16
    if left + width > surface.get_width() - 4:
        left = surface.get_width() - 4 - width
    if top + height > surface.get_height() - 4:
        top = mouse[1] - 6 - height
    rect = pygame.Rect(left, top, width, height)
    pygame.draw.rect(surface, (36, 36, 42), rect)
    pygame.draw.rect(surface, DIALOG_BORDER, rect, 1)
    y = top + TOOLTIP_PAD
    for image in rendered:
        surface.blit(image, (left + TOOLTIP_PAD, y))
        y += image.get_height() + TOOLTIP_LINE_GAP


def _draw_thumbnail(
    surface: pygame.Surface,
    rect: pygame.Rect,
    frame: str,
    base_dir: str | None,
    selected: bool,
    number: int,
    font: pygame.font.Font,
) -> None:
    """画一帧的缩略图：等比缩进格子、居中；图片找不到时铺黑紫棋盘格，选中的描亮边。"""
    pygame.draw.rect(surface, (40, 40, 46), rect)
    path = resolve_level_path(frame, base_dir)
    size = image_size(path) if path is not None else None
    image = None
    if size is not None:
        image = load_scaled(path, _fit_within(size, rect.size), False)
    if image is None:
        draw_missing_texture(surface, rect)
    else:
        surface.blit(image, image.get_rect(center=rect.center))
    pygame.draw.rect(surface, HIGHLIGHT if selected else (86, 86, 94), rect, 2 if selected else 1)
    tag = font.render(str(number), True, TEXT)
    backing = pygame.Rect(rect.left + 1, rect.top + 1, tag.get_width() + 6, tag.get_height() + 2)
    surface.blit(_shade(backing), backing.topleft)
    surface.blit(tag, (backing.left + 3, backing.top + 1))


def _shade(rect: pygame.Rect) -> pygame.Surface:
    surface = pygame.Surface(rect.size, pygame.SRCALPHA)
    surface.fill((0, 0, 0, 150))
    return surface


def _draw_delay(
    surface: pygame.Surface,
    font: pygame.font.Font,
    cell: dict,
    editing: dict | None,
) -> None:
    """缩略图下面的停留时长：正在输入时显示原文，否则显示夹好的秒数。"""
    rect = cell["delay"]
    active = editing is not None and editing["index"] == cell["index"]
    pygame.draw.rect(surface, (62, 62, 72) if active else (48, 48, 54), rect)
    pygame.draw.rect(surface, HIGHLIGHT if active else (86, 86, 94), rect, 1)
    text = editing["text"] if active else f"{cell['hold']:g}s"
    rendered = font.render(text, True, TEXT if active else DIM_TEXT)
    clip = max(1, rect.width - 10)
    surface.blit(
        rendered,
        (rect.left + 5, rect.centery - rendered.get_height() // 2),
        (0, 0, min(rendered.get_width(), clip), rendered.get_height()),
    )


def _draw_empty_hint(
    surface: pygame.Surface, font: pygame.font.Font, grid: pygame.Rect, editor, side: str
) -> None:
    """这一侧没有帧时，说清楚游戏里会用另一侧镜像。"""
    other = "left" if side == "right" else "right"
    lines = ["这一侧还没有帧：点「＋」选一张图。"]
    if editor.animation_frames_of(other):
        lines.append(f"空着不要紧：游戏里会用{SIDE_NAMES[other]}的帧镜像播放，预览也是。")
    else:
        lines.append("两侧都空着时，会退到站立；站立也没有就不画玩家贴图。")
    y = grid.centery - len(lines) * 11
    for line in lines:
        rendered = font.render(line, True, DIM_TEXT)
        surface.blit(rendered, (grid.centerx - rendered.get_width() // 2, y))
        y += 22


def draw_animation_page(
    surface: pygame.Surface,
    editor,
    font: pygame.font.Font,
    geometry: dict,
    mouse: tuple | None = None,
) -> None:
    position = mouse if mouse is not None else pygame.mouse.get_pos()
    current = editor.animation_state

    for rect, index, label in geometry["tabs"]:
        selected = index == current
        pygame.draw.rect(surface, (80, 80, 90) if selected else (48, 48, 54), rect)
        pygame.draw.rect(surface, HIGHLIGHT if selected else (86, 86, 94), rect, 1)
        rendered = font.render(label, True, HIGHLIGHT if selected else TEXT)
        surface.blit(
            rendered,
            (rect.centerx - rendered.get_width() // 2, rect.centery - rendered.get_height() // 2),
        )

    side = editor.animation_side
    side_label = dict(PLAYER_SIDES)[side]
    draw_button(surface, font, geometry["side"], f"方向：{side_label}")
    # 下拉框右边的三角（不靠字体里有没有这个符号）
    middle = geometry["side"].centery
    tip = geometry["side"].right - 11
    pygame.draw.polygon(
        surface,
        TEXT,
        [(tip - 4, middle - 2), (tip + 4, middle - 2), (tip, middle + 4)],
    )
    clip = editor.animation_clip()
    draw_checkbox(surface, font, geometry["loop"], "循环", bool(clip["loop"]), inset=4)
    draw_button(surface, font, geometry["add"], "＋")
    draw_button(surface, font, geometry["remove"], "−")
    draw_button(surface, font, geometry["preview"], "预览")

    grid = geometry["grid"]
    pygame.draw.rect(surface, (44, 44, 50), grid)
    pygame.draw.rect(surface, (70, 70, 78), grid, 1)

    if not geometry["cells"]:
        _draw_empty_hint(surface, font, grid, editor, side)
    else:
        previous = surface.get_clip()
        surface.set_clip(previous.clip(grid))
        for cell in geometry["cells"]:
            selected = cell["index"] == editor.animation_frame
            _draw_thumbnail(
                surface,
                cell["rect"],
                cell["frame"],
                editor.media_base_dir,
                selected,
                cell["index"] + 1,
                font,
            )
            _draw_delay(surface, font, cell, editor.animation_delay_edit)
        surface.set_clip(previous)

    draw_scrollbar(surface, grid, geometry["content_height"], geometry["scroll"])

    if geometry["count"]:
        total = font.render(f"共 {geometry['count']} 帧", True, DIM_TEXT)
        surface.blit(
            total, (geometry["hint"].right - total.get_width(), geometry["hint"].centery - 8)
        )
    hint = font.render("点缩略图选中，拖动换顺序；点秒数可以改；Delete 删除选中帧", True, DIM_TEXT)
    surface.blit(hint, (geometry["hint"].left, geometry["hint"].centery - hint.get_height() // 2))

    # 正在拖一帧：在它要落下去的位置画一条竖线
    drag = editor.animation_drag
    if drag is not None and drag["moved"]:
        x, top = _drag_marker(geometry, drag["slot"])
        bottom = min(geometry["grid"].bottom - 2, top + THUMB_HEIGHT)
        pygame.draw.line(surface, HIGHLIGHT, (x, top), (x, bottom), 3)

    # 方向下拉菜单画在格子上层
    if geometry["side_menu_open"]:
        for rect, name, label in geometry["side_menu"]:
            selected = name == side
            pygame.draw.rect(surface, (80, 80, 90) if selected else (48, 48, 54), rect)
            pygame.draw.rect(surface, HIGHLIGHT if selected else (86, 86, 94), rect, 1)
            if selected:                # 当前这一侧：画一个小三角当记号
                middle = rect.centery
                pygame.draw.polygon(
                    surface,
                    HIGHLIGHT,
                    [
                        (rect.left + 7, middle - 3),
                        (rect.left + 13, middle - 3),
                        (rect.left + 10, middle + 3),
                    ],
                )
            rendered = font.render(label, True, HIGHLIGHT if selected else TEXT)
            surface.blit(
                rendered,
                (rect.left + (20 if selected else 10), rect.centery - rendered.get_height() // 2),
            )

    # 鼠标停在缩略图上：浮出这一帧的图片路径
    if (
        editor.animation_preview is not None
        or drag is not None
        or editor.animation_delay_edit is not None
        or geometry["side_menu_open"]
    ):
        return
    for cell in geometry["cells"]:
        if cell["rect"].collidepoint(position):
            draw_tooltip(surface, font, cell["frame"], position)
            return


def _drag_marker(geometry: dict, slot: int) -> tuple:
    """插入线的位置：按格子排法算出插槽所在的列和行，落在格子左边。"""
    grid = geometry["grid"]
    columns = geometry["grid_columns"]
    row = slot // columns
    column = slot % columns
    x = grid.left + column * (CELL_WIDTH + CELL_GAP) - CELL_GAP // 2
    x = max(grid.left + 2, min(x, grid.right - 2))
    top = grid.top + row * (CELL_HEIGHT + CELL_GAP) - round(geometry["scroll"]) + 2
    top = max(grid.top + 2, min(top, grid.bottom - THUMB_HEIGHT - 2))
    return x, top


def animation_preview_geometry(surface: pygame.Surface) -> dict:
    """预览浮层：标题、图、第几帧 / 时长 / 循环、提示和「关闭」。"""
    panel = place_panel(
        surface, pygame.Rect(0, 0, PREVIEW_PANEL_WIDTH, PREVIEW_PANEL_HEIGHT)
    )
    title = pygame.Rect(panel.left + 14, panel.top + 10, panel.width - 28, ROW_HEIGHT)
    note = pygame.Rect(panel.left + 14, title.bottom + 2, panel.width - 28, ROW_HEIGHT)
    image = pygame.Rect(
        panel.left + 14, note.bottom + 6, panel.width - 28, PREVIEW_IMAGE_HEIGHT
    )
    info = pygame.Rect(panel.left + 14, image.bottom + 6, panel.width - 28, ROW_HEIGHT)
    hint = pygame.Rect(panel.left + 14, info.bottom + 2, panel.width - 28, ROW_HEIGHT)
    close = pygame.Rect(panel.centerx - 40, panel.bottom - 12 - BUTTON_HEIGHT, 80, BUTTON_HEIGHT)
    return {
        "panel": panel,
        "title": title,
        "note": note,
        "image": image,
        "info": info,
        "hint": hint,
        "close": close,
    }


def _fit_within(size: tuple, box: tuple) -> tuple:
    """等比缩放到 box 里，宽高都不超过它。"""
    width, height = size
    if width <= 0 or height <= 0:
        return max(1, box[0]), max(1, box[1])
    scale = min(box[0] / width, box[1] / height)
    return max(1, round(width * scale)), max(1, round(height * scale))


def _draw_preview_image(
    surface: pygame.Surface,
    font: pygame.font.Font,
    box: pygame.Rect,
    path: str | None,
    mirror: bool,
) -> None:
    pygame.draw.rect(surface, (40, 40, 46), box)
    size = image_size(path) if path is not None else None
    image = None
    if size is not None:
        image = load_scaled(path, _fit_within(size, box.size), True)
    if image is None:
        draw_missing_texture(surface, box)
        text = font.render("找不到这张图", True, DIM_TEXT)
        surface.blit(
            text, (box.centerx - text.get_width() // 2, box.bottom - text.get_height() - 6)
        )
        return
    if mirror:
        image = pygame.transform.flip(image, True, False)
    surface.blit(image, image.get_rect(center=box.center))


def draw_animation_preview(
    surface: pygame.Surface, editor, font: pygame.font.Font
) -> None:
    """预览浮层：按每帧的停留时长播放；本侧空着时和游戏里一样镜像另一侧。"""
    geometry = animation_preview_geometry(surface)
    panel = geometry["panel"]
    draw_panel(surface, panel)
    preview = editor.animation_preview
    if preview is None:
        return
    action = preview["action"]
    side = preview["side"]
    label = dict(PLAYER_ANIMATIONS).get(action, action)
    side_label = dict(PLAYER_SIDES)[side]
    title = font.render(f"播放预览：{label}（{side_label}）", True, HIGHLIGHT)
    surface.blit(title, (geometry["title"].left, geometry["title"].centery - title.get_height() // 2))

    frames, holds, loop, mirrored = resolved(editor.game_animations, action, side)
    if not frames:
        empty = font.render("两侧都还没有帧", True, DIM_TEXT)
        surface.blit(empty, (geometry["image"].centerx - empty.get_width() // 2, geometry["image"].centery))
        return
    if mirrored is not None:
        note = font.render(
            f"镜像自{SIDE_NAMES[mirrored]}：本侧空着，游戏里也这样放", True, DIM_TEXT
        )
        surface.blit(note, (geometry["note"].left, geometry["note"].centery - note.get_height() // 2))

    frame = max(0, min(preview["frame"], len(frames) - 1))
    path = resolve_level_path(frames[frame], editor.media_base_dir)
    _draw_preview_image(surface, font, geometry["image"], path, mirrored is not None)

    hold = holds[frame] if frame < len(holds) else DEFAULT_HOLD
    loop_text = "循环" if loop else "播完停在最后一帧"
    info = font.render(
        f"第 {frame + 1}/{len(frames)} 帧 · 停留 {hold:g} 秒 · {loop_text}", True, TEXT
    )
    surface.blit(info, (geometry["info"].left, geometry["info"].centery - info.get_height() // 2))
    hint = font.render("Esc 或点面板外关闭", True, DIM_TEXT)
    surface.blit(hint, (geometry["hint"].left, geometry["hint"].centery - hint.get_height() // 2))
    draw_button(surface, font, geometry["close"], "关闭")
