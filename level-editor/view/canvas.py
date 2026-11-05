"""画布：关卡本体、支点/喷口标注和底部刻度。"""

import math
from typing import TYPE_CHECKING

import pygame

from core.constants import (
    BLOCK_COLOR,
    BUTTON_COLOR,
    DESTINATION_COLOR,
    DIALOG_BORDER,
    DIM_TEXT,
    FACE_ROTATIONS,
    GRID,
    GROUND_COLOR,
    HANDLE_COLOR,
    HIGHLIGHT,
    ITEM_COLOR,
    KIND_NOZZLE,
    KIND_TEXTURE,
    MOVABLE_COLOR,
    NOZZLE_COLOR,
    NOZZLE_DEFAULT_POWER,
    PANEL,
    PIVOT_COLOR,
    PLANK_COLOR,
    PLAYER_COLOR,
    PREVIEW,
    RANGE_COLOR,
    RULER_STEP,
    TOOL_COLORS,
)
from core.helpers import nozzle_box, normalize_drag, readable_color
from core.level import player_position
from view.background import draw_background
from view.layout import Layout
from view.texture import draw_textures, texture_rect

if TYPE_CHECKING:
    from editing.editor import Editor


def draw_cell_marker(surface: pygame.Surface, rect: pygame.Rect, color: tuple) -> None:
    """起点/终点用的标记：2px 方框 + 中心一个小方点。"""
    pygame.draw.rect(surface, color, rect, 2)
    center = rect.center
    pygame.draw.rect(surface, color, pygame.Rect(center[0] - 2, center[1] - 2, 4, 4))


def frustum_points(rect: pygame.Rect, face: str) -> list:
    """按钮的棱台：窄端指向 face（up/right/down/left），和游戏里的画法一致。"""
    inset = max(1.0, rect.width * 0.2)
    base = [
        (rect.left, rect.bottom),
        (rect.right, rect.bottom),
        (rect.right - inset, rect.top),
        (rect.left + inset, rect.top),
    ]
    angle = math.radians(FACE_ROTATIONS.get(str(face), 0))
    if not angle:
        return base
    center_x, center_y = rect.center
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    return [
        (center_x + dx * cos_a - dy * sin_a, center_y + dx * sin_a + dy * cos_a)
        for dx, dy in ((x - center_x, y - center_y) for x, y in base)
    ]


