"""动画库：game.json 里 animation_library 的「键 → 剪辑」。

一条动画只有帧、每帧停留秒数、循环；它不认识左右，也不认识预设——左右和预设
是动画对象自己的事（见 animation.sprite）。键就是编辑器里显示的名字，动画对象
的链接用键引用这里的剪辑；找不到键、帧文件缺失都只是没有这一段动画。
"""

from pathlib import Path

from animation.clip import AnimationClip

LIBRARY_KEY = "animation_library"


def library_animations(
    game_settings: dict | None, base_dir: str | Path | None
) -> dict[str, AnimationClip]:
    """game.json 的动画库 → 键 → 剪辑；空表、坏条目、一帧都找不到的动画都跳过。"""
    table = (game_settings or {}).get(LIBRARY_KEY)
    clips: dict[str, AnimationClip] = {}
    if not isinstance(table, dict):
        return clips
    for key, value in table.items():
        if not isinstance(value, dict):
            continue
        frames = []
        for frame in value.get("frames") or []:
            path = _resolve(frame, base_dir)
            if path is not None:
                frames.append(path)
        if not frames:
            continue
        clips[str(key)] = AnimationClip(
            frames, value.get("holds"), bool(value.get("loop", True))
        )
    return clips


def _resolve(value, base_dir: str | Path | None) -> str | None:
    """帧图片的绝对路径：相对 game.json；没有兜底，找不到就当没有这一帧。"""
    if not value:
        return None
    path = Path(str(value))
    if not path.is_absolute() and base_dir is not None:
        path = Path(base_dir) / path
    return str(path) if path.is_file() else None
