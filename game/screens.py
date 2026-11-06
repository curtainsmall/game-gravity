"""各个界面的绘制：标题、选关、结算，以及暂停与设置浮层。"""

import pygame

import debug_display
import ui
from levels import level_preview


def draw_title(surface: pygame.Surface, app) -> None:
    surface.fill(ui.BACKGROUND)
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


def draw_ending(surface: pygame.Surface, app) -> None:
    surface.fill(ui.BACKGROUND)
    width, height = surface.get_size()
    ui.draw_text(surface, "感谢您的游玩", 46, center=(width // 2, int(height * 0.16)))
    ui.draw_text(
        surface, "您已通过全部关卡", 20, center=(width // 2, int(height * 0.25)), color=ui.DIM_TEXT
    )
    # 版权信息来自 game.json：职位在左边（右对齐），名字在右边（左对齐）
    for index, (job, names) in enumerate(app.credits.items()):
        y = int(height * 0.36) + index * 30
        _draw_credits_row(surface, width, y, job, names)

    rects = ui.ending_rects(surface)
    ui.draw_button(surface, rects["title"], "返回标题界面")
    ui.draw_button(surface, rects["quit"], "退出")


def _draw_credits_row(
    surface: pygame.Surface, width: int, y: int, job: str, names: list[str]
) -> None:
    """一行版权：职位（暗色）贴着中线右侧结束，名字从另一侧开始。"""
    label = ui.font(18).render(job, True, ui.DIM_TEXT)
    surface.blit(label, (width // 2 - 24 - label.get_width(), y - label.get_height() // 2))
    text = ui.font(18).render(", ".join(names), True, ui.TEXT)
    surface.blit(text, (width // 2 + 24, y - text.get_height() // 2))


def draw_pause(surface: pygame.Surface) -> None:
    ui.draw_shade(surface)
    rects = ui.pause_rects(surface)
    ui.draw_panel(surface, rects["panel"])
    ui.draw_text(surface, "游戏已暂停", 30, center=(rects["panel"].centerx, rects["panel"].top + 42))
    ui.draw_button(surface, rects["resume"], "继续游戏")
    ui.draw_button(surface, rects["restart"], "重新开始")
    ui.draw_button(surface, rects["settings"], "设置")
    ui.draw_button(surface, rects["title"], "返回标题界面")


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

    row = rects["debug"]
    hovered = row.collidepoint(pygame.mouse.get_pos())
    if hovered:
        pygame.draw.rect(surface, (245, 245, 245), row)
    box = pygame.Rect(row.left + 6, row.centery - 8, 16, 16)
    pygame.draw.rect(surface, ui.BUTTON_HOVER if app.debug else ui.BUTTON, box)
    pygame.draw.rect(surface, ui.BORDER, box, 2)
    if app.debug:
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
        "调试显示（占位几何体 + 翻转带）",
        18,
        pos=(box.right + 10, row.centery - 11),
        color=ui.TEXT if app.debug else ui.DIM_TEXT,
    )

    ui.draw_button(surface, rects["back"], "返回")
