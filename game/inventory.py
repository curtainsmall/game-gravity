"""背包：本次运行里捡到的物品，只记 id，不写任何文件。

物品本身（图标和说明图）在 game.json 的 item_library 里；这里只负责顺序和去重。
换关、重开都保留，回到标题就清空——和游戏“不存档”的设定一致。
"""

from pathlib import Path

from game_settings import item_library_of


class Inventory:
    def __init__(self) -> None:
        self._items: list[str] = []
        self._seen: set[str] = set()

    def unlock(self, item_id: str) -> bool:
        """解锁一件物品；已经有的返回 False，不重复加。"""
        key = str(item_id or "").strip()
        if not key or key in self._seen:
            return False
        self._seen.add(key)
        self._items.append(key)
        return True

    def clear(self) -> None:
        self._items.clear()
        self._seen.clear()

    def items(self) -> list[str]:
        return list(self._items)

    def __len__(self) -> int:
        return len(self._items)


def item_pictures(settings: dict, base_dir: str | Path | None) -> dict[str, dict[str, str]]:
    """物品库 → id → 图标/说明图的绝对路径；文件在不在不在这里判断。"""
    root = Path(base_dir) if base_dir is not None else Path(".")
    result: dict[str, dict[str, str]] = {}
    for key, entry in item_library_of(settings).items():
        result[key] = {
            "icon": str(root / entry["icon"]),
            "description": str(root / entry["description"]),
        }
    return result
