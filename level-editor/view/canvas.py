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
    FACE_DIRECTIONS,
    FACE_ORDER,
    FLIP_DOWN_COLOR,
    FLIP_UP_COLOR,
    GRID,
    GROUND_COLOR,
    HANDLE_COLOR,
    HIGHLIGHT,
    ITEM_COLOR,
    KIND_BUTTON,
    KIND_PORTAL,
    MIN_SIZE,
    MOVABLE_COLOR,
    NOZZLE_COLOR,
    PANEL,
    PIVOT_COLOR,
    PLANK_COLOR,
    PLAYER_COLOR,
    PORTAL_COLOR,
    PREVIEW,
    RANGE_COLOR,
    RULER_STEP,
    TOOL_COLORS,
)
from core.helpers import (
    normalize_rect,
    nozzle_box,
    nozzle_face_axis,
    nozzle_marker_box,
    nozzle_power_tip,
    object_box,
    readable_color,
)
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
    """按钮的棱台：窄端指向 face（up/right/down/left），占满这块矩形，和游戏一致。

    矩形已经按朝向摆正过（左右朝向是竖的），所以这里只把四条边做成梯形，不旋转整块。
    """
    name = str(face)
    if name in ("left", "right"):
        inset = max(1.0, rect.height * 0.2)
        far = rect.right if name == "right" else rect.left
        near = rect.left if name == "right" else rect.right
        return [
            (near, rect.top),
            (far, rect.top + inset),
            (far, rect.bottom - inset),
            (near, rect.bottom),
        ]
    inset = max(1.0, rect.width * 0.2)
    far = rect.top if name == "up" else rect.bottom
    near = rect.bottom if name == "up" else rect.top
    return [
        (rect.left, near),
        (rect.right, near),
        (rect.right - inset, far),
        (rect.left + inset, far),
    ]


