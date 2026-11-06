"""浮层：启动窗、关卡列表、关卡设置、游戏配置、切换确认、退出确认。"""

import os
from typing import TYPE_CHECKING

import pygame

from core.constants import (
    BUTTON_BG,
    BUTTON_HEIGHT,
    DIALOG_BORDER,
    DIM_TEXT,
    FOOTER,
    HEADER,
    HIGHLIGHT,
    LEVEL_SELECT_WIDTH,
    MARGIN,
    ROW_HEIGHT,
    TEXT,
)
from core.helpers import display_path, level_name_of
from view.widgets import draw_button, draw_panel, draw_stepper, place_panel, stepper_rects

if TYPE_CHECKING:
    from editing.editor import Editor


def startup_rects(surface: pygame.Surface) -> list:
    """启动窗：先问要哪份游戏配置（game.json）。"""
    panel = pygame.Rect(0, 0, 400, 156)
    panel.center = (surface.get_width() // 2, surface.get_height() // 2)
    return [
        (pygame.Rect(panel.left + 24, panel.top + 84, 160, 32), "create"),
        (pygame.Rect(panel.right - 24 - 160, panel.top + 84, 160, 32), "open"),
    ]


def draw_startup(surface: pygame.Surface, font: pygame.font.Font) -> None:
    panel = place_panel(surface, pygame.Rect(0, 0, 400, 156))
    draw_panel(surface, panel)
    title = font.render("关卡编辑器", True, TEXT)
    surface.blit(title, (panel.centerx - title.get_width() // 2, panel.top + 16))
    hint = font.render("请打开或新建游戏配置文件（game.json）。", True, DIM_TEXT)
    surface.blit(hint, (panel.centerx - hint.get_width() // 2, panel.top + 50))
    for rect, action in startup_rects(surface):
        pygame.draw.rect(surface, BUTTON_BG, rect)
        pygame.draw.rect(surface, DIALOG_BORDER, rect, 1)
        label = "新建游戏配置" if action == "create" else "打开游戏配置"
        text = font.render(label, True, TEXT)
        surface.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))


def level_select_geometry(surface: pygame.Surface, count: int) -> tuple:
    """关卡列表浮层：标题 + 列表 + 新建关卡 / 关闭。

    列表按窗口高度决定能看到几行，超出的部分用滚轮翻（scroll 是编辑器上的状态）。
    """
    # 最多摊 14 行：再多就滚动，面板不至于顶满整个窗口
    rows_visible = max(1, min(14, (surface.get_height() - 200) // ROW_HEIGHT))
    rows_visible = max(1, min(count if count else 1, rows_visible))
    panel = place_panel(
        surface,
        pygame.Rect(0, 0, LEVEL_SELECT_WIDTH, 96 + rows_visible * ROW_HEIGHT + BUTTON_HEIGHT + 16),
    )
    area = pygame.Rect(
        panel.left + 12,
        panel.top + 40,
        panel.width - 24,
        rows_visible * ROW_HEIGHT,
    )
    button_y = panel.bottom - BUTTON_HEIGHT - 10
    create_rect = pygame.Rect(panel.right - 12 - 96, button_y, 96, BUTTON_HEIGHT)
    close_rect = pygame.Rect(create_rect.left - 10 - 76, button_y, 76, BUTTON_HEIGHT)
    return panel, area, rows_visible, create_rect, close_rect


def draw_level_select(surface: pygame.Surface, editor: Editor, font: pygame.font.Font) -> None:
    files = editor.level_files()
    panel, area, rows_visible, create_rect, close_rect = level_select_geometry(surface, len(files))
    draw_panel(surface, panel)

    surface.blit(font.render("选择关卡", True, TEXT), (panel.left + 12, panel.top + 10))
    hint = font.render(display_path(editor.levels_dir) if editor.levels_dir else "", True, DIM_TEXT)
    surface.blit(hint, (panel.right - 12 - hint.get_width(), panel.top + 10))

    if not files:
        text = font.render("levels/ 目录中暂无关卡，请点击「新建关卡」创建。", True, DIM_TEXT)
        surface.blit(text, (area.left + 6, area.top + 6))
    else:
        # 列表超出窗口时按 scroll 翻页，只画能看见的几行
        scroll = max(0, min(editor.level_select_scroll, max(0, len(files) - rows_visible)))
        previous = surface.get_clip()
        surface.set_clip(area)
        mouse = pygame.mouse.get_pos()
        current = os.path.normpath(editor.path) if editor.path else None
        for row in range(rows_visible):
            index = scroll + row
            if index >= len(files):
                break
            path = files[index]
            rect = pygame.Rect(area.left, area.top + row * ROW_HEIGHT, area.width, ROW_HEIGHT)
            if rect.collidepoint(mouse):
                pygame.draw.rect(surface, (100, 100, 110), rect)
            mark = "✓" if current is not None and os.path.normpath(path) == current else "  "
            text = font.render(f"{mark} {level_name_of(path)}", True, TEXT)
            surface.blit(text, (rect.left + 6, rect.centery - text.get_height() // 2))
        surface.set_clip(previous)
        if len(files) > rows_visible:
            more = font.render(
                f"{scroll + 1}-{min(scroll + rows_visible, len(files))} / {len(files)}（滚轮翻页）",
                True,
                DIM_TEXT,
            )
            surface.blit(more, (area.right - more.get_width(), area.bottom + 2))

    draw_button(surface, font, create_rect, "新建关卡")
    draw_button(surface, font, close_rect, "关闭")


def settings_geometry(surface: pygame.Surface) -> tuple:
    """关卡设置：名称、宽高、翻转带、背景，以及玩家参数的本关覆盖。"""
    panel = place_panel(surface, pygame.Rect(0, 0, 560, 368))
    name_rect = pygame.Rect(panel.left + 12, panel.top + 38, panel.width - 24, ROW_HEIGHT + 2)
    width_rect = pygame.Rect(panel.left + 12, panel.top + 72, panel.width - 24, ROW_HEIGHT + 2)
    height_rect = pygame.Rect(panel.left + 12, panel.top + 106, panel.width - 24, ROW_HEIGHT + 2)
    flip_up_rect = pygame.Rect(panel.left + 12, panel.top + 140, panel.width - 24, ROW_HEIGHT + 2)
    flip_down_rect = pygame.Rect(panel.left + 12, panel.top + 174, panel.width - 24, ROW_HEIGHT + 2)
    background_rect = pygame.Rect(
        panel.left + 12, panel.top + 208, panel.width - 24, ROW_HEIGHT + 2
    )
    browse_rect = pygame.Rect(
        background_rect.right - 76, background_rect.top + 1, 76, background_rect.height - 2
    )
    player_hint_rect = pygame.Rect(
        panel.left + 12, panel.top + 242, panel.width - 24, ROW_HEIGHT
    )
    jump_rect = pygame.Rect(panel.left + 12, panel.top + 264, panel.width - 24, ROW_HEIGHT + 2)
    speed_rect = pygame.Rect(panel.left + 12, panel.top + 298, panel.width - 24, ROW_HEIGHT + 2)
    button_y = panel.bottom - BUTTON_HEIGHT - 8
    apply_rect = pygame.Rect(panel.right - 12 - 140, button_y, 68, BUTTON_HEIGHT)
    cancel_rect = pygame.Rect(panel.right - 12 - 68, button_y, 68, BUTTON_HEIGHT)
    return (
        panel,
        name_rect,
        width_rect,
        height_rect,
        flip_up_rect,
        flip_down_rect,
        background_rect,
        browse_rect,
        player_hint_rect,
        jump_rect,
        speed_rect,
        apply_rect,
        cancel_rect,
    )


def _draw_settings_row(
    surface: pygame.Surface,
    font: pygame.font.Font,
    rect: pygame.Rect,
    label: str,
    value,
    selected: bool,
) -> None:
    pygame.draw.rect(surface, (62, 62, 72) if selected else (48, 48, 54), rect)
    pygame.draw.rect(surface, HIGHLIGHT if selected else (86, 86, 94), rect, 1)
    text = font.render(f"{label}: {value}", True, HIGHLIGHT if selected else TEXT)
    surface.blit(text, (rect.left + 6, rect.centery - text.get_height() // 2))


def draw_settings(surface: pygame.Surface, editor: Editor, font: pygame.font.Font) -> None:
    (
        panel,
        name_rect,
        width_rect,
        height_rect,
        flip_up_rect,
        flip_down_rect,
        background_rect,
        browse_rect,
        player_hint_rect,
        jump_rect,
        speed_rect,
        apply_rect,
        cancel_rect,
    ) = settings_geometry(surface)
    draw_panel(surface, panel)

    surface.blit(font.render("关卡设置", True, TEXT), (panel.left + 12, panel.top + 8))
    hint = font.render("点击面板外区域即取消", True, DIM_TEXT)
    surface.blit(hint, (panel.right - 12 - hint.get_width(), panel.top + 8))

    name = editor.settings["name"]
    name_selected = editor.settings_field == 0
    pygame.draw.rect(surface, (62, 62, 72) if name_selected else (48, 48, 54), name_rect)
    pygame.draw.rect(surface, HIGHLIGHT if name_selected else (86, 86, 94), name_rect, 1)
    caret = "|" if name_selected else ""
    # 名字就是文件名：改了名字，保存时写到 levels/<新名字>.json
    text = font.render(
        f"名称（即文件名）：{name if name else '（空）'}{caret}",
        True,
        HIGHLIGHT if name_selected else TEXT,
    )
    clip = max(1, name_rect.width - 12)
    surface.blit(
        text,
        (name_rect.left + 6, name_rect.centery - text.get_height() // 2),
        (0, 0, min(text.get_width(), clip), text.get_height()),
    )

    # 宽高决定画布大小：游戏里可玩行固定 400px，所以高度越大格子越小
    for field, rect, label, key in (
        (1, width_rect, "宽度（格）", "width"),
        (2, height_rect, "高度（格）", "height"),
    ):
        selected = editor.settings_field == field
        _draw_settings_row(surface, font, rect, label, editor.settings[key], selected)
        left, right = stepper_rects(rect)
        draw_stepper(surface, left, -1)
        draw_stepper(surface, right, 1)

    # 翻转带：脚边落在带子里才翻得动。向上翻贴着关卡顶、向下翻贴着关卡底，
    # 数字是带子的高度，0 表示这一侧翻不了
    for field, rect, label, key in (
        (3, flip_up_rect, "向上翻带（贴顶）", "flip_up"),
        (4, flip_down_rect, "向下翻带（贴底）", "flip_down"),
    ):
        selected = editor.settings_field == field
        _draw_settings_row(surface, font, rect, label, editor.settings[key], selected)
        left, right = stepper_rects(rect)
        draw_stepper(surface, left, -1)
        draw_stepper(surface, right, 1)

    # 背景：直接敲路径，或点右边「选择…」挑一张图；存的是相对关卡目录的路径
    background_selected = editor.settings_field == 5
    pygame.draw.rect(
        surface, (62, 62, 72) if background_selected else (48, 48, 54), background_rect
    )
    pygame.draw.rect(
        surface, HIGHLIGHT if background_selected else (86, 86, 94), background_rect, 1
    )
    path = editor.settings["background"]
    caret = "|" if background_selected else ""
    text = font.render(
        f"背景：{path if path else '（无）'}{caret}",
        True,
        HIGHLIGHT if background_selected else TEXT,
    )
    clip = max(1, browse_rect.left - background_rect.left - 12)
    surface.blit(
        text,
        (background_rect.left + 6, background_rect.centery - text.get_height() // 2),
        (0, 0, min(text.get_width(), clip), text.get_height()),
    )
    draw_button(surface, font, browse_rect, "浏览…")

    # 玩家参数默认来自游戏配置；这两格填了就是本关的覆盖值，空着跟随游戏配置
    surface.blit(
        font.render("玩家（留空跟随游戏配置，填了就覆盖本关）", True, DIM_TEXT),
        (player_hint_rect.left, player_hint_rect.top + 2),
    )
    for field, rect, label, key, fallback, unit in (
        (6, jump_rect, "跳高", "jump_height", editor.player_stats()[0], "格"),
        (7, speed_rect, "速度", "move_speed", editor.player_stats()[1], "格/秒"),
    ):
        selected = editor.settings_field == field
        raw = editor.settings[key]
        value = raw if raw else f"跟随（{fallback:g}）"
        _draw_settings_row(surface, font, rect, f"{label}（{unit}）", value, selected)
        left, right = stepper_rects(rect)
        draw_stepper(surface, left, -1)
        draw_stepper(surface, right, 1)

    draw_button(surface, font, apply_rect, "应用")
    draw_button(surface, font, cancel_rect, "取消")


GAME_PANEL_WIDTH = 620
GAME_HEADER_HEIGHT = 166        # 面板顶部到版权卡片区之前的固定高度
GAME_FOOTER_HEIGHT = 74         # 卡片区之后：说明、按钮
CREDIT_CARD_PAD = 6
CREDIT_CARD_GAP = 6
CREDIT_LINE_HEIGHT = ROW_HEIGHT
CREDIT_JOB_WIDTH = 150
CREDIT_ICON = 16                # 名字行尾的「−」和下边「＋」的边长


def _credit_card_height(card: dict) -> int:
    """一张版权卡片的高度：职位一格、每个名字一行，底下再加一行「＋」。"""
    lines = max(1, len(card["names"]))
    return CREDIT_CARD_PAD * 2 + lines * CREDIT_LINE_HEIGHT + CREDIT_LINE_HEIGHT


def game_settings_geometry(surface: pygame.Surface, cards: list, scroll: int = 0) -> tuple:
    """游戏配置：标题、玩家的跳高与速度、每个职位一张版权卡片，再加应用/取消。

    卡片一张一张往下排，装不下就用滚轮翻（scroll 是编辑器上的 game_card_scroll）。
    """
    card_heights = [_credit_card_height(card) for card in cards]
    content = sum(height + CREDIT_CARD_GAP for height in card_heights)
    # 面板最高顶到信息栏下面、状态栏上面，剩下的靠滚轮翻
    max_height = max(360, surface.get_height() - HEADER - FOOTER - 8)
    wanted = GAME_HEADER_HEIGHT + max(120, content) + GAME_FOOTER_HEIGHT
    panel = place_panel(
        surface, pygame.Rect(0, 0, GAME_PANEL_WIDTH, min(wanted, max_height))
    )
    title_rect = pygame.Rect(panel.left + 12, panel.top + 38, panel.width - 24, ROW_HEIGHT + 2)
    player_section_rect = pygame.Rect(panel.left + 12, panel.top + 66, panel.width - 24, ROW_HEIGHT)
    jump_rect = pygame.Rect(panel.left + 12, panel.top + 88, panel.width - 24, ROW_HEIGHT)
    speed_rect = pygame.Rect(
        panel.left + 12, panel.top + 92 + ROW_HEIGHT, panel.width - 24, ROW_HEIGHT
    )
    section_rect = pygame.Rect(
        panel.left + 12, panel.top + 120 + ROW_HEIGHT, panel.width - 24, ROW_HEIGHT
    )
    cards_area = pygame.Rect(
        panel.left + 12,
        panel.top + GAME_HEADER_HEIGHT,
        panel.width - 24,
        max(0, panel.height - GAME_HEADER_HEIGHT - GAME_FOOTER_HEIGHT),
    )

    # 从滚动位置开始往下摆，装不下的卡片先不画（内容还在，应用时照样写回）
    layouts = []
    scroll = max(0, min(scroll, max(0, len(cards) - 1)))
    y = cards_area.top
    for index in range(scroll, len(cards)):
        height = card_heights[index]
        if y + height > cards_area.bottom:
            break
        card_rect = pygame.Rect(cards_area.left, y, cards_area.width, height)
        job_rect = pygame.Rect(
            card_rect.left + CREDIT_CARD_PAD,
            card_rect.top + CREDIT_CARD_PAD,
            CREDIT_JOB_WIDTH,
            CREDIT_LINE_HEIGHT,
        )
        name_left = job_rect.right + 8
        name_width = card_rect.right - CREDIT_CARD_PAD - name_left - CREDIT_ICON - 4
        name_rects = []
        minus_rects = []
        for line in range(len(cards[index]["names"])):
            line_top = card_rect.top + CREDIT_CARD_PAD + line * CREDIT_LINE_HEIGHT
            name_rects.append(pygame.Rect(name_left, line_top, name_width, CREDIT_LINE_HEIGHT))
            minus_rects.append(
                pygame.Rect(
                    name_left + name_width + 4,
                    line_top + (CREDIT_LINE_HEIGHT - CREDIT_ICON) // 2,
                    CREDIT_ICON,
                    CREDIT_ICON,
                )
            )
        plus_rect = pygame.Rect(
            name_left,
            card_rect.top + CREDIT_CARD_PAD + max(1, len(cards[index]["names"])) * CREDIT_LINE_HEIGHT,
            CREDIT_ICON,
            CREDIT_ICON,
        )
        layouts.append(
            {
                "index": index,
                "rect": card_rect,
                "job": job_rect,
                "names": name_rects,
                "minus": minus_rects,
                "plus": plus_rect,
            }
        )
        y += height + CREDIT_CARD_GAP
    visible = len(layouts)

    button_y = panel.bottom - BUTTON_HEIGHT - 10
    add_rect = pygame.Rect(panel.left + 12, button_y, 110, BUTTON_HEIGHT)
    remove_rect = pygame.Rect(add_rect.right + 8, button_y, 110, BUTTON_HEIGHT)
    apply_rect = pygame.Rect(panel.right - 12 - 140, button_y, 68, BUTTON_HEIGHT)
    cancel_rect = pygame.Rect(panel.right - 12 - 68, button_y, 68, BUTTON_HEIGHT)
    return (
        panel,
        title_rect,
        player_section_rect,
        jump_rect,
        speed_rect,
        section_rect,
        cards_area,
        layouts,
        visible,
        add_rect,
        remove_rect,
        apply_rect,
        cancel_rect,
    )


def draw_icon_button(
    surface: pygame.Surface, rect: pygame.Rect, glyph: str, font: pygame.font.Font
) -> None:
    """名字行尾的小方形按钮：中间画一个「−」或「＋」。"""
    pygame.draw.rect(surface, (80, 80, 90), rect)
    pygame.draw.rect(surface, (150, 150, 160), rect, 1)
    text = font.render(glyph, True, TEXT)
    surface.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))


def _draw_cell(
    surface: pygame.Surface,
    font: pygame.font.Font,
    rect: pygame.Rect,
    text: str,
    selected: bool,
) -> None:
    """一格可编辑文本：选中时高亮、末尾带光标。"""
    pygame.draw.rect(surface, (62, 62, 72) if selected else (48, 48, 54), rect)
    pygame.draw.rect(surface, HIGHLIGHT if selected else (86, 86, 94), rect, 1)
    label = f"{text}|" if selected else text
    rendered = font.render(label or "（空）", True, HIGHLIGHT if selected else TEXT)
    clip = max(1, rect.width - 12)
    surface.blit(
        rendered,
        (rect.left + 6, rect.centery - rendered.get_height() // 2),
        (0, 0, min(rendered.get_width(), clip), rendered.get_height()),
    )


def draw_game_settings(surface: pygame.Surface, editor: Editor, font: pygame.font.Font) -> None:
    cards = editor.game_cards
    cells = editor.game_cells()
    (
        panel,
        title_rect,
        player_section_rect,
        jump_rect,
        speed_rect,
        section_rect,
        cards_area,
        layouts,
        visible,
        add_rect,
        remove_rect,
        apply_rect,
        cancel_rect,
    ) = game_settings_geometry(surface, cards, editor.game_card_scroll)
    draw_panel(surface, panel)

    surface.blit(font.render("游戏配置", True, TEXT), (panel.left + 12, panel.top + 8))
    hint = font.render("点击面板外区域即取消", True, DIM_TEXT)
    surface.blit(hint, (panel.right - 12 - hint.get_width(), panel.top + 8))

    def selected_index(cell: tuple) -> bool:
        return cells[editor.game_field] == cell if editor.game_field < len(cells) else False

    _draw_cell(
        surface,
        font,
        title_rect,
        str((editor.game_settings or {}).get("title") or ""),
        selected_index(("title",)),
    )

    # 玩家参数属于整个游戏，这一关的 player 里写同名键就会覆盖它
    label = "玩家（全游戏共用，关卡里的 player 写了就覆盖它）"
    surface.blit(
        font.render(label, True, DIM_TEXT), (player_section_rect.left, player_section_rect.top + 2)
    )
    for field, cell, rect, title, key, unit in (
        (1, ("jump",), jump_rect, "跳高", "jump_height", "格"),
        (2, ("speed",), speed_rect, "速度", "move_speed", "格/秒"),
    ):
        selected = selected_index(cell)
        pygame.draw.rect(surface, (62, 62, 72) if selected else (48, 48, 54), rect)
        pygame.draw.rect(surface, HIGHLIGHT if selected else (86, 86, 94), rect, 1)
        value = editor.game_numbers.get(key, "")
        caret = "|" if selected else ""
        text = font.render(f"{title}（{unit}）：{value}{caret}", True, HIGHLIGHT if selected else TEXT)
        clip = max(1, rect.width - 12)
        surface.blit(
            text,
            (rect.left + 6, rect.centery - text.get_height() // 2),
            (0, 0, min(text.get_width(), clip), text.get_height()),
        )
        left, right = stepper_rects(rect)
        draw_stepper(surface, left, -1)
        draw_stepper(surface, right, 1)

    # 版权信息：每个职位一张卡片，左边写职位、右边一行一个名字
    label = "版权信息（每个职位一张卡片；名字为空也行，一个名字都没有就是空数组）"
    if len(cards) > visible:
        label += f"   滚轮翻卡片（{visible} / {len(cards)} 张可见）"
    surface.blit(font.render(label, True, DIM_TEXT), (section_rect.left, section_rect.top + 2))
    if not cards:
        text = font.render("还没有职位，请点击「添加职位」", True, DIM_TEXT)
        surface.blit(text, (cards_area.left + 6, cards_area.top + 6))
    previous_clip = surface.get_clip()
    surface.set_clip(cards_area)
    for layout in layouts:
        card = cards[layout["index"]]
        pygame.draw.rect(surface, (58, 58, 66), layout["rect"])
        pygame.draw.rect(surface, (110, 110, 120), layout["rect"], 1)
        _draw_cell(
            surface,
            font,
            layout["job"],
            str(card.get("job") or ""),
            selected_index(("job", layout["index"])),
        )
        for line, rect in enumerate(layout["names"]):
            _draw_cell(
                surface,
                font,
                rect,
                str(card["names"][line]),
                selected_index(("name", layout["index"], line)),
            )
            draw_icon_button(surface, layout["minus"][line], "−", font)
        draw_icon_button(surface, layout["plus"], "＋", font)
    surface.set_clip(previous_clip)

    # 这几项写的是游戏自己的配置，不属于任何一关
    note = font.render(
        f"{display_path(editor.game_path) if editor.game_path else 'game.json'}："
        "标题用于标题画面，玩家参数用于每一关，版权信息用于结算画面",
        True,
        DIM_TEXT,
    )
    surface.blit(note, (section_rect.left, panel.bottom - BUTTON_HEIGHT - 36))

    draw_button(surface, font, add_rect, "添加职位")
    draw_button(surface, font, remove_rect, "删除职位")
    draw_button(surface, font, apply_rect, "应用")
    draw_button(surface, font, cancel_rect, "取消")


def switch_geometry(surface: pygame.Surface) -> tuple:
    """有没保存的修改时要走开：保存并切换 / 不保存切换 / 取消。"""
    panel = place_panel(surface, pygame.Rect(0, 0, 470, 158))
    button_y = panel.bottom - 12 - BUTTON_HEIGHT
    save_rect = pygame.Rect(panel.right - 12 - 110, button_y, 110, BUTTON_HEIGHT)
    discard_rect = pygame.Rect(save_rect.left - 10 - 110, button_y, 110, BUTTON_HEIGHT)
    cancel_rect = pygame.Rect(discard_rect.left - 10 - 76, button_y, 76, BUTTON_HEIGHT)
    return panel, save_rect, discard_rect, cancel_rect


def draw_switch_confirm(surface: pygame.Surface, editor: Editor, font: pygame.font.Font) -> None:
    panel, save_rect, discard_rect, cancel_rect = switch_geometry(surface)
    draw_panel(surface, panel)

    surface.blit(font.render("关卡尚未保存", True, HIGHLIGHT), (panel.left + 14, panel.top + 12))
    surface.blit(
        font.render(
            display_path(editor.path) if editor.path else "新关卡（未保存）", True, DIM_TEXT
        ),
        (panel.left + 14, panel.top + 40),
    )
    surface.blit(
        font.render(f"存在未保存的修改，{editor.pending_switch_label()}之前是否保存？", True, TEXT),
        (panel.left + 14, panel.top + 62),
    )
    hint = font.render("Y 保存并切换；N 不保存并切换；Esc 取消", True, DIM_TEXT)
    surface.blit(hint, (panel.left + 14, panel.top + 88))

    draw_button(surface, font, save_rect, "保存并切换")
    draw_button(surface, font, discard_rect, "不保存并切换")
    draw_button(surface, font, cancel_rect, "取消")


def save_notice_geometry(surface: pygame.Surface) -> tuple:
    """存完弹的那句提示：这关缺起点/终点，游戏里会跳过它。只是个消息框。"""
    panel = place_panel(surface, pygame.Rect(0, 0, 470, 158))
    button_y = panel.bottom - 12 - BUTTON_HEIGHT
    ok_rect = pygame.Rect(panel.right - 12 - 110, button_y, 110, BUTTON_HEIGHT)
    return panel, ok_rect


def draw_save_notice(surface: pygame.Surface, editor: Editor, font: pygame.font.Font) -> None:
    panel, ok_rect = save_notice_geometry(surface)
    draw_panel(surface, panel)

    surface.blit(font.render("关卡还缺起点或终点", True, HIGHLIGHT), (panel.left + 14, panel.top + 12))
    surface.blit(
        font.render(
            display_path(editor.path) if editor.path else "新关卡（未保存）", True, DIM_TEXT
        ),
        (panel.left + 14, panel.top + 40),
    )
    surface.blit(
        font.render(
            f"这一关{editor.save_notice or '缺部分内容'}，游戏里会跳过它。", True, TEXT
        ),
        (panel.left + 14, panel.top + 62),
    )
    surface.blit(
        font.render("已经保存，关掉这条提示即可。", True, DIM_TEXT), (panel.left + 14, panel.top + 84)
    )
    hint = font.render("Enter / Esc / 点击任意位置关闭", True, DIM_TEXT)
    surface.blit(hint, (panel.left + 14, panel.top + 106))

    draw_button(surface, font, ok_rect, "知道了")


def quit_geometry(surface: pygame.Surface) -> tuple:
    panel = place_panel(surface, pygame.Rect(0, 0, 430, 152))
    button_y = panel.bottom - 12 - BUTTON_HEIGHT
    quit_rect = pygame.Rect(panel.right - 12 - 120, button_y, 120, BUTTON_HEIGHT)
    cancel_rect = pygame.Rect(quit_rect.left - 10 - 76, button_y, 76, BUTTON_HEIGHT)
    return panel, quit_rect, cancel_rect

def draw_quit_confirm(surface: pygame.Surface, editor: Editor, font: pygame.font.Font) -> None:
    panel, quit_rect, cancel_rect = quit_geometry(surface)
    draw_panel(surface, panel)

    surface.blit(font.render("关卡尚未保存", True, HIGHLIGHT), (panel.left + 14, panel.top + 12))
    surface.blit(
        font.render(
            display_path(editor.path) if editor.path else "新关卡（未保存）", True, DIM_TEXT
        ),
        (panel.left + 14, panel.top + 40),
    )
    surface.blit(
        font.render("存在未保存的修改，确定要退出吗？", True, TEXT), (panel.left + 14, panel.top + 62)
    )
    hint = font.render("Enter 退出；Esc 取消", True, DIM_TEXT)
    surface.blit(hint, (panel.left + 14, panel.top + 88))

    draw_button(surface, font, quit_rect, "不保存并退出")
    draw_button(surface, font, cancel_rect, "取消")