def draw_canvas(surface: pygame.Surface, editor: Editor, layout: Layout) -> None:
    level = editor.level
    tile = layout.tile
    pygame.draw.rect(surface, PANEL, (layout.left, layout.top, layout.width, layout.height))
    if editor.view_settings.get("background", True):
        draw_background(surface, layout, level.background, editor.path)

    for row in range(layout.rows + 2):
        top = layout.top + row * tile
        if row in (0, layout.rows + 1):
            pygame.draw.rect(surface, GROUND_COLOR, (layout.left, top, layout.width, tile))

    for entry in level.blocks:
        pygame.draw.rect(surface, BLOCK_COLOR, layout.entry_rect(entry))
    for entry in level.planks:
        pygame.draw.rect(surface, PLANK_COLOR, layout.entry_rect(entry))
    for entry in level.movable_blocks:
        pygame.draw.rect(surface, MOVABLE_COLOR, layout.entry_rect(entry))

    # 贴图压在所有方块之上（方块、木板、可移动方块），网格线再盖在贴图上当辅助线
    draw_textures(surface, layout, level, editor.path)

    for col in range(layout.cols + 1):
        x = layout.left + col * tile
        if -tile <= x <= layout.window[0] + tile:
            pygame.draw.line(surface, GRID, (x, layout.top), (x, layout.top + layout.height))
    for row in range(layout.rows + 3):
        y = layout.top + row * tile
        pygame.draw.line(surface, GRID, (layout.left, y), (layout.left + layout.width, y))

    for entry in level.buttons:
        pygame.draw.polygon(surface, BUTTON_COLOR, frustum_points(layout.entry_rect(entry), entry.get("face", "")))

    for entry in level.items:
        rect = layout.entry_rect(entry)
        center = rect.center
        radius = rect.width / 2.0
        pygame.draw.polygon(
            surface,
            ITEM_COLOR,
            [
                (
                    center[0] + radius * math.cos(math.radians(-90 + 72 * i)),
                    center[1] + radius * math.sin(math.radians(-90 + 72 * i)),
                )
                for i in range(5)
            ],
        )

    for entry in level.nozzles:
        # pos 是底边中点：三角形底边中点就画在这个点上，底边落在 y 这道平面上。
        center_x = layout.left + entry["pos"][0] * tile
        base_y = layout.top + (layout.rows + 1 - entry["pos"][1]) * tile
        up = int(entry.get("power", NOZZLE_DEFAULT_POWER)) >= 0
        apex_y = base_y - tile if up else base_y + tile
        draw_nozzle_range(surface, layout, entry)
        pygame.draw.polygon(
            surface,
            NOZZLE_COLOR,
            [(center_x - tile / 2, base_y), (center_x + tile / 2, base_y), (center_x, apex_y)],
        )
        draw_nozzle_power(surface, layout, entry)

    # 起点和终点都画成同一款标记：2px 方框 + 中心小方点
    start = player_position(level)
    if start is not None:
        draw_cell_marker(surface, layout.cell_rect(start[0], start[1], (1, 1)), PLAYER_COLOR)
    if level.destination:
        draw_cell_marker(surface, layout.entry_rect(level.destination), DESTINATION_COLOR)

    # 可移动方块：支点、目标点，以及两点之间的红色虚线（直线，不拐弯）
    for entry in level.movable_blocks:
        draw_pivot_guide(surface, layout, entry)

    # 拖动预览
    if editor.drag_start is not None and editor.drag_current is not None:
        x, y, w, h = normalize_drag(editor.drag_start, editor.drag_current)
        preview = pygame.Surface((max(1, round(w * tile)), max(1, round(h * tile))), pygame.SRCALPHA)
        preview.fill(PREVIEW)
        surface.blit(preview, layout.cell_rect(x, y, (w, h)).topleft)

    if editor.picking_offset:
        # 选目标位置时：光标所在格的中心画一个红点，和支点/目标点同一个红
        if editor.hover is not None:
            center = layout.cell_rect(editor.hover[0], editor.hover[1], (1, 1)).center
            pygame.draw.circle(surface, PIVOT_COLOR, center, 4)
    elif editor.creating:
        # 新建状态：光标所在格用「要放的那种对象」的颜色描边；拖动时改画整个预览范围
        color = readable_color(TOOL_COLORS.get(editor.tool, HIGHLIGHT))
        if editor.hover is not None:
            left, bottom = editor.hover
            pygame.draw.rect(surface, color, layout.cell_rect(left, bottom, (1, 1)), 2)
        if editor.drag_start is not None and editor.drag_current is not None:
            x, y, w, h = normalize_drag(editor.drag_start, editor.drag_current)
            pygame.draw.rect(surface, color, layout.cell_rect(x, y, (w, h)), 2)
    elif not editor.startup:
        # 选中的对象一直亮着，直到选了别的或者点空地取消；正在拖的贴图也算选中
        active = None
        if editor.texture_grab is not None:
            active = (KIND_TEXTURE, editor.texture_grab["entry"])
        elif editor.dialog is not None:
            active = (editor.dialog["kind"], editor.dialog["entry"])
        active_corner = editor.texture_grab["corner"] if editor.texture_grab else None
        if active is not None:
            draw_object_outline(
                surface,
                layout,
                active[0],
                active[1],
                HIGHLIGHT,
                2,
                handles=active[0] == KIND_TEXTURE,
                active_corner=active_corner,
            )
        # 光标压在某张贴图的角上：把那四角也画出来，并高亮要拉的那个
        handle = editor.hovered_handle
        if handle is not None and (active is None or handle[0] is not active[1]):
            entry, corner = handle
            draw_object_outline(
                surface, layout, KIND_TEXTURE, entry, DIM_TEXT, 1, handles=True, active_corner=corner
            )
        # 光标下的另一个对象只是淡描边，避免和选中项抢视线
        hovered = editor.hovered
        if (
            hovered is not None
            and (active is None or hovered[1] is not active[1])
            and (handle is None or hovered[1] is not handle[0])
        ):
            draw_object_outline(surface, layout, hovered[0], hovered[1], DIM_TEXT, 1)


def draw_object_outline(
    surface: pygame.Surface,
    layout: Layout,
    kind: str,
    entry: dict,
    color: tuple,
    width: int = 2,
    handles: bool = False,
    active_corner: str | None = None,
) -> None:
    """给一个对象画描边；贴图可以顺便画出四角的缩放把手。"""
    if kind == KIND_TEXTURE:
        rect = texture_rect(layout, entry)
        pygame.draw.rect(surface, color, rect, width)
        if handles:
            for name, point in (
                ("bl", rect.bottomleft),
                ("br", rect.bottomright),
                ("tl", rect.topleft),
                ("tr", rect.topright),
            ):
                size = 14 if name == active_corner else 9
                box = pygame.Rect(0, 0, size, size)
                box.center = point
                pygame.draw.rect(surface, HIGHLIGHT if name == active_corner else HANDLE_COLOR, box)
        return
    box = nozzle_box(entry) if kind == KIND_NOZZLE else entry
    pygame.draw.rect(surface, color, layout.entry_rect(box), width)