def draw_canvas(surface: pygame.Surface, editor: Editor, layout: Layout) -> None:
    level = editor.level
    tile = layout.tile
    debug = editor.view_settings.get("debug", True)
    pygame.draw.rect(surface, PANEL, (layout.left, layout.top, layout.width, layout.height))
    if editor.view_settings.get("background", True):
        draw_background(surface, layout, level.background, editor.media_base_dir)

    for row in range(layout.rows + 2):
        top = layout.top + row * tile
        if row in (0, layout.rows + 1):
            pygame.draw.rect(surface, GROUND_COLOR, (layout.left, top, layout.width, tile))

    # 网格先画：所有对象（方块、贴图、机关标记）都压在它上面，别被辅助线切开。
    # 网格还是按整格画（吸附细到半格，但不改网格的样子）
    for col in range(layout.cols + 1):
        x = layout.left + col * tile
        if -tile <= x <= layout.window[0] + tile:
            pygame.draw.line(surface, GRID, (x, layout.top), (x, layout.top + layout.height))
    for row in range(layout.rows + 3):
        y = layout.top + row * tile
        pygame.draw.line(surface, GRID, (layout.left, y), (layout.left + layout.width, y))

    # 调试显示也包含翻转带：画在对象下面，标出区域但不盖住方块
    if debug:
        draw_flip_area(surface, editor, layout)
        for entry in level.blocks:
            pygame.draw.rect(surface, BLOCK_COLOR, layout.entry_rect(entry))
        for entry in level.planks:
            pygame.draw.rect(surface, PLANK_COLOR, layout.entry_rect(entry))
        for entry in level.movable_blocks:
            pygame.draw.rect(surface, MOVABLE_COLOR, layout.entry_rect(entry))

    # 贴图压在所有方块之上（方块、木板、可移动方块）
    draw_textures(surface, layout, level, editor.media_base_dir)

    if debug:
        for entry in level.buttons:
            pygame.draw.polygon(
                surface,
                BUTTON_COLOR,
                frustum_points(
                    layout.entry_rect(object_box(KIND_BUTTON, entry)), entry.get("face", "")
                ),
            )

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

        for entry in level.portals:
            draw_portal(surface, layout, entry)

        selected_ids = {id(entry) for _, entry in editor.selection}
        for entry in level.nozzles:
            draw_nozzle(surface, layout, entry, selected=id(entry) in selected_ids)

        # 起点和终点都画成同一款标记：2px 方框 + 中心小方点
        if level.player is not None:
            draw_cell_marker(surface, layout.entry_rect(level.player), PLAYER_COLOR)
        if level.destination:
            draw_cell_marker(surface, layout.entry_rect(level.destination), DESTINATION_COLOR)

        # 可移动方块：支点、目标点，以及两点之间的红色虚线（直线，不拐弯）
        for entry in level.movable_blocks:
            draw_pivot_guide(surface, layout, entry)

    # 拖动预览（浮点自由矩形）
    if editor.drag_start is not None and editor.drag_current is not None:
        x, y, w, h = normalize_rect(editor.drag_start, editor.drag_current, MIN_SIZE)
        preview = pygame.Surface((max(1, round(w * tile)), max(1, round(h * tile))), pygame.SRCALPHA)
        preview.fill(PREVIEW)
        surface.blit(preview, layout.world_rect(x, y, w, h).topleft)

    # 框选中的矩形
    if editor.marquee_start is not None and editor.marquee_current is not None:
        x0, x1 = sorted((editor.marquee_start[0], editor.marquee_current[0]))
        y0, y1 = sorted((editor.marquee_start[1], editor.marquee_current[1]))
        rect = layout.world_rect(x0, y0, max(0.0, x1 - x0), max(0.0, y1 - y0))
        fill = pygame.Surface(rect.size, pygame.SRCALPHA)
        fill.fill((255, 230, 120, 60))
        surface.blit(fill, rect.topleft)
        pygame.draw.rect(surface, HIGHLIGHT, rect, 1)

    if editor.creating:
        # 新建状态：光标处用「要放的那种对象」的颜色描边；拖动时改画整个预览范围
        color = readable_color(TOOL_COLORS.get(editor.tool, HIGHLIGHT))
        if editor.drag_start is not None and editor.drag_current is not None:
            x, y, w, h = normalize_rect(editor.drag_start, editor.drag_current, MIN_SIZE)
            pygame.draw.rect(surface, color, layout.world_rect(x, y, w, h), 2)
        else:
            point = layout.world_point(pygame.mouse.get_pos())
            left, bottom = point
            pygame.draw.rect(surface, color, layout.world_rect(left, bottom, 1.0, 1.0), 2)
    elif not editor.startup:
        # 选中的对象都亮着；只有"唯一选中"的那个才画四角把手
        grabbed = (editor.object_grab["kind"], editor.object_grab["entry"]) if editor.object_grab else None
        selected = grabbed or (editor.selection[0] if len(editor.selection) == 1 else None)
        for kind, entry in editor.selection:
            if selected is not None and entry is selected[1]:
                continue
            draw_object_outline(surface, layout, kind, entry, HIGHLIGHT, 1)
        if selected is not None:
            active_corner = editor.object_grab["corner"] if editor.object_grab else None
            draw_object_outline(
                surface,
                layout,
                selected[0],
                selected[1],
                HIGHLIGHT,
                2,
                handles=True,
                active_corner=active_corner,
            )
        # 光标下的对象只给淡描边，不画把手
        hovered = editor.hovered
        if hovered is not None and not any(hovered[1] is entry for _, entry in editor.selection):
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
    """给一个对象画描边，需要时画出缩放把手：四角 + 四条边的中点。"""
    rect = layout.entry_rect(object_box(kind, entry))
    pygame.draw.rect(surface, color, rect, width)
    if not handles:
        return
    for name, point, size in (
        ("bl", rect.bottomleft, 9),
        ("br", rect.bottomright, 9),
        ("tl", rect.topleft, 9),
        ("tr", rect.topright, 9),
        ("l", rect.midleft, 7),
        ("r", rect.midright, 7),
        ("b", rect.midbottom, 7),
        ("t", rect.midtop, 7),
    ):
        active = name == active_corner
        handle = pygame.Rect(0, 0, 14 if active else size, 14 if active else size)
        handle.center = point
        pygame.draw.rect(surface, HIGHLIGHT if active else HANDLE_COLOR, handle)


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
    """可移动方块：对象中心是支点，支点 + offset 是目标点，两点红色虚线相连。"""
    rect = layout.entry_rect(entry)
    pivot = (float(rect.centerx), float(rect.centery))
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


def draw_nozzle(surface: pygame.Surface, layout: Layout, entry: dict, selected: bool = False) -> None:
    """喷口：风区虚线框 + 底面朝 face 的三角 + 力度箭头（选中时末端有可拖的高亮把手）。"""
    range_rect = layout.entry_rect(nozzle_box(entry))
    corners = [range_rect.topleft, range_rect.topright, range_rect.bottomright, range_rect.bottomleft]
    for start, end in zip(corners, corners[1:] + corners[:1]):
        _dotted_line(surface, start, end, RANGE_COLOR, dash=3.0, gap=3.0)

    # 三角画在自己的 1×1 格里：底边中点落在 pos 上，尖端朝 face 那一边
    marker = layout.entry_rect(nozzle_marker_box(entry))
    step_x, step_y = nozzle_face_axis(entry)
    if step_x:
        base = marker.left if step_x > 0 else marker.right
        apex = marker.right if step_x > 0 else marker.left
        points = [(base, marker.top), (base, marker.bottom), (apex, marker.centery)]
    else:
        base = marker.bottom if step_y > 0 else marker.top
        apex = marker.top if step_y > 0 else marker.bottom
        points = [(marker.left, base), (marker.right, base), (marker.centerx, apex)]
    pygame.draw.polygon(surface, NOZZLE_COLOR, points)

    draw_nozzle_power(surface, layout, entry, selected)


