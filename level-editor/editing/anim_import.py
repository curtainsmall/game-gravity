"""动画帧的导入：一张图片一帧；GIF 拆成同名文件夹里的一串 PNG。

选中的是 GIF 时，在它旁边建一个和它同名的文件夹（去掉 .gif），把每一帧写成
01.png、02.png……每帧的停留时长取 GIF 自己的帧间隔（pygame 给的是毫秒，换算成秒）；
GIF 自带的循环信息不用，循环开关在页面上单独调。
"""

from pathlib import Path

import pygame

from core.animation import DEFAULT_HOLD, MAX_HOLD, MIN_HOLD
from core.helpers import clamp_float, relative_level_path


class AnimationImportError(Exception):
    """导入动画帧失败：消息直接给状态栏用。"""


def import_animation_frames(path: str, base_dir: str | None) -> tuple[list, list | None]:
    """图片路径 → (帧路径列表, 每帧时长列表或 None)。

    None 表示单张图片：只有一帧，时长由调用方决定（默认沿用上一帧）。GIF 返回的时长
    已经夹在 0.01–10 秒之间。
    """
    source = Path(path)
    if source.suffix.lower() == ".gif":
        return _split_gif(source, base_dir)
    if not source.is_file():
        raise AnimationImportError("找不到这张图片。")
    return [relative_level_path(str(source), base_dir)], None


def _split_gif(source: Path, base_dir: str | None) -> tuple[list, list]:
    """GIF → 同名文件夹里的 01.png、02.png…；每帧时长取 GIF 自己的帧间隔（毫秒）。"""
    try:
        frames = pygame.image.load_animation(str(source))
    except (pygame.error, OSError) as error:
        raise AnimationImportError(f"这个 GIF 读不出来：{error}") from error
    if not frames:
        raise AnimationImportError("这个 GIF 里没有帧。")
    folder = source.with_suffix("")
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise AnimationImportError(f"建不了文件夹 {folder.name}：{error}") from error

    paths = []
    holds = []
    for index, (surface, delay) in enumerate(frames, start=1):
        target = folder / f"{index:02d}.png"
        try:
            pygame.image.save(surface, str(target))
        except (pygame.error, OSError) as error:
            raise AnimationImportError(f"第 {index} 帧存不下来：{error}") from error
        paths.append(relative_level_path(str(target), base_dir))
        holds.append(clamp_float(delay / 1000.0, MIN_HOLD, MAX_HOLD, DEFAULT_HOLD))
    return paths, holds
