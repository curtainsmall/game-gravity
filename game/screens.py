"""各个界面的绘制：标题、选关、结算，以及暂停与设置浮层。"""

import pygame

import debug_display
import ui
import window
from levels import level_preview
from renderer.texture import image_size, load_scaled


def _draw_screen_background(surface: pygame.Surface, path: str | None) -> None:
    """整屏背景：等比放大到盖住窗口、居中，超出窗口的部分裁掉；没图就只铺底色。"""
    surface.fill(ui.BACKGROUND)
    if path is None:
        return
    original = image_size(path)
    if original is None or original[0] <= 0 or original[1] <= 0:
        return
    width, height = surface.get_size()
    scale = max(width / original[0], height / original[1])
    size = (max(1, round(original[0] * scale)), max(1, round(original[1] * scale)))
    image = load_scaled(path, size, True)
    if image is None:
        return
    surface.blit(image, image.get_rect(center=(width // 2, height // 2)))


def draw_title(surface: pygame.Surface, app) -> None:
    _draw_screen_background(surface, app.title_background)
    width, height = surface.get_size()
    # 标题来自 game.json
    ui.draw_text(surface, app.title, 64, center=(width // 2, int(height * 0.22)))
    if not app.levels:
        ui.draw_text(
            surface,
            "game/levels/ 目录中暂无可用的关卡",
            18,
            center=(width // 2, int(height * 0.32)),
            color=ui.DIM_TEXT,
        )
    rects = ui.title_rects(surface)
    ui.draw_button(surface, rects["start"], "开始游戏")
    ui.draw_button(surface, rects["levels"], "选择关卡")
    ui.draw_button(surface, rects["quit"], "退出")

    gear = rects["settings"]
    pygame.draw.rect(surface, ui.BUTTON, gear)
    pygame.draw.rect(surface, ui.BORDER, gear, 2)
    ui.draw_gear(surface, gear.inflate(-16, -16))


def draw_level_select(surface: pygame.Surface, app) -> None:
    surface.fill(ui.BACKGROUND)
    width, _ = surface.get_size()
    ui.draw_text(surface, "选择关卡", 34, center=(width // 2, 44))
    ui.draw_button(surface, ui.back_rect(surface), "返回", 18)

    area = ui.level_view_area(surface)
    if not app.levels:
        ui.draw_text(
            surface, "game/levels/ 目录中暂无可用的关卡", 18, center=area.center, color=ui.DIM_TEXT
        )
        return

    previous_clip = surface.get_clip()
    surface.set_clip(area)
    for index, entry in enumerate(app.levels):
        rect = ui.level_row_rect(surface, index, app.level_scroll)
        if rect.bottom <= area.top or rect.top >= area.bottom:
            continue
        pygame.draw.rect(surface, ui.PANEL, rect)
        preview = level_preview(entry, (rect.width - 4, rect.height - 4))
        if preview is not None:
            surface.blit(preview, (rect.left + 2, rect.top + 2))
        pygame.draw.rect(surface, ui.BORDER, rect, 2)

        label = ui.font(20).render(entry.name, True, ui.TEXT)
        badge = pygame.Rect(
            rect.left + 10, rect.top + 10, label.get_width() + 18, label.get_height() + 10
        )
        pygame.draw.rect(surface, ui.BUTTON, badge)
        pygame.draw.rect(surface, ui.BORDER, badge, 1)
        surface.blit(label, (badge.left + 9, badge.top + 5))
        if not entry.playable:
            _fade_row(surface, rect, badge, entry)
    surface.set_clip(previous_clip)

    if ui.max_level_scroll(surface, len(app.levels)):
        hint = ui.font(16).render("可使用滚轮滚动列表", True, ui.DIM_TEXT)
        surface.blit(hint, (area.right - hint.get_width(), area.bottom + 6))


def _fade_row(surface: pygame.Surface, rect: pygame.Rect, badge: pygame.Rect, entry) -> None:
    """没有起点或终点的关卡：整行压一层半透明白，再标一句「缺少起点或终点」。"""
    layer = pygame.Surface(rect.size, pygame.SRCALPHA)
    layer.fill((*ui.BACKGROUND, 170))
    surface.blit(layer, rect.topleft)
    note = ui.font(16).render("缺少起点或终点，不参与通关", True, ui.DIM_TEXT)
    surface.blit(note, (badge.right + 12, badge.centery - note.get_height() // 2))


# 结算画面的制作名单：一行为一个名字，一个职位的第一行带职位名。
# 名单用满标题下面的整块区域，不给按钮留位置；名单放完以后按钮才出现在正中间。
CREDITS_LINE_HEIGHT = 28
CREDITS_PAGE_ROWS = 12         # 一页放几行（标题下方到窗口底部）；放不下的分页
CREDITS_TOP_RATIO = 0.32       # 名单第一行的位置（窗口高度的比例）
CREDITS_DOTS_BOTTOM = 22       # 页码小点离窗口底部多远
CREDITS_FADE_IN = 0.25         # 每页淡入多久
CREDITS_FADE_OUT = 0.2         # 翻到下一页之前淡出多久
CREDITS_HOLD = 3.0             # 一页停多久再自动翻页
CREDITS_PAGE_SECONDS = CREDITS_FADE_IN + CREDITS_HOLD + CREDITS_FADE_OUT


def credits_lines(credits: dict) -> list:
    """制作名单 → 行：职位和它的第一个名字同一行，后面的名字各占一行。"""
    lines = []
    for job, names in credits.items():
        if not names:
            lines.append((job, ""))
            continue
        lines.append((job, names[0]))
        lines.extend((None, name) for name in names[1:])
    return lines


def credits_pages(credits: dict) -> list:
    """按一页 CREDITS_PAGE_ROWS 行切页；没有名单也留一页（只是空白）。

    一页如果从某个职位的续行开始，就把职位名再写一次，免得翻开新页只看到一排名字。
    """
    lines = credits_lines(credits)
    pages = [
        lines[index : index + CREDITS_PAGE_ROWS]
        for index in range(0, len(lines), CREDITS_PAGE_ROWS)
    ]
    job = None
    for page in pages:
        if page and page[0][0] is None and job:
            page[0] = (job, page[0][1])
        for line in page:
            if line[0]:
                job = line[0]
    return pages or [[]]


def credits_alpha(elapsed: float) -> int:
    """这一页当前的透明度：开头淡入，停一会儿，最后淡出交给结束画面。"""
    if elapsed < CREDITS_FADE_IN:
        return round(255 * max(0.0, elapsed) / CREDITS_FADE_IN)
    hold_end = CREDITS_FADE_IN + CREDITS_HOLD
    if elapsed > hold_end:
        fade = min(1.0, (elapsed - hold_end) / CREDITS_FADE_OUT)
        return round(255 * (1.0 - fade))
    return 255


def credits_done(app) -> bool:
    """名单是不是放完了：最后一页也淡出完了，该换成按钮了。没有名单就直接算完。"""
    if not credits_lines(app.credits):
        return True
    last = len(credits_pages(app.credits)) - 1
    return app.credits_page >= last and app.credits_elapsed >= CREDITS_PAGE_SECONDS


def _draw_credits_dots(surface: pygame.Surface, width: int, height: int, count: int, current: int) -> None:
    """页数进度：走到第几页就把前几个点填实。"""
    if count <= 1:
        return
    radius = 4
    step = 18
    left = width // 2 - (count - 1) * step // 2
    y = height - CREDITS_DOTS_BOTTOM
    for index in range(count):
        color = ui.TEXT if index <= current else ui.BORDER
        pygame.draw.circle(surface, color, (left + index * step, y), radius)


def draw_ending(surface: pygame.Surface, app) -> None:
    _draw_screen_background(surface, app.credits_background)
    width, height = surface.get_size()
    ui.draw_text(surface, "感谢您的游玩", 46, center=(width // 2, int(height * 0.16)))
    ui.draw_text(
        surface, "您已通过全部关卡", 20, center=(width // 2, int(height * 0.25)), color=ui.DIM_TEXT
    )

    if credits_done(app):
        # 名单放完了：没有名字，按钮出现在画面正中间
        rects = ui.ending_rects(surface)
        ui.draw_button(surface, rects["title"], "返回标题界面")
        ui.draw_button(surface, rects["quit"], "退出")
        return

    # 制作名单来自 game.json：一行为一个名字，职位和第一个名字同一行。
    # 横向还是「职位 | 名字」两栏，纵向用满标题下面到窗口底部的整块区域
    pages = credits_pages(app.credits)
    page = max(0, min(app.credits_page, len(pages) - 1))
    lines = pages[page]
    if lines:
        layer = pygame.Surface((width, height), pygame.SRCALPHA)
        top = int(height * CREDITS_TOP_RATIO)
        for index, (job, name) in enumerate(lines):
            y = top + index * CREDITS_LINE_HEIGHT
            if job:
                label = ui.font(18).render(job, True, ui.DIM_TEXT)
                layer.blit(
                    label,
                    (width // 2 - 24 - label.get_width(), y - label.get_height() // 2),
                )
            if name:
                text = ui.font(18).render(name, True, ui.TEXT)
                layer.blit(text, (width // 2 + 24, y - text.get_height() // 2))
        layer.set_alpha(credits_alpha(app.credits_elapsed))
        surface.blit(layer, (0, 0))

    _draw_credits_dots(surface, width, height, len(pages), page)


def draw_pause(surface: pygame.Surface) -> None:
    ui.draw_shade(surface)
    rects = ui.pause_rects(surface)
    ui.draw_panel(surface, rects["panel"])
    ui.draw_text(surface, "游戏已暂停", 30, center=(rects["panel"].centerx, rects["panel"].top + 42))
    ui.draw_button(surface, rects["resume"], "继续游戏")
    ui.draw_button(surface, rects["restart"], "重新开始")
    ui.draw_button(surface, rects["settings"], "设置")
    ui.draw_button(surface, rects["title"], "返回标题界面")


def draw_cutscene_pause(surface: pygame.Surface) -> None:
    """过场的暂停浮层：没有「重新开始」，音乐不跟着停。"""
    ui.draw_shade(surface)
    rects = ui.cutscene_pause_rects(surface)
    ui.draw_panel(surface, rects["panel"])
    ui.draw_text(surface, "游戏已暂停", 30, center=(rects["panel"].centerx, rects["panel"].top + 42))
    ui.draw_button(surface, rects["resume"], "继续游戏")
    ui.draw_button(surface, rects["settings"], "设置")
    ui.draw_button(surface, rects["title"], "返回标题界面")


def _draw_check_row(surface: pygame.Surface, rect: pygame.Rect, checked: bool, label: str) -> None:
    """设置里的一个复选框行：整行都能点，勾上时在方框里画个勾。"""
    if rect.collidepoint(window.mouse_pos()):
        pygame.draw.rect(surface, (245, 245, 245), rect)
    box = pygame.Rect(rect.left + 6, rect.centery - 8, 16, 16)
    pygame.draw.rect(surface, ui.BUTTON_HOVER if checked else ui.BUTTON, box)
    pygame.draw.rect(surface, ui.BORDER, box, 2)
    if checked:
        pygame.draw.lines(
            surface,
            ui.TEXT,
            False,
            [
                (box.left + 3, box.centery),
                (box.centerx, box.bottom - 4),
                (box.right - 3, box.top + 4),
            ],
            2,
        )
    ui.draw_text(
        surface,
        label,
        18,
        pos=(box.right + 10, rect.centery - 11),
        color=ui.TEXT if checked else ui.DIM_TEXT,
    )


def draw_settings(surface: pygame.Surface, app) -> None:
    ui.draw_shade(surface)
    rects = ui.settings_rects(surface)
    panel = rects["panel"]
    ui.draw_panel(surface, panel)
    ui.draw_text(surface, "设置", 30, center=(panel.centerx, panel.top + 40))

    # 音量：总音量乘在音乐和音效上，改一下立刻生效，同时写进 .game/setting.json
    surface.blit(ui.font(18).render("音量", True, ui.DIM_TEXT), (panel.left + 24, panel.top + 64))
    saved = ui.font(16).render("保存到程序旁边的 .game/setting.json", True, ui.DIM_TEXT)
    surface.blit(saved, (panel.right - 24 - saved.get_width(), panel.top + 66))
    for key, row in rects["volume"].items():
        amount = app.sound.volume.get(key, 1.0)
        ui.draw_text(
            surface, ui.VOLUME_LABELS[key], 18, pos=(row["row"].left, row["row"].centery - 11)
        )
        track = row["track"]
        pygame.draw.rect(surface, (210, 210, 210), track)
        filled = pygame.Rect(track.left, track.top, int(track.width * amount), track.height)
        pygame.draw.rect(surface, (120, 150, 190), filled)
        pygame.draw.rect(surface, ui.BORDER, track, 1)
        pygame.draw.rect(
            surface, ui.TEXT, pygame.Rect(filled.right - 1, track.top - 4, 3, track.height + 8)
        )
        ui.draw_button(surface, row["minus"], "−", 18)
        ui.draw_button(surface, row["plus"], "＋", 18)
        ui.draw_text(surface, f"{round(amount * 100)}%", 18, center=row["value"].center)

    # 两个开关：整体调试显示（其他机关 + 翻转带）和只管玩家的调试显示
    _draw_check_row(surface, rects["debug"], app.debug, "调试显示（占位几何体 + 翻转带）")
    _draw_check_row(
        surface, rects["player_debug"], app.player_debug, "玩家调试显示（橙色占位框）"
    )

    ui.draw_button(surface, rects["back"], "返回")


def _fit_picture(path: str, box: pygame.Rect) -> pygame.Surface | None:
    """把一张图按比例缩进 box，居中留白；不拉伸。"""
    original = image_size(path)
    if original is None or original[0] <= 0 or original[1] <= 0:
        return None
    scale = min(box.width / original[0], box.height / original[1])
    size = (max(1, round(original[0] * scale)), max(1, round(original[1] * scale)))
    return load_scaled(path, size, True)


def _draw_backpack_zoom(surface: pygame.Surface, path: str) -> None:
    """说明图放大：几乎铺满整屏，点击或 Esc 回背包。"""
    screen = surface.get_rect()
    box = screen.inflate(-48, -72)
    pygame.draw.rect(surface, (24, 24, 28), box)
    pygame.draw.rect(surface, (90, 90, 100), box, 2)
    picture = _fit_picture(path, box.inflate(-8, -8))
    if picture is not None:
        surface.blit(picture, picture.get_rect(center=box.center))
    else:
        ui.draw_text(
            surface, "说明图找不到了", 20, center=box.center, color=(230, 230, 230)
        )
    hint = ui.font(16).render("点击 / Esc / B 返回背包", True, (235, 235, 235))
    bar = pygame.Rect(0, 0, hint.get_width() + 28, hint.get_height() + 12)
    bar.center = (screen.centerx, screen.bottom - 30)
    pygame.draw.rect(surface, (35, 35, 40), bar)
    surface.blit(hint, (bar.left + 14, bar.top + 6))


def draw_backpack(surface: pygame.Surface, app) -> None:
    """B 背包：已捡到的物品图标和选中物品的说明图，纯展示。"""
    ui.draw_shade(surface)
    items = [item_id for item_id in app.inventory.items() if item_id in app.item_library]
    count = len(items)
    slots_per_page = ui.BACKPACK_COLUMNS * ui.BACKPACK_ROWS
    page_count = max(1, (count + slots_per_page - 1) // slots_per_page)
    page = max(0, min(app.backpack_page, page_count - 1))
    app.backpack_page = page
    selected = min(max(app.backpack_selected, 0), count - 1) if count else -1
    app.backpack_selected = selected
    if app.backpack_zoom and selected >= 0:
        _draw_backpack_zoom(surface, app.item_library[items[selected]]["description"])
        return
    geometry = ui.backpack_rects(surface, count, page, selected)
    panel = geometry["panel"]
    ui.draw_panel(surface, panel)
    ui.draw_text(
        surface, "背包", 30, pos=(geometry["title"].left, geometry["title"].top)
    )
    ui.draw_text(
        surface, "B / Esc 关闭", 18, pos=(geometry["hint"].left, geometry["hint"].top),
        color=ui.DIM_TEXT,
    )
    pygame.draw.line(
        surface,
        ui.BORDER,
        (panel.left + ui.BACKPACK_MARGIN, panel.top + 58),
        (panel.right - ui.BACKPACK_MARGIN, panel.top + 58),
    )

    mouse = window.mouse_pos()
    for slot in geometry["slots"]:
        rect = slot["rect"]
        index = slot["index"]
        hovered = slot["filled"] and rect.collidepoint(mouse)
        pygame.draw.rect(surface, (245, 240, 210) if hovered else (235, 235, 235), rect)
        pygame.draw.rect(
            surface,
            (200, 160, 40) if index == selected else ui.BORDER,
            rect,
            3 if index == selected else 1,
        )
        if not slot["filled"]:
            continue
        item_id = items[index]
        icon_box = rect.inflate(-16, -16)
        picture = _fit_picture(app.item_library[item_id]["icon"], icon_box)
        if picture is not None:
            surface.blit(picture, picture.get_rect(center=rect.center))
        else:
            ui.draw_text(surface, "缺图", 14, center=rect.center, color=ui.DIM_TEXT)

    detail = geometry["detail"]
    pygame.draw.rect(surface, (230, 230, 230), detail)
    pygame.draw.rect(surface, ui.BORDER, detail, 1)
    if count == 0:
        ui.draw_text(surface, "还没有捡到东西", 20, center=detail.center, color=ui.DIM_TEXT)
    elif selected >= 0:
        picture = _fit_picture(
            app.item_library[items[selected]]["description"], detail.inflate(-16, -16)
        )
        if picture is not None:
            surface.blit(picture, picture.get_rect(center=detail.center))
        else:
            ui.draw_text(surface, "说明图找不到了", 16, center=detail.center, color=ui.DIM_TEXT)
        ui.draw_text(
            surface,
            "点击放大",
            14,
            center=(detail.centerx, detail.bottom - 16),
            color=ui.DIM_TEXT,
        )

    footer = geometry["footer"]
    ui.draw_text(
        surface,
        "点击图标选择 · 点说明图放大 · 滚轮翻页",
        16,
        pos=(footer.left, footer.top),
        color=ui.DIM_TEXT,
    )
    if count:
        page_text = f"第 {page + 1} / {page_count} 页"
        rendered = ui.font(16).render(page_text, True, ui.DIM_TEXT)
        surface.blit(
            rendered,
            (
                panel.right - ui.BACKPACK_MARGIN - rendered.get_width(),
                footer.top,
            ),
        )