def draw_nozzle_power(surface: pygame.Surface, layout: Layout, entry: dict, selected: bool = False) -> None:
    """力度：从 pos 沿 face 指向末端的红色尺寸线 + 箭头；只有选中时末端才画可拖的高亮把手。"""
    step_x, step_y = nozzle_face_axis(entry)
    # 0.1 格的小方块取中心：正好落在那个世界坐标上（world_rect 最小 1px 也不影响）
    x, y = entry["pos"]
    base_x, base_y = layout.world_rect(x - 0.05, y - 0.05, 0.1, 0.1).center
    tip_x, tip_y = nozzle_power_tip(entry)
    tip = layout.world_rect(tip_x - 0.05, tip_y - 0.05, 0.1, 0.1).center
    pygame.draw.line(surface, PIVOT_COLOR, (base_x, base_y), tip, 2)
    _arrow_head(surface, tip, (step_x, -step_y), PIVOT_COLOR)
    if not selected:
        return
    # 末端的高亮把手：拖它就是改力度（力度是 0 时它就贴在 pos 上，照样能拖出去）
    if step_x:
        size = (3, max(10, round(layout.tile * 0.6)))
    else:
        size = (max(10, round(layout.tile * 0.6)), 3)
    handle = pygame.Rect(0, 0, *size)
    handle.center = tip
    pygame.draw.rect(surface, HIGHLIGHT, handle)


def draw_portal(surface: pygame.Surface, layout: Layout, entry: dict) -> None:
    """传送门：那块门就是触发区（左右朝向时竖起来），再画一个朝向箭头。"""
    rect = layout.entry_rect(object_box(KIND_PORTAL, entry))
    pygame.draw.rect(surface, PORTAL_COLOR, rect)
    pygame.draw.rect(surface, DIALOG_BORDER, rect, 1)

    # 朝向：从门的中心往朝的那一边画一小段箭头，出来时也是往这边挪
    step_x, step_y = FACE_DIRECTIONS.get(str(entry.get("face", FACE_ORDER[0])), (0.0, 1.0))
    center = rect.center
    tip = (
        center[0] + step_x * layout.tile * 0.7,
        center[1] - step_y * layout.tile * 0.7,
    )
    pygame.draw.line(surface, PORTAL_COLOR, center, tip, 2)
    _arrow_head(surface, tip, (step_x, -step_y), PORTAL_COLOR, size=6)


def draw_flip_area(surface: pygame.Surface, editor: Editor, layout: Layout) -> None:
    """翻转带：向上翻贴顶画红斜纹、向下翻贴底画蓝斜纹（和游戏里的调试显示一样）。

    带的几何和游戏里同一套：向上翻是 [关卡高度 - 上偏移, 关卡高度)，
    向下翻是 [0, 下偏移)，偏移是 0 就是空带子。画在对象下面，不盖住方块。
    """
    level = editor.level
    height = float(level.height)
    window = pygame.Rect(0, 0, *layout.window)
    up_offset, down_offset = level.flip_area_offsets
    for upward, offset in ((True, float(up_offset)), (False, float(down_offset))):
        if offset <= 0.0:
            continue
        low, high = (height - offset, height) if upward else (0.0, offset)
        rect = layout.world_rect(0.0, low, float(level.width), high - low).clip(window)
        if rect.width <= 0 or rect.height <= 0:
            continue
        _hatch(surface, rect, FLIP_UP_COLOR if upward else FLIP_DOWN_COLOR)


def _hatch(surface: pygame.Surface, rect: pygame.Rect, color: tuple, step: int = 14, width: int = 4) -> None:
    """斜向斑马纹：45° 斜线铺满这块矩形，颜色带 alpha 所以是半透明的。"""
    layer = pygame.Surface(rect.size, pygame.SRCALPHA)
    reach = rect.height
    for x in range(-reach - step, rect.width + step, step):
        pygame.draw.line(layer, color, (x, rect.height), (x + reach, 0), width)
    surface.blit(layer, rect.topleft)


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
