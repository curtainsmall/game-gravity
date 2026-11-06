"""游戏配置里的「玩家动画」页：五个固定的玩家状态，每个状态一段帧动画。

每行两栏：上面是状态名、fps、循环开关和「预览」，下面是帧的缩略图条和「添加帧 / 删除帧」。
点缩略图选中一帧，按住缩略图拖动可以直接换顺序（拖动时缩略图之间画一条插入线）；
按钮都作用在选中的那一帧上；鼠标停在缩略图上会浮出这一帧的图片路径。
「预览」弹出一个小窗，按 fps 播放这段动画。
"""

import pygame

from core.animation import (
    DEFAULT_FPS,
    FPS_MAX,
    FPS_MIN,
    PLAYER_ANIMATIONS,
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
from core.helpers import clamp_float, resolve_level_path
from view.texture import draw_missing_texture, image_size, load_scaled
from view.widgets import (
    draw_button,
    draw_checkbox,
    draw_panel,
    draw_stepper,
    place_panel,
    stepper_rects,
)

ROW_SPACE = 88                 # 一行占的高度（含间距）
ANIMATION_ROW_HEIGHT = 82
ANIMATION_ROW_GAP = 6
ANIMATION_THUMB_WIDTH = 34
ANIMATION_THUMB_HEIGHT = 42
ANIMATION_THUMB_GAP = 4
ANIMATION_LABEL_WIDTH = 96
ANIMATION_FPS_WIDTH = 110
ANIMATION_ADD_WIDTH = 62
ANIMATION_DELETE_WIDTH = 62
ANIMATION_PREVIEW_WIDTH = 62
ANIMATION_BOTTOM = 46          # 最后一行下面留出应用/取消的位置

PREVIEW_PANEL_WIDTH = 380
PREVIEW_PANEL_HEIGHT = 400
PREVIEW_IMAGE_HEIGHT = 250

TOOLTIP_MAX_WIDTH = 340        # 图片路径长的时候按这个宽度折行
TOOLTIP_PAD = 6
TOOLTIP_LINE_GAP = 2


def animation_page_height(top_offset: int) -> int:
    count = len(PLAYER_ANIMATIONS)
    return top_offset + count * ROW_SPACE - ANIMATION_ROW_GAP + ANIMATION_BOTTOM


def animation_geometry(
    surface: pygame.Surface, editor, panel: pygame.Rect, top: int
) -> dict:
    """玩家动画页的几何：每个状态一行，行里面有 fps 格、循环格、预览格、缩略图条和几个按钮。"""
    rows = []
    for index, (name, _) in enumerate(PLAYER_ANIMATIONS):
        rect = pygame.Rect(
            panel.left + MARGIN,
            top + index * ROW_SPACE,
            panel.width - 2 * MARGIN,
            ANIMATION_ROW_HEIGHT,
        )
        line = pygame.Rect(rect.left + 8, rect.top + 6, rect.width - 16, ROW_HEIGHT)
        label = pygame.Rect(line.left, line.top, ANIMATION_LABEL_WIDTH, ROW_HEIGHT)
        fps = pygame.Rect(label.right + 10, line.top, ANIMATION_FPS_WIDTH, ROW_HEIGHT)
        loop = pygame.Rect(fps.right + 14, line.top, 120, ROW_HEIGHT)
        preview = pygame.Rect(
            loop.right + 16, line.top, ANIMATION_PREVIEW_WIDTH, ROW_HEIGHT
        )

        remove = pygame.Rect(
            rect.right - 8 - ANIMATION_DELETE_WIDTH,
            rect.top + 42,
            ANIMATION_DELETE_WIDTH,
            ROW_HEIGHT,
        )
        add = pygame.Rect(
            remove.left - 6 - ANIMATION_ADD_WIDTH,
            rect.top + 42,
            ANIMATION_ADD_WIDTH,
            ROW_HEIGHT,
        )
        strip = pygame.Rect(
            rect.left + 8,
            rect.top + 32,
            add.left - 8 - (rect.left + 8),
            ANIMATION_THUMB_HEIGHT,
        )

        frames = editor.animation_clip(index)["frames"]
        thumb_gap = ANIMATION_THUMB_GAP
        width = ANIMATION_THUMB_WIDTH
        if frames and len(frames) * width + (len(frames) - 1) * thumb_gap > strip.width:
            width = max(16, (strip.width - (len(frames) - 1) * thumb_gap) // len(frames))
        step = width + thumb_gap
        visible = max(0, (strip.width + thumb_gap) // step) if frames else 0
        thumbs = [
            {
                "index": frame_index,
                "rect": pygame.Rect(
                    strip.left + frame_index * step, strip.top, width, ANIMATION_THUMB_HEIGHT
                ),
            }
            for frame_index in range(min(len(frames), visible))
        ]
        rows.append(
            {
                "index": index,
                "name": name,
                "rect": rect,
                "label": label,
                "fps": fps,
                "loop": loop,
                "preview": preview,
                "strip": strip,
                "thumbs": thumbs,
                "add": add,
                "remove": remove,
                "count": len(frames),
            }
        )
    return {"rows": rows}


def _draw_cell(
    surface: pygame.Surface,
    font: pygame.font.Font,
    rect: pygame.Rect,
    text: str,
    selected: bool,
) -> None:
    pygame.draw.rect(surface, (62, 62, 72) if selected else (48, 48, 54), rect)
    pygame.draw.rect(surface, HIGHLIGHT if selected else (86, 86, 94), rect, 1)
    rendered = font.render(text, True, HIGHLIGHT if selected else TEXT)
    clip = max(1, rect.width - 12)
    surface.blit(
        rendered,
        (rect.left + 6, rect.centery - rendered.get_height() // 2),
        (0, 0, min(rendered.get_width(), clip), rendered.get_height()),
    )


def _draw_thumbnail(
    surface: pygame.Surface,
    font: pygame.font.Font,
    rect: pygame.Rect,
    frame: str,
    base_dir: str | None,
    selected: bool,
) -> None:
    """画一帧的缩略图；图片找不到时铺黑紫棋盘格，选中的描亮边。"""
    pygame.draw.rect(surface, (40, 40, 46), rect)
    path = resolve_level_path(frame, base_dir)
    image = load_scaled(path, rect.size, False) if path is not None else None
    if image is None:
        draw_missing_texture(surface, rect)
    else:
        surface.blit(image, rect.topleft)
    pygame.draw.rect(surface, HIGHLIGHT if selected else (86, 86, 94), rect, 2 if selected else 1)


def _cut_line(font: pygame.font.Font, line: str, width: int) -> list:
    """一行实在放不下时按字符切开。"""
    chunks = []
    chunk = ""
    for character in line:
        if chunk and font.size(chunk + character)[0] > width:
            chunks.append(chunk)
            chunk = character
        else:
            chunk += character
    chunks.append(chunk)
    return chunks


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
    return [chunk for line in lines for chunk in _cut_line(font, line, width)]


def draw_tooltip(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    mouse: tuple,
) -> None:
    """在鼠标旁边画一小块说明；靠右边或下边时自动往里挪。"""
    lines = _wrap_path(font, text, TOOLTIP_MAX_WIDTH)
    rendered = [font.render(line, True, TEXT) for line in lines]
    width = max(image.get_width() for image in rendered) + TOOLTIP_PAD * 2
    height = sum(
        image.get_height() + TOOLTIP_LINE_GAP for image in rendered
    ) - TOOLTIP_LINE_GAP + TOOLTIP_PAD * 2
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


def _drag_marker_x(row: dict, slot: int) -> int:
    """插入线的横坐标：落在某个缩略图左边，或者最后一帧的右边。"""
    thumbs = row["thumbs"]
    if not thumbs:
        return row["strip"].left
    if slot < len(thumbs):
        return thumbs[slot]["rect"].left - 2
    return min(thumbs[-1]["rect"].right + 2, row["strip"].right)


def draw_animation_page(
    surface: pygame.Surface,
    editor,
    font: pygame.font.Font,
    geometry: dict,
    mouse: tuple | None = None,
) -> None:
    for row in geometry["rows"]:
        clip = editor.animation_clip(row["index"])
        current = editor.animation_state == row["index"]
        pygame.draw.rect(surface, (58, 58, 66) if current else (52, 52, 58), row["rect"])
        pygame.draw.rect(surface, HIGHLIGHT if current else (86, 86, 94), row["rect"], 1)

        label = font.render(PLAYER_ANIMATIONS[row["index"]][1], True, HIGHLIGHT if current else TEXT)
        surface.blit(label, (row["label"].left, row["label"].centery - label.get_height() // 2))
        key = font.render(row["name"], True, DIM_TEXT)
        surface.blit(key, (row["label"].right - key.get_width() - 6, row["label"].centery - key.get_height() // 2))

        _draw_cell(surface, font, row["fps"], f"fps：{clip['fps']}", current)
        left, right = stepper_rects(row["fps"])
        draw_stepper(surface, left, -1)
        draw_stepper(surface, right, 1)
        draw_checkbox(surface, font, row["loop"], "循环", bool(clip["loop"]), current, inset=6)
        draw_button(surface, font, row["preview"], "预览")

        count = font.render(f"共 {row['count']} 帧", True, DIM_TEXT)
        surface.blit(
            count,
            (row["rect"].right - 8 - count.get_width(), row["rect"].top + 10),
        )

        if not clip["frames"]:
            hint = font.render("还没有帧：点「添加帧」", True, DIM_TEXT)
            surface.blit(hint, (row["strip"].left + 2, row["strip"].centery - hint.get_height() // 2))
        for thumb in row["thumbs"]:
            selected = current and editor.animation_frame == thumb["index"]
            _draw_thumbnail(
                surface,
                font,
                thumb["rect"],
                clip["frames"][thumb["index"]],
                editor.media_base_dir,
                selected,
            )
        if row["thumbs"] and len(row["thumbs"]) < row["count"]:
            more = font.render("…", True, DIM_TEXT)
            last = row["thumbs"][-1]["rect"]
            surface.blit(more, (min(last.right + 4, row["strip"].right - 10), last.top + 2))

        draw_button(surface, font, row["add"], "添加帧")
        draw_button(surface, font, row["remove"], "删除帧")

    # 正在拖一帧：在它要落下去的位置画一条竖线
    drag = editor.animation_drag
    if drag is not None and drag["moved"]:
        row = geometry["rows"][drag["index"]]
        x = _drag_marker_x(row, drag["slot"])
        pygame.draw.line(
            surface, HIGHLIGHT, (x, row["strip"].top - 3), (x, row["strip"].bottom + 3), 3
        )

    # 鼠标停在缩略图上：浮出这一帧的图片路径
    if editor.animation_preview is not None or drag is not None:
        return
    position = mouse if mouse is not None else pygame.mouse.get_pos()
    for row in geometry["rows"]:
        frames = editor.animation_clip(row["index"])["frames"]
        for thumb in row["thumbs"]:
            if thumb["rect"].collidepoint(position):
                draw_tooltip(surface, font, frames[thumb["index"]], position)
                return


def animation_preview_geometry(surface: pygame.Surface) -> dict:
    """预览浮层：标题、图、帧数与 fps、提示和「关闭」。"""
    panel = place_panel(
        surface, pygame.Rect(0, 0, PREVIEW_PANEL_WIDTH, PREVIEW_PANEL_HEIGHT)
    )
    title = pygame.Rect(panel.left + 14, panel.top + 10, panel.width - 28, ROW_HEIGHT)
    image = pygame.Rect(
        panel.left + 14, title.bottom + 6, panel.width - 28, PREVIEW_IMAGE_HEIGHT
    )
    info = pygame.Rect(panel.left + 14, image.bottom + 6, panel.width - 28, ROW_HEIGHT)
    hint = pygame.Rect(panel.left + 14, info.bottom + 2, panel.width - 28, ROW_HEIGHT)
    close = pygame.Rect(panel.centerx - 40, panel.bottom - 12 - BUTTON_HEIGHT, 80, BUTTON_HEIGHT)
    return {
        "panel": panel,
        "title": title,
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
    surface: pygame.Surface, font: pygame.font.Font, box: pygame.Rect, path: str | None
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
    surface.blit(image, image.get_rect(center=box.center))


def draw_animation_preview(
    surface: pygame.Surface, editor, font: pygame.font.Font
) -> None:
    """预览浮层：当前帧的图、第几帧、fps 和循环，底下是「关闭」。"""
    geometry = animation_preview_geometry(surface)
    panel = geometry["panel"]
    draw_panel(surface, panel)
    preview = editor.animation_preview
    if preview is None:
        return
    index = max(0, min(preview["index"], len(PLAYER_ANIMATIONS) - 1))
    label, key = PLAYER_ANIMATIONS[index][1], PLAYER_ANIMATIONS[index][0]
    clip = editor.animation_clip(index)
    frames = clip["frames"]
    title = font.render(f"播放预览：{label}（{key}）", True, HIGHLIGHT)
    surface.blit(title, (geometry["title"].left, geometry["title"].centery - title.get_height() // 2))
    if not frames:
        return

    frame = max(0, min(preview["frame"], len(frames) - 1))
    path = resolve_level_path(frames[frame], editor.media_base_dir)
    _draw_preview_image(surface, font, geometry["image"], path)

    fps = clamp_float(clip["fps"], FPS_MIN, FPS_MAX, DEFAULT_FPS)
    loop = "循环" if clip["loop"] else "播完停在最后一帧"
    info = font.render(f"第 {frame + 1}/{len(frames)} 帧 · {fps:g} fps · {loop}", True, TEXT)
    surface.blit(info, (geometry["info"].left, geometry["info"].centery - info.get_height() // 2))
    hint = font.render("Esc 或点面板外关闭", True, DIM_TEXT)
    surface.blit(hint, (geometry["hint"].left, geometry["hint"].centery - hint.get_height() // 2))
    draw_button(surface, font, geometry["close"], "关闭")
