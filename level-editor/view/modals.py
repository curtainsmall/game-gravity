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
    GAME_ANIMATION_TAB,
    GAME_CUTSCENE_TAB,
    GAME_PLAYER_VIEW_TAB,
    GAME_SETTINGS_TABS,
    GAME_SOUND_LIBRARY_TAB,
    HEADER,
    HIGHLIGHT,
    LEVEL_SELECT_WIDTH,
    MARGIN,
    ROW_HEIGHT,
    SETTINGS_CUTSCENE_TAB,
    SETTINGS_TABS,
    TEXT,
)
from core.helpers import display_path, level_name_of
from core.sound import SCENE_KEYS, key_label
from view.animation import draw_library_page, library_geometry, library_page_height
from view.cutscene import cutscene_geometry, cutscene_page_height, draw_cutscene_page
from view.sound import (
    draw_sound_library,
    draw_sound_menu,
    sound_library_geometry,
    sound_library_height,
    sound_menu_geometry,
)
from view.widgets import (
    draw_button,
    draw_checkbox,
    draw_panel,
    draw_scrollbar,
    draw_stepper,
    place_panel,
    stepper_rects,
)

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


def level_select_scroll(editor: "Editor", count: int, area: pygame.Rect) -> float:
    """关卡列表滚到多少像素：绘制和点击都用这一套夹取，结果写回编辑器。"""
    content = count * ROW_HEIGHT
    max_scroll = max(0.0, content - area.height)
    scroll = max(0.0, min(float(editor.level_select_scroll), max_scroll))
    editor.level_select_scroll = scroll
    return scroll


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
        # 列表按像素滚动：行从 area.top - 滚动量 开始摆，超出可视区的靠裁剪
        scroll = level_select_scroll(editor, len(files), area)
        previous = surface.get_clip()
        surface.set_clip(area)
        mouse = pygame.mouse.get_pos()
        current = os.path.normpath(editor.path) if editor.path else None
        top = area.top - round(scroll)
        for index, path in enumerate(files):
            rect = pygame.Rect(area.left, top + index * ROW_HEIGHT, area.width, ROW_HEIGHT)
            if rect.collidepoint(mouse):
                pygame.draw.rect(surface, (100, 100, 110), rect)
            mark = "✓" if current is not None and os.path.normpath(path) == current else "  "
            text = font.render(f"{mark} {level_name_of(path)}", True, TEXT)
            surface.blit(text, (rect.left + 6, rect.centery - text.get_height() // 2))
        surface.set_clip(previous)
        draw_scrollbar(surface, area, len(files) * ROW_HEIGHT, scroll)
        if len(files) * ROW_HEIGHT > area.height:
            more = font.render("滚轮上下滚动", True, DIM_TEXT)
            surface.blit(more, (area.right - more.get_width(), area.bottom + 2))

    draw_button(surface, font, create_rect, "新建关卡")
    draw_button(surface, font, close_rect, "关闭")


# ---- 页签（关卡设置和游戏配置共用） --------------------------------
TAB_HEIGHT = 24
TAB_GAP = 4
TAB_PADDING = 12
TAB_MAX_WIDTH = 180

_TAB_FONT: pygame.font.Font | None = None


def _tab_text_width(text: str) -> int:
    """页签宽度要按文字量算；几何和绘制用同一个字体，两边才对得上。"""
    global _TAB_FONT
    if _TAB_FONT is None:
        _TAB_FONT = pygame.font.SysFont("microsoftyahei", 14)
    return _TAB_FONT.size(text)[0]


def _tab_width(label: str) -> int:
    return min(TAB_MAX_WIDTH, _tab_text_width(label) + TAB_PADDING * 2)


def _pack_tabs(widths: list, limit: int) -> list:
    """页签一行放不下就换行；limit 是一行最多多宽，返回每行里有哪几页（下标）。"""
    rows: list[list[int]] = [[]]
    used = 0
    for index, width in enumerate(widths):
        if rows[-1] and used + width > limit:
            rows.append([])
            used = 0
        rows[-1].append(index)
        used += width + TAB_GAP
    return rows


SETTINGS_PANEL_WIDTH = 560
SETTINGS_PANEL_HEIGHT = 320    # 常规 / 玩家 / 声音三页一样高：切页时面板不跳（过场页按图片张数变高）
SETTINGS_PANEL_TOP = 30        # 标题下面这一行是页签
SETTINGS_CONTENT_TOP = 64      # 页签下面开始排字段


def settings_geometry(surface: pygame.Surface, editor: Editor) -> dict:
    """关卡设置：常规 / 玩家 / 声音 / 过场四页，底下是应用和取消。

    每页的字段都排成同高的行：常规是名称、宽高、翻转带、背景，玩家是跳高与速度的覆盖，
    声音是这一关的 BGM（声音库里的键）、循环和淡入淡出；过场是级联、声音和一串图片卡片（见 view.cutscene）。
    只有当前页的那些行有矩形。
    """
    tab = editor.settings_tab
    if tab == SETTINGS_CUTSCENE_TAB:
        # 过场页的高度跟着图片张数走，顶到信息栏下面、状态栏上面就用滚轮翻
        max_height = max(360, surface.get_height() - HEADER - FOOTER - 8)
        height = min(cutscene_page_height(editor, SETTINGS_CONTENT_TOP), max_height)
    else:
        height = SETTINGS_PANEL_HEIGHT
    panel = place_panel(surface, pygame.Rect(0, 0, SETTINGS_PANEL_WIDTH, height))
    tab_rects = []
    x = panel.left + MARGIN
    for index, (label, _) in enumerate(SETTINGS_TABS):
        width = _tab_width(label)
        tab_rects.append(
            (pygame.Rect(x, panel.top + SETTINGS_PANEL_TOP, width, TAB_HEIGHT), index)
        )
        x += width + TAB_GAP
    content_top = panel.top + SETTINGS_CONTENT_TOP

    row_width = panel.width - 2 * MARGIN
    rows: dict[int, pygame.Rect] = {}
    browse = None
    audio_browse = None
    audio_preview = None
    hint = None
    page = None

    def row(offset: int, width: int = row_width) -> pygame.Rect:
        return pygame.Rect(
            panel.left + MARGIN, content_top + offset, width, ROW_HEIGHT + 2
        )

    if tab == 0:                    # 常规
        for field, offset in ((0, 0), (1, 34), (2, 68), (3, 102), (4, 136), (5, 170)):
            rows[field] = row(offset)
        browse = pygame.Rect(rows[5].right - 76, rows[5].top + 1, 76, rows[5].height - 2)
        rows[5].width -= 82         # 背景格让出「浏览…」的位置
    elif tab == 1:                  # 玩家
        hint = pygame.Rect(panel.left + MARGIN, content_top, row_width, ROW_HEIGHT)
        rows[6] = row(24)
        rows[7] = row(58)
    elif tab == SETTINGS_CUTSCENE_TAB:  # 过场：级联、声音和图片卡片
        page = cutscene_geometry(surface, editor, panel, content_top)
    else:                           # 声音
        rows[8] = row(0)
        audio_preview = pygame.Rect(rows[8].right - 76, rows[8].top, 76, rows[8].height)
        audio_browse = pygame.Rect(
            audio_preview.left - 6 - 76, rows[8].top, 76, rows[8].height
        )
        rows[8].width = audio_browse.left - 6 - rows[8].left
        rows[9] = row(34, 260)
        fade_width = min(260, (row_width - 16) // 2)
        rows[10] = pygame.Rect(
            panel.left + MARGIN, content_top + 68, fade_width, ROW_HEIGHT + 2
        )
        rows[11] = pygame.Rect(rows[10].right + 16, rows[10].top, fade_width, ROW_HEIGHT + 2)
        hint = pygame.Rect(panel.left + MARGIN, content_top + 100, row_width, 44)

    button_y = panel.bottom - 12 - BUTTON_HEIGHT
    apply_rect = pygame.Rect(panel.right - MARGIN - 140, button_y, 68, BUTTON_HEIGHT)
    cancel_rect = pygame.Rect(panel.right - MARGIN - 68, button_y, 68, BUTTON_HEIGHT)
    # 「选择…」摊开的声音下拉：锚在声音格（或过场音乐那一行）下面
    anchor = page.get("sound_path") if page is not None else rows.get(8)
    return {
        "panel": panel,
        "tabs": tab_rects,
        "rows": rows,
        "browse": browse,
        "audio_browse": audio_browse,
        "audio_preview": audio_preview,
        "hint": hint,
        "cutscene": page,
        "apply": apply_rect,
        "cancel": cancel_rect,
        "sound_menu": sound_menu_geometry(editor, anchor, surface.get_rect()),
    }


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


def _draw_settings_text_row(
    surface: pygame.Surface,
    font: pygame.font.Font,
    rect: pygame.Rect,
    text: str,
    selected: bool,
    clip: int,
) -> None:
    """一格可编辑的路径 / 名称：选中时高亮，末尾带光标，长了就截断。"""
    pygame.draw.rect(surface, (62, 62, 72) if selected else (48, 48, 54), rect)
    pygame.draw.rect(surface, HIGHLIGHT if selected else (86, 86, 94), rect, 1)
    label = f"{text}|" if selected else text
    rendered = font.render(label, True, HIGHLIGHT if selected else TEXT)
    surface.blit(
        rendered,
        (rect.left + 6, rect.centery - rendered.get_height() // 2),
        (0, 0, min(rendered.get_width(), max(1, clip)), rendered.get_height()),
    )


def _draw_general_settings(
    surface: pygame.Surface, editor: Editor, font: pygame.font.Font, geometry: dict
) -> None:
    """常规页：名称（即文件名）、宽高、翻转带、背景。"""
    rows = geometry["rows"]
    _draw_settings_text_row(
        surface,
        font,
        rows[0],
        f"名称（即文件名）：{editor.settings['name'] or '（空）'}",
        editor.settings_field == 0,
        rows[0].width - 12,
    )

    # 宽高决定画布大小：游戏里可玩行固定 400px，所以高度越大格子越小
    for field, label, key in (
        (1, "宽度（格）", "width"),
        (2, "高度（格）", "height"),
    ):
        selected = editor.settings_field == field
        _draw_settings_row(surface, font, rows[field], label, editor.settings[key], selected)
        left, right = stepper_rects(rows[field])
        draw_stepper(surface, left, -1)
        draw_stepper(surface, right, 1)

    # 翻转带：玩家整块和带子重叠才翻得动。向上翻贴着关卡顶、向下翻贴着关卡底，
    # 数字是带子的高度，0 表示这一侧翻不了
    for field, label, key in (
        (3, "向上翻转判断范围（距离顶部）", "flip_up"),
        (4, "向下翻转判断范围（距离底部）", "flip_down"),
    ):
        selected = editor.settings_field == field
        _draw_settings_row(surface, font, rows[field], label, editor.settings[key], selected)
        left, right = stepper_rects(rows[field])
        draw_stepper(surface, left, -1)
        draw_stepper(surface, right, 1)

    # 背景：直接敲路径，或点右边「浏览…」挑一张图；存的是相对 game.json 的路径
    _draw_settings_text_row(
        surface,
        font,
        rows[5],
        f"背景：{editor.settings['background'] or '（无）'}",
        editor.settings_field == 5,
        geometry["browse"].left - rows[5].left - 12,
    )
    draw_button(surface, font, geometry["browse"], "浏览…")


def _draw_player_settings(
    surface: pygame.Surface, editor: Editor, font: pygame.font.Font, geometry: dict
) -> None:
    """玩家页：这一关对游戏配置里跳高、速度的覆盖。"""
    surface.blit(
        font.render("留空跟随游戏配置，填了就覆盖本关。", True, DIM_TEXT),
        (geometry["hint"].left, geometry["hint"].top + 2),
    )
    for field, label, key, fallback, unit in (
        (6, "跳高", "jump_height", editor.player_stats()[0], "格"),
        (7, "速度", "move_speed", editor.player_stats()[1], "格/秒"),
    ):
        selected = editor.settings_field == field
        raw = editor.settings[key]
        value = raw if raw else f"跟随（{fallback:g}）"
        _draw_settings_row(
            surface, font, geometry["rows"][field], f"{label}（{unit}）", value, selected
        )
        left, right = stepper_rects(geometry["rows"][field])
        draw_stepper(surface, left, -1)
        draw_stepper(surface, right, 1)


def _draw_level_sound_settings(
    surface: pygame.Surface, editor: Editor, font: pygame.font.Font, geometry: dict
) -> None:
    """声音页：这一关自己的一声 BGM（库里的声音）、循环、淡入淡出。"""
    rows = geometry["rows"]
    _draw_settings_text_row(
        surface,
        font,
        rows[8],
        f"声音：{key_label(editor.sound_library, editor.settings['sound'])}",
        editor.settings_field == 8,
        geometry["audio_browse"].left - rows[8].left - 12,
    )
    draw_button(surface, font, geometry["audio_browse"], "选择…")
    draw_button(surface, font, geometry["audio_preview"], "试听")

    pygame.draw.rect(surface, (48, 48, 54), rows[9])
    pygame.draw.rect(
        surface, HIGHLIGHT if editor.settings_field == 9 else (86, 86, 94), rows[9], 1
    )
    draw_checkbox(
        surface,
        font,
        rows[9],
        "循环播放",
        bool(editor.settings["loop"]),
        editor.settings_field == 9,
        inset=6,
    )

    for field, label, key in ((10, "淡入（秒）", "fade_in"), (11, "淡出（秒）", "fade_out")):
        selected = editor.settings_field == field
        _draw_settings_row(surface, font, rows[field], label, editor.settings[key], selected)
        left, right = stepper_rects(rows[field])
        draw_stepper(surface, left, -1)
        draw_stepper(surface, right, 1)

    for line_index, line in enumerate(
        (
            "「选择…」摊开声音库里的声音；新的音频在游戏配置的「声音库」页导入。",
            "循环关闭只放一遍；没有选声音就是这一关不放音乐。",
        )
    ):
        surface.blit(
            font.render(line, True, DIM_TEXT),
            (geometry["hint"].left, geometry["hint"].top + line_index * 22),
        )


def draw_settings(surface: pygame.Surface, editor: Editor, font: pygame.font.Font) -> None:
    geometry = settings_geometry(surface, editor)
    panel = geometry["panel"]
    draw_panel(surface, panel)

    surface.blit(font.render("关卡设置", True, TEXT), (panel.left + MARGIN, panel.top + 8))
    tip = font.render("Tab 切换分页；点击面板外区域即取消", True, DIM_TEXT)
    surface.blit(tip, (panel.right - MARGIN - tip.get_width(), panel.top + 8))

    # 页签：常规 / 玩家 / 声音 / 过场
    for rect, index in geometry["tabs"]:
        selected = index == editor.settings_tab
        pygame.draw.rect(surface, (80, 80, 90) if selected else BUTTON_BG, rect)
        pygame.draw.rect(surface, HIGHLIGHT if selected else DIALOG_BORDER, rect, 1)
        label = font.render(SETTINGS_TABS[index][0], True, HIGHLIGHT if selected else TEXT)
        surface.blit(
            label,
            (rect.centerx - label.get_width() // 2, rect.centery - label.get_height() // 2),
        )

    if editor.settings_cutscene_tab():
        draw_cutscene_page(surface, editor, font, geometry["cutscene"])
    elif editor.settings_tab == 0:
        _draw_general_settings(surface, editor, font, geometry)
    elif editor.settings_tab == 1:
        _draw_player_settings(surface, editor, font, geometry)
    else:
        _draw_level_sound_settings(surface, editor, font, geometry)

    draw_button(surface, font, geometry["apply"], "应用")
    draw_button(surface, font, geometry["cancel"], "取消")
    draw_sound_menu(surface, editor, font, geometry.get("sound_menu"))


GAME_PANEL_WIDTH = 620
GAME_TAB_TOP = 30               # 标题下面这一行是页签
GAME_CONTENT_TOP = 64           # 页签下面开始排内容
GAME_GENERAL_HEIGHT = 340       # 常规页：标题、玩家参数、两个画面背景、说明
GAME_SOUND_HEIGHT = 380         # 声音页：标题与制作名单两块
GAME_FOOTER_HEIGHT = 74         # 制作名单页：卡片区之后：说明、按钮
CREDIT_CARD_PAD = 6
CREDIT_CARD_GAP = 6
CREDIT_LINE_HEIGHT = ROW_HEIGHT
CREDIT_JOB_WIDTH = 150
CREDIT_ICON = 16                # 名字行尾的「−」和下边「＋」的边长
SCENE_STEP = 112                # 声音页里一块占多高：小标题、路径、循环、淡入淡出


def _credit_card_height(card: dict) -> int:
    """一张制作名单卡片的高度：职位一格、每个名字一行，底下再加一行「＋」。"""
    lines = max(1, len(card["names"]))
    return CREDIT_CARD_PAD * 2 + lines * CREDIT_LINE_HEIGHT + CREDIT_LINE_HEIGHT


def game_settings_geometry(surface: pygame.Surface, editor: Editor) -> dict:
    """游戏配置：常规 / 动画集 / 制作名单 / 声音 / 声音库 / 过场 / 玩家表现七页，底下是应用和取消。

    常规页是标题与玩家参数；动画集页列出 game.json 动画库里的条目（键名 + 一行帧缩略图，
    点一行打开编辑弹窗，见 view.animation）；
    制作名单页每个职位一张卡片，装不下就用滚轮按像素上下滚（滚了多少记在编辑器的
    game_card_scroll 上）；声音页把标题与制作名单两块上下排开，每块是路径、循环和淡入淡出；
    过场页和关卡设置里的是同一页（见 view.cutscene）；玩家表现页放两个按钮，关掉本页
    并选中对象列表里的全局项，真正的编辑在属性面板里做。只有当前页的那些矩形有值。
    """
    tab = editor.game_tab
    cards = editor.game_cards
    if tab == 0:
        height = GAME_GENERAL_HEIGHT
    elif tab == GAME_ANIMATION_TAB:
        # 动画集页有滚动，窗口矮的时候面板跟着矮
        max_height = max(240, surface.get_height() - HEADER - FOOTER - 8)
        height = min(library_page_height(GAME_CONTENT_TOP), max_height)
    elif tab == GAME_SOUND_LIBRARY_TAB:
        # 声音库页也是列表，窗口矮的时候面板跟着矮
        max_height = max(240, surface.get_height() - HEADER - FOOTER - 8)
        height = min(sound_library_height(GAME_CONTENT_TOP), max_height)
    elif tab == 2:                      # 制作名单
        card_heights = [_credit_card_height(card) for card in cards]
        content = sum(card_height + CREDIT_CARD_GAP for card_height in card_heights)
        # 面板最高顶到信息栏下面、状态栏上面，剩下的靠滚轮翻
        max_height = max(360, surface.get_height() - HEADER - FOOTER - 8)
        wanted = GAME_CONTENT_TOP + 26 + max(120, content) + GAME_FOOTER_HEIGHT
        height = min(wanted, max_height)
    elif tab == GAME_CUTSCENE_TAB:
        max_height = max(360, surface.get_height() - HEADER - FOOTER - 8)
        height = min(cutscene_page_height(editor, GAME_CONTENT_TOP), max_height)
    elif tab == GAME_PLAYER_VIEW_TAB:
        height = 250
    else:
        height = GAME_SOUND_HEIGHT
    panel = place_panel(surface, pygame.Rect(0, 0, GAME_PANEL_WIDTH, height))

    tab_rects = []
    x = panel.left + MARGIN
    for index, label in enumerate(GAME_SETTINGS_TABS):
        width = _tab_width(label)
        tab_rects.append((pygame.Rect(x, panel.top + GAME_TAB_TOP, width, TAB_HEIGHT), index))
        x += width + TAB_GAP
    content_top = panel.top + GAME_CONTENT_TOP
    row_width = panel.width - 2 * MARGIN

    button_y = panel.bottom - 12 - BUTTON_HEIGHT
    geometry = {
        "panel": panel,
        "tabs": tab_rects,
        "tab": tab,
        "rows": {},
        "scenes": [],
        "hint": None,
        "cards_area": None,
        "layouts": [],
        "visible": 0,
        "add": None,
        "remove": None,
        "cutscene": None,
        "animation": None,
        "sound_library": None,
        "player_views": None,
        "note_top": content_top,
        "backgrounds": [],
        "apply": pygame.Rect(panel.right - MARGIN - 140, button_y, 68, BUTTON_HEIGHT),
        "cancel": pygame.Rect(panel.right - MARGIN - 68, button_y, 68, BUTTON_HEIGHT),
    }

    if tab == 0:
        rows = geometry["rows"]
        rows["title"] = pygame.Rect(panel.left + MARGIN, content_top, row_width, ROW_HEIGHT + 2)
        rows["player_label"] = pygame.Rect(
            panel.left + MARGIN, content_top + 30, row_width, ROW_HEIGHT
        )
        rows["jump"] = pygame.Rect(
            panel.left + MARGIN, content_top + 52, row_width, ROW_HEIGHT + 2
        )
        rows["speed"] = pygame.Rect(
            panel.left + MARGIN, content_top + 84, row_width, ROW_HEIGHT + 2
        )
        rows["bg_label"] = pygame.Rect(
            panel.left + MARGIN, content_top + 112, row_width, ROW_HEIGHT
        )
        # 标题 / 结算画面的背景：一行一个，右边是「浏览…」
        for index, (key, label) in enumerate((("title", "标题画面"), ("credits", "结算画面"))):
            row = pygame.Rect(
                panel.left + MARGIN,
                content_top + 134 + index * 32,
                row_width,
                ROW_HEIGHT + 2,
            )
            browse = pygame.Rect(row.right - 76, row.top, 76, row.height)
            text = pygame.Rect(row.left, row.top, browse.left - 6 - row.left, row.height)
            geometry["backgrounds"].append(
                {"key": key, "label": label, "text": text, "browse": browse}
            )
        geometry["note_top"] = content_top + 202
    elif tab == GAME_ANIMATION_TAB:
        geometry["animation"] = library_geometry(surface, editor, panel, content_top)
    elif tab == GAME_SOUND_LIBRARY_TAB:
        geometry["sound_library"] = sound_library_geometry(
            surface, editor, panel, content_top
        )
    elif tab == 2:                      # 制作名单
        geometry["section"] = pygame.Rect(
            panel.left + MARGIN, content_top, row_width, ROW_HEIGHT
        )
        cards_top = content_top + 26
        cards_area = pygame.Rect(
            panel.left + MARGIN,
            cards_top,
            row_width,
            max(0, panel.height - (cards_top - panel.top) - GAME_FOOTER_HEIGHT),
        )
        geometry["cards_area"] = cards_area

        # 内容按像素滚动：卡片从 cards_area.top - 滚动量 开始摆，超出内容区的靠绘制时裁剪
        card_heights = [_credit_card_height(card) for card in cards]
        content_height = sum(card_heights) + CREDIT_CARD_GAP * max(0, len(card_heights) - 1)
        scroll = max(
            0.0, min(float(editor.game_card_scroll), max(0.0, content_height - cards_area.height))
        )
        editor.game_card_scroll = scroll
        layouts = []
        y = cards_area.top - round(scroll)
        for index, card_height in enumerate(card_heights):
            card_rect = pygame.Rect(cards_area.left, y, cards_area.width, card_height)
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
                name_rects.append(
                    pygame.Rect(name_left, line_top, name_width, CREDIT_LINE_HEIGHT)
                )
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
                card_rect.top
                + CREDIT_CARD_PAD
                + max(1, len(cards[index]["names"])) * CREDIT_LINE_HEIGHT,
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
            y += card_height + CREDIT_CARD_GAP
        geometry["layouts"] = layouts
        geometry["content_height"] = content_height
        geometry["scroll"] = scroll
        geometry["add"] = pygame.Rect(panel.left + MARGIN, button_y, 110, BUTTON_HEIGHT)
        geometry["remove"] = pygame.Rect(
            geometry["add"].right + 8, button_y, 110, BUTTON_HEIGHT
        )
        geometry["note_top"] = panel.bottom - BUTTON_HEIGHT - 36
    elif tab == GAME_CUTSCENE_TAB:
        geometry["cutscene"] = cutscene_geometry(surface, editor, panel, content_top)
    elif tab == GAME_PLAYER_VIEW_TAB:
        geometry["player_views"] = {
            "title": pygame.Rect(
                panel.left + MARGIN, content_top, row_width, ROW_HEIGHT
            ),
            "animation": pygame.Rect(
                panel.left + MARGIN, content_top + 58, row_width, ROW_HEIGHT + 8
            ),
            "sound": pygame.Rect(
                panel.left + MARGIN, content_top + 104, row_width, ROW_HEIGHT + 8
            ),
        }
    else:
        for scene_index, (key, label) in enumerate(SCENE_KEYS):
            top = content_top + scene_index * SCENE_STEP
            path_row = pygame.Rect(
                panel.left + MARGIN, top + 22, row_width, ROW_HEIGHT + 2
            )
            preview = pygame.Rect(path_row.right - 76, path_row.top, 76, path_row.height)
            browse = pygame.Rect(preview.left - 6 - 76, path_row.top, 76, path_row.height)
            path = pygame.Rect(
                path_row.left, path_row.top, browse.left - 6 - path_row.left, path_row.height
            )
            fade_width = min(260, (row_width - 16) // 2)
            fades_top = top + 78
            geometry["scenes"].append(
                {
                    "key": key,
                    "label": label,
                    "label_top": top,
                    "path": path,
                    "browse": browse,
                    "preview": preview,
                    "loop": pygame.Rect(
                        panel.left + MARGIN, top + 50, 260, ROW_HEIGHT + 2
                    ),
                    "fade_in": pygame.Rect(
                        panel.left + MARGIN, fades_top, fade_width, ROW_HEIGHT + 2
                    ),
                    "fade_out": pygame.Rect(
                        panel.left + MARGIN + fade_width + 16,
                        fades_top,
                        fade_width,
                        ROW_HEIGHT + 2,
                    ),
                }
            )
        geometry["hint"] = pygame.Rect(
            panel.left + MARGIN, content_top + 224, row_width, 44
        )
    # 「选择…」摊开的声音下拉：锚在对应那一行下面
    anchor = None
    if geometry["cutscene"] is not None:
        anchor = geometry["cutscene"].get("sound_path")
    elif tab == 3:
        target = (editor.sound_menu or {}).get("target") or ()
        for scene in geometry["scenes"]:
            if target[:1] == ("game",) and scene["key"] == target[1]:
                anchor = scene["path"]
    geometry["sound_menu"] = sound_menu_geometry(editor, anchor, surface.get_rect())
    return geometry


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


def _cell_selected(editor: Editor, cell: tuple) -> bool:
    """光标是不是停在 game.json 的这一格上。"""
    cells = editor.game_cells()
    return editor.game_field < len(cells) and cells[editor.game_field] == cell


def _draw_game_general(
    surface: pygame.Surface, editor: Editor, font: pygame.font.Font, geometry: dict
) -> None:
    """常规页：标题，以及玩家共用的跳高与速度。"""
    rows = geometry["rows"]
    _draw_cell(
        surface,
        font,
        rows["title"],
        str((editor.game_settings or {}).get("title") or ""),
        _cell_selected(editor, ("title",)),
    )

    surface.blit(
        font.render("玩家（全游戏共用，关卡里的 player 写了就覆盖它）", True, DIM_TEXT),
        (rows["player_label"].left, rows["player_label"].top + 2),
    )
    for key, cell, title, unit in (
        ("jump_height", ("jump",), "跳高", "格"),
        ("move_speed", ("speed",), "速度", "格/秒"),
    ):
        rect = rows["jump" if key == "jump_height" else "speed"]
        selected = _cell_selected(editor, cell)
        pygame.draw.rect(surface, (62, 62, 72) if selected else (48, 48, 54), rect)
        pygame.draw.rect(surface, HIGHLIGHT if selected else (86, 86, 94), rect, 1)
        value = editor.game_numbers.get(key, "")
        caret = "|" if selected else ""
        text = font.render(
            f"{title}（{unit}）：{value}{caret}", True, HIGHLIGHT if selected else TEXT
        )
        clip = max(1, rect.width - 12)
        surface.blit(
            text,
            (rect.left + 6, rect.centery - text.get_height() // 2),
            (0, 0, min(text.get_width(), clip), text.get_height()),
        )
        left, right = stepper_rects(rect)
        draw_stepper(surface, left, -1)
        draw_stepper(surface, right, 1)

    # 标题 / 结算画面的背景：一行一个，右边「浏览…」
    surface.blit(
        font.render("标题 / 结算画面的背景（整屏铺满，等比放大后裁掉多余的边）", True, DIM_TEXT),
        (rows["bg_label"].left, rows["bg_label"].top + 2),
    )
    for background in geometry["backgrounds"]:
        path = editor.game_backgrounds.get(background["key"], "")
        _draw_cell(
            surface,
            font,
            background["text"],
            f"{background['label']}：{path or '（无）'}",
            _cell_selected(editor, (f"{background['key']}_bg",)),
        )
        draw_button(surface, font, background["browse"], "浏览…")

    note = font.render(
        f"{display_path(editor.game_path) if editor.game_path else 'game.json'}："
        "标题用于标题画面和窗口标题，玩家参数用于每一关。",
        True,
        DIM_TEXT,
    )
    surface.blit(note, (geometry["panel"].left + MARGIN, geometry["note_top"]))


def _draw_game_credits(
    surface: pygame.Surface, editor: Editor, font: pygame.font.Font, geometry: dict
) -> None:
    """制作名单页：每个职位一张卡片，左边写职位、右边一行一个名字；多了可以用滚轮上下滚。"""
    cards = editor.game_cards
    cards_area = geometry["cards_area"]
    label = "制作名单（每个职位一张卡片；名字为空也行，一个名字都没有就是空数组）"
    surface.blit(
        font.render(label, True, DIM_TEXT),
        (geometry["section"].left, geometry["section"].top + 2),
    )
    if not cards:
        text = font.render("还没有职位，请点击「添加职位」", True, DIM_TEXT)
        surface.blit(text, (cards_area.left + 6, cards_area.top + 6))
    previous_clip = surface.get_clip()
    surface.set_clip(cards_area)
    for layout in geometry["layouts"]:
        card = cards[layout["index"]]
        pygame.draw.rect(surface, (58, 58, 66), layout["rect"])
        pygame.draw.rect(surface, (110, 110, 120), layout["rect"], 1)
        _draw_cell(
            surface,
            font,
            layout["job"],
            str(card.get("job") or ""),
            _cell_selected(editor, ("job", layout["index"])),
        )
        for line, rect in enumerate(layout["names"]):
            _draw_cell(
                surface,
                font,
                rect,
                str(card["names"][line]),
                _cell_selected(editor, ("name", layout["index"], line)),
            )
            draw_icon_button(surface, layout["minus"][line], "−", font)
        draw_icon_button(surface, layout["plus"], "＋", font)
    surface.set_clip(previous_clip)
    draw_scrollbar(surface, cards_area, geometry["content_height"], geometry["scroll"])

    note = font.render(
        f"{display_path(editor.game_path) if editor.game_path else 'game.json'}："
        "制作名单用于结算画面。",
        True,
        DIM_TEXT,
    )
    surface.blit(note, (cards_area.left, geometry["note_top"]))
    draw_button(surface, font, geometry["add"], "添加职位")
    draw_button(surface, font, geometry["remove"], "删除职位")


def _draw_game_sound(
    surface: pygame.Surface, editor: Editor, font: pygame.font.Font, geometry: dict
) -> None:
    """声音页：标题与制作名单两块，每块是库里的声音、循环和淡入淡出。"""
    for scene in geometry["scenes"]:
        key = scene["key"]
        values = editor.game_sound.get(key, {})
        surface.blit(
            font.render(f"{scene['label']}音乐", True, DIM_TEXT),
            (scene["path"].left, scene["label_top"]),
        )
        _draw_cell(
            surface,
            font,
            scene["path"],
            f"声音：{key_label(editor.sound_library, values.get('sound'))}",
            _cell_selected(editor, ("sound", key)),
        )
        draw_button(surface, font, scene["browse"], "选择…")
        draw_button(surface, font, scene["preview"], "试听")

        selected = _cell_selected(editor, ("loop", key))
        pygame.draw.rect(surface, (48, 48, 54), scene["loop"])
        pygame.draw.rect(
            surface, HIGHLIGHT if selected else (86, 86, 94), scene["loop"], 1
        )
        draw_checkbox(
            surface,
            font,
            scene["loop"],
            "循环播放",
            bool(values.get("loop", True)),
            selected,
            inset=6,
        )

        for field, rect, title in (
            ("fade_in", scene["fade_in"], "淡入（秒）"),
            ("fade_out", scene["fade_out"], "淡出（秒）"),
        ):
            _draw_settings_row(
                surface,
                font,
                rect,
                title,
                values.get(field, ""),
                _cell_selected(editor, (field, key)),
            )
            left, right = stepper_rects(rect)
            draw_stepper(surface, left, -1)
            draw_stepper(surface, right, 1)

    for line_index, line in enumerate(
        (
            "「选择…」摊开声音库里的声音；新的音频在「声音库」页导入。",
            "循环关闭只放一遍；没有选声音的一幕就不写进去。",
        )
    ):
        surface.blit(
            font.render(line, True, DIM_TEXT),
            (geometry["hint"].left, geometry["hint"].top + line_index * 22),
        )


def _draw_game_player_views(
    surface: pygame.Surface, font: pygame.font.Font, geometry: dict
) -> None:
    """玩家表现页：只放两个入口，真正的编辑在右侧属性面板里做，画布不会被挡住。"""
    page = geometry.get("player_views")
    if page is None:
        return
    surface.blit(
        font.render("玩家动画 / 音效由所有关卡共用，编辑在属性面板里进行。", True, TEXT),
        (page["title"].left, page["title"].top),
    )
    draw_button(surface, font, page["animation"], "编辑玩家动画（在属性面板）")
    draw_button(surface, font, page["sound"], "编辑玩家音效（在属性面板）")
    note = font.render("点上面的按钮会关掉本窗口并选中全局项；不会写入关卡。", True, DIM_TEXT)
    surface.blit(note, (page["sound"].left, page["sound"].bottom + 10))


def draw_game_settings(surface: pygame.Surface, editor: Editor, font: pygame.font.Font) -> None:
    geometry = game_settings_geometry(surface, editor)
    panel = geometry["panel"]
    draw_panel(surface, panel)

    surface.blit(font.render("游戏配置", True, TEXT), (panel.left + MARGIN, panel.top + 8))
    hint = font.render("Tab 切换分页；点击面板外区域即取消", True, DIM_TEXT)
    surface.blit(hint, (panel.right - MARGIN - hint.get_width(), panel.top + 8))

    # 页签：常规 / 动画集 / 制作名单 / 声音 / 过场
    for rect, index in geometry["tabs"]:
        selected = index == editor.game_tab
        pygame.draw.rect(surface, (80, 80, 90) if selected else BUTTON_BG, rect)
        pygame.draw.rect(surface, HIGHLIGHT if selected else DIALOG_BORDER, rect, 1)
        label = font.render(GAME_SETTINGS_TABS[index], True, HIGHLIGHT if selected else TEXT)
        surface.blit(
            label,
            (rect.centerx - label.get_width() // 2, rect.centery - label.get_height() // 2),
        )

    if editor.game_cutscene_tab():
        draw_cutscene_page(surface, editor, font, geometry["cutscene"])
    elif editor.game_animation_tab():
        draw_library_page(surface, editor, font, geometry["animation"])
    elif editor.game_sound_library_tab():
        draw_sound_library(surface, editor, font, geometry["sound_library"])
    elif editor.game_tab == GAME_PLAYER_VIEW_TAB:
        _draw_game_player_views(surface, font, geometry)
    elif editor.game_tab == 0:
        _draw_game_general(surface, editor, font, geometry)
    elif editor.game_tab == 2:
        _draw_game_credits(surface, editor, font, geometry)
    else:
        _draw_game_sound(surface, editor, font, geometry)

    draw_button(surface, font, geometry["apply"], "应用")
    draw_button(surface, font, geometry["cancel"], "取消")
    draw_sound_menu(surface, editor, font, geometry.get("sound_menu"))

    # 单条动画的编辑弹窗压在最上面
    if editor.animation_edit is not None:
        from view.animation import draw_animation_edit

        draw_animation_edit(surface, editor, font)


def global_prompt_geometry(surface: pygame.Surface) -> tuple:
    """离开全局玩家表现页时的保存提示：应用 / 放弃 / 取消。"""
    panel = place_panel(surface, pygame.Rect(0, 0, 500, 166))
    button_y = panel.bottom - 12 - BUTTON_HEIGHT
    apply_rect = pygame.Rect(panel.right - 12 - 120, button_y, 120, BUTTON_HEIGHT)
    discard_rect = pygame.Rect(apply_rect.left - 10 - 120, button_y, 120, BUTTON_HEIGHT)
    cancel_rect = pygame.Rect(discard_rect.left - 10 - 76, button_y, 76, BUTTON_HEIGHT)
    return panel, apply_rect, discard_rect, cancel_rect


def draw_global_prompt(surface: pygame.Surface, editor: Editor, font: pygame.font.Font) -> None:
    panel, apply_rect, discard_rect, cancel_rect = global_prompt_geometry(surface)
    draw_panel(surface, panel)
    surface.blit(
        font.render("玩家表现有未应用的修改", True, HIGHLIGHT),
        (panel.left + 14, panel.top + 12),
    )
    surface.blit(
        font.render("玩家动画 / 音效是所有关卡共用的，应用后会写入 game.json。", True, TEXT),
        (panel.left + 14, panel.top + 44),
    )
    hint = font.render("Y / Enter 应用并继续；N 放弃并继续；Esc 取消", True, DIM_TEXT)
    surface.blit(hint, (panel.left + 14, panel.top + 96))
    draw_button(surface, font, apply_rect, "应用并继续")
    draw_button(surface, font, discard_rect, "放弃并继续")
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
