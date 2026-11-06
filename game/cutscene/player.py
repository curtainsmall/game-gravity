"""过场播放：计时、淡入淡出、按住空格跳过，以及画图。

窗口固定，图片按 contain 缩放：整张等比塞进窗口，空出来的地方是黑边。
跳过必须等过场开始后新按下的空格（用按键事件，进过场时本来就按着的不算），
按住 1 秒后 0.2 秒淡出直接结束整段。
"""

import math

import pygame

from cutscene.cutscene import Cutscene

SKIP_SECONDS = 1.0
SKIP_FADE_SECONDS = 0.2
RING_RADIUS = 14
RING_MARGIN = 26
RING_TRACK = (90, 90, 90)
RING_FILL = (240, 240, 240)


class CutscenePlayer:
    def __init__(self, cutscene: Cutscene, window_size: tuple[int, int]) -> None:
        self.cutscene = cutscene
        self.width, self.height = window_size
        self.elapsed = 0.0
        self.paused = False
        self.held = False               # 空格是否按着（只有过场开始后按下的才算）
        self.progress = 0.0             # 按住跳过的进度 0~1
        self.skip_fade = 0.0            # 跳过后的淡出还剩几秒
        self.finished = False
        self.images = [self._load(picture) for picture in cutscene.pictures]

    @property
    def has_pictures(self) -> bool:
        return any(image is not None for image in self.images)

    def _load(self, picture) -> pygame.Surface | None:
        try:
            image = pygame.image.load(picture.path).convert_alpha()
        except (pygame.error, OSError):
            return None
        width, height = image.get_size()
        if width <= 0 or height <= 0:
            return None
        scale = min(self.width / width, self.height / height)
        return pygame.transform.smoothscale(
            image, (max(1, round(width * scale)), max(1, round(height * scale)))
        )

    # ---- 输入 -------------------------------------------------------
    def hold_skip(self) -> None:
        """空格按下：过场开始后的一次按键才算，按住不放不会重复触发。"""
        if not self.paused and self.skip_fade <= 0.0:
            self.held = True

    def release_skip(self) -> None:
        self.held = False
        self.progress = 0.0

    # ---- 每帧 -------------------------------------------------------
    def update(self, elapsed_seconds: float) -> None:
        if self.finished or self.paused:
            return
        if self.skip_fade > 0.0:
            # 跳过后的淡出：画面冻结，黑幕渐深，走完就结束
            self.skip_fade = max(0.0, self.skip_fade - elapsed_seconds)
            if self.skip_fade <= 0.0:
                self.finished = True
            return
        self.elapsed += elapsed_seconds
        if self.held and self.progress < 1.0:
            self.progress = min(1.0, self.progress + elapsed_seconds / SKIP_SECONDS)
            if self.progress >= 1.0:
                self.held = False
                self.progress = 0.0
                self.skip_fade = SKIP_FADE_SECONDS
        if self.elapsed >= self.cutscene.duration:
            self.finished = True

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((0, 0, 0))
        elapsed = min(self.elapsed, self.cutscene.duration)
        for index, image in enumerate(self.images):
            if image is None:
                continue
            alpha = self.cutscene.alpha_at(index, elapsed)
            if alpha <= 0.0:
                continue
            image.set_alpha(round(alpha * 255))
            surface.blit(image, image.get_rect(center=(self.width // 2, self.height // 2)))
        if self.skip_fade > 0.0:
            alpha = round(255 * (1.0 - self.skip_fade / SKIP_FADE_SECONDS))
            overlay = pygame.Surface((self.width, self.height))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(max(0, min(255, alpha)))
            surface.blit(overlay, (0, 0))
            return
        if self.held and self.progress > 0.0:
            self._draw_skip_ring(surface)

    def _draw_skip_ring(self, surface: pygame.Surface) -> None:
        """右下角的圆形进度：按住空格时出现，从顶部顺时针填满。"""
        centre = (self.width - RING_MARGIN, self.height - RING_MARGIN)
        rect = pygame.Rect(0, 0, RING_RADIUS * 2, RING_RADIUS * 2)
        rect.center = centre
        pygame.draw.circle(surface, RING_TRACK, centre, RING_RADIUS, 3)
        start = math.pi / 2 - 2 * math.pi * self.progress
        pygame.draw.arc(surface, RING_FILL, rect, start, math.pi / 2, 3)
