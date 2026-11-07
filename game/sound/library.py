"""声音库：game.json 里 sound_library 的「键 → 文件」。

一条声音只有一个字段：path，和别的图片、音频路径一样相对 game.json 所在的文件夹。
名字就是键，链接（音乐或声音对象）用键引用它；找不到键、文件不在了都只是没有声音。
"""

from pathlib import Path

LIBRARY_KEY = "sound_library"


def library_sounds(
    game_settings: dict | None, base_dir: str | Path | None
) -> dict[str, str]:
    """game.json 的声音库 → 键 → 绝对路径；空表、坏条目、找不到文件都跳过。"""
    table = (game_settings or {}).get(LIBRARY_KEY)
    sounds: dict[str, str] = {}
    if not isinstance(table, dict):
        return sounds
    for key, value in table.items():
        name = str(key).strip()
        if not name:
            continue
        path = _resolve(value, base_dir)
        if path is not None:
            sounds[name] = path
    return sounds


def _resolve(value, base_dir: str | Path | None) -> str | None:
    """一条声音的路径：条目是 {"path": …}（也认直接写路径字符串的老写法）。"""
    if isinstance(value, dict):
        value = value.get("path")
    if not value:
        return None
    path = Path(str(value))
    if not path.is_absolute():
        if base_dir is None:
            return None
        path = Path(base_dir) / path
    path = path.resolve()
    return str(path) if path.is_file() else None