def _dotted_line(
    surface: pygame.Surface, start: tuple, end: tuple, color: tuple, dash: float = 4.0, gap: float = 4.0
) -> None:
    """两点之间画虚线，斜着也走直线。"""
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length < 1:
        return
    ux, uy = dx / length, dy / length
    position = 0.0
    while position < length:
        head = position
        tail = min(position + dash, length)
        pygame.draw.line(
            surface,
            color,
            (start[0] + ux * head, start[1] + uy * head),
            (start[0] + ux * tail, start[1] + uy * tail),
        )
        position += dash + gap


def draw_pivot_guide(surface: pygame.Surface, layout: Layout, entry: dict) -> None:
    """可移动方块：pos 那一格的中心是支点，支点 + offset 是目标点，两点红色虚线相连。"""
    pos = entry["pos"]
    cell = layout.cell_rect(pos[0], pos[1], (1, 1))
    pivot = (float(cell.centerx), float(cell.centery))
    offset = entry.get("offset", [0, 0])
    target = (pivot[0] + offset[0] * layout.tile, pivot[1] - offset[1] * layout.tile)
    _dotted_line(surface, pivot, target, PIVOT_COLOR)
    for point in (pivot, target):
        pygame.draw.circle(surface, PIVOT_COLOR, (round(point[0]), round(point[1])), 3)


def _arrow_head(surface: pygame.Surface, tip: tuple, direction: tuple, color: tuple, size: int = 7) -> None:
    """单个箭头：尖端在 tip，direction 是由尾部指向尖端的单位向量。"""
    dx, dy = direction
    base_x = tip[0] - dx * size
    base_y = tip[1] - dy * size
    half = size * 0.5
    pygame.draw.polygon(
        surface,
        color,
        [
            (tip[0], tip[1]),
            (base_x - dy * half, base_y + dx * half),
            (base_x + dy * half, base_y - dx * half),
        ],
    )


def nozzle_range_rect(layout: Layout, entry: dict) -> pygame.Rect:
    """风区（range）占的那一格宽、length 格高的矩形。"""
    x, y = entry["pos"]
    length = max(0, int(entry.get("range", 0)))
    up = int(entry.get("power", NOZZLE_DEFAULT_POWER)) >= 0
    bottom = y if up else y - length
    return layout.cell_rect(x - 0.5, bottom, (1, max(1, length)))


def draw_nozzle_range(surface: pygame.Surface, layout: Layout, entry: dict) -> None:
    """范围用虚线框标出来。"""
    if int(entry.get("range", 0)) <= 0:
        return
    rect = nozzle_range_rect(layout, entry)
    corners = [rect.topleft, rect.topright, rect.bottomright, rect.bottomleft]
    for start, end in zip(corners, corners[1:] + corners[:1]):
        _dotted_line(surface, start, end, RANGE_COLOR, dash=3.0, gap=3.0)


def draw_nozzle_power(surface: pygame.Surface, layout: Layout, entry: dict) -> None:
    """力度用一条从 pos 指向目标的红色尺寸线，只在目标端有一个箭头。"""
    power = int(entry.get("power", 0))
    if power == 0:
        return
    center_x = layout.left + entry["pos"][0] * layout.tile
    base_y = layout.top + (layout.rows + 1 - entry["pos"][1]) * layout.tile
    tip_y = base_y - power * layout.tile
    pygame.draw.line(surface, PIVOT_COLOR, (center_x, base_y), (center_x, tip_y), 2)
    direction = (0.0, -1.0 if power > 0 else 1.0)
    _arrow_head(surface, (center_x, tip_y), direction, PIVOT_COLOR)


def draw_ruler(surface: pygame.Surface, layout: Layout, font: pygame.font.Font) -> None:
    """画布底部的刻度：每 10 格一个刻度和编号，跟着网格一起移动。"""
    top = layout.top + (layout.rows + 2) * layout.tile
    left = layout.left
    pygame.draw.line(surface, DIALOG_BORDER, (left, top), (left + layout.width, top))
    for block in range(0, layout.cols + 1, RULER_STEP):
        x = left + block * layout.tile
        if x < -layout.tile or x > surface.get_width() + layout.tile:
            continue
        pygame.draw.line(surface, DIM_TEXT, (x, top), (x, top + 5))
        text = font.render(str(block), True, DIM_TEXT)
        if block == 0:
            text_x = x + 2
        elif block == layout.cols:
            text_x = x - text.get_width() - 2
        else:
            text_x = x - text.get_width() / 2
        text_x = max(0.0, min(text_x, surface.get_width() - text.get_width()))
        surface.blit(text, (text_x, top + 6))
