"""物品库：game.json 的 item_library（id → 图标 + 说明图）。

触发源按 id 解锁物品；背包只显示库里有的物品。两张图都只记相对 game.json 的路径，
和贴图、声音库一样，编辑器不复制文件。
"""

import os

LIBRARY_KEY = "item_library"


def library_of(settings: dict) -> dict:
    """game.json → 物品库（id → {"icon": …, "description": …}）；坏条目跳过。"""
    table = (settings or {}).get(LIBRARY_KEY)
    library: dict = {}
    if not isinstance(table, dict):
        return library
    for key, value in table.items():
        if not isinstance(value, dict):
            continue
        name = str(key).strip()
        icon = str(value.get("icon") or "").strip()
        description = str(value.get("description") or "").strip()
        if name and icon and description:
            library[name] = {"icon": icon, "description": description}
    return library


def to_settings(settings: dict, library: dict) -> dict:
    """编辑好的物品库写回 game.json；缺图标或缺说明图的条目丢掉。"""
    table = {}
    for key, value in (library or {}).items():
        name = str(key).strip()
        icon = str((value or {}).get("icon") or "").strip()
        description = str((value or {}).get("description") or "").strip()
        if name and icon and description:
            table[name] = {"icon": icon, "description": description}
    settings[LIBRARY_KEY] = table
    return settings


def key_for(library: dict, icon_path: str) -> str:
    """给一张新图标起 id：先找用同一张图的老条目，否则用文件名，重名加 -2。"""
    icon_path = str(icon_path or "").strip()
    for key, entry in (library or {}).items():
        if str((entry or {}).get("icon") or "").strip() == icon_path:
            return key
    stem = os.path.splitext(os.path.basename(icon_path))[0].strip() or "物品"
    key = stem
    index = 2
    while key in library:
        key = f"{stem}-{index}"
        index += 1
    return key


def label(library: dict, key: str) -> str:
    """属性面板和下拉里显示什么：id 加图标文件名；没有就是（无）。"""
    key = str(key or "").strip()
    if not key:
        return "（无）"
    entry = (library or {}).get(key) or {}
    icon = os.path.basename(str(entry.get("icon") or "").strip())
    stem = os.path.splitext(icon)[0]
    return f"{key}（{icon}）" if icon and stem != key else key


def references_in(definition: dict, key: str) -> bool:
    """一份关卡数据里有没有触发源引用这个物品。"""
    key = str(key or "").strip()
    if not key or not isinstance(definition, dict):
        return False
    sources = definition.get("trigger_sources")
    if not isinstance(sources, list):
        return False
    return any(
        isinstance(source, dict) and str(source.get("item") or "").strip() == key
        for source in sources
    )
