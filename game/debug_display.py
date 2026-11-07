"""调试显示：设置里的开关，控制画不画占位几何体和翻转带。

关卡里的对象现在只画占位几何（方块是块黑的、按钮是棱台……），正式发布时这些位置
都会被贴图盖住，所以默认不画。勾上就在所有对象的位置画出它们的占位几何体，贴图和
背景本来就是美术，任何时候都照画。翻转带的红/蓝斜纹跟着这个开关一起出现。
玩家的占位框有自己单独的一个开关：不管整体调试显示开没开，只跟着它自己那一项。
这个开关打开时，左上角还顺带报出玩家当前的跳高（触发源按下期间会被加减）。
"""

import pygame

import ui

# 翻转带：向上翻贴顶画红、向下翻贴底画蓝
FLIP_UP_COLOR = (235, 70, 70, 70)
FLIP_DOWN_COLOR = (70, 120, 235, 70)

# 玩家调试：占位框是橙色的，左上角那行跳高也用同一个橙色
PLAYER_DEBUG_COLOR = (255, 140, 0)
PLAYER_DEBUG_SHADE = (20, 20, 20, 160)
PLAYER_DEBUG_MARGIN = 16
PLAYER_DEBUG_FONT_SIZE = 20


def draw_player_debug(surface: pygame.Surface, jump_height: float) -> None:
    """左上角报当前跳高（格）：垫一层半透明底，压在什么背景上都看得清。"""
    label = ui.font(PLAYER_DEBUG_FONT_SIZE).render(
        f"跳高：{jump_height:g} 格", True, PLAYER_DEBUG_COLOR
    )
    rect = label.get_rect(topleft=(PLAYER_DEBUG_MARGIN, PLAYER_DEBUG_MARGIN))
    shade = pygame.Surface((rect.width + 16, rect.height + 8), pygame.SRCALPHA)
    shade.fill(PLAYER_DEBUG_SHADE)
    surface.blit(shade, (rect.left - 8, rect.top - 4))
    surface.blit(label, rect)
