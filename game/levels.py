"""关卡清单：game/levels/ 下每个 <关卡名>.json 是一关，按文件名排字母序。

关卡名就是文件名（不含 .json）；图片等资源放在项目里任何地方，路径相对 game.json。
没有起点（player）或没有终点（destination）的关卡不算可玩：选关里照样列出来，
但是半透明显示，开局和过关都会跳过它。
"""

import json
from dataclasses import dataclass
from pathlib import Path

import pygame

from game_settings import LEVELS_DIR
from renderer.render_system import RenderSystem
from renderer.viewport import ViewMode
from scenes.scene import Scene

SCENE_SUFFIX = ".json"


@dataclass(frozen=True)
class LevelEntry:
    path: Path
    name: str                  # 文件名去掉 .json
    playable: bool = True      # 起点和终点都在才算可玩


def definition_is_playable(definition: dict) -> bool:
    """有起点也有终点才算能玩的一关。"""
    player = definition.get("player")
    destination = definition.get("destination")
    return isinstance(player, dict) and isinstance(destination, dict)


def read_definition(path: str | Path) -> dict | None:
    """读关卡 json；读不出来返回 None。"""
    try:
        with open(path, encoding="utf-8") as file:
            value = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def discover_levels() -> list[LevelEntry]:
    """扫 levels/ 下的 .json，按文件名不分大小写排字母序。"""
    if not LEVELS_DIR.is_dir():
        return []
    entries = []
    for path in LEVELS_DIR.iterdir():
        if not path.is_file() or path.suffix.lower() != SCENE_SUFFIX:
            continue
        definition = read_definition(path)
        playable = definition is not None and definition_is_playable(definition)
        entries.append(LevelEntry(path=path, name=path.stem, playable=playable))
    return sorted(entries, key=lambda entry: entry.name.lower())


def load_scene(entry: LevelEntry) -> Scene | None:
    try:
        return Scene.from_level_file(str(entry.path))
    except (OSError, ValueError):
        return None


_PREVIEWS: dict[tuple[str, int, int], pygame.Surface | None] = {}

PREVIEW_BACKGROUND = (255, 255, 255)
PREVIEW_BAND_BACKGROUND = (235, 235, 235)


def level_preview(entry: LevelEntry, size: tuple[int, int]) -> pygame.Surface | None:
    """整关缩略图：横竖都塞进给定尺寸，居中留白，按尺寸缓存。"""
    if size[0] <= 0 or size[1] <= 0:
        return None
    key = (str(entry.path), size[0], size[1])
    if key in _PREVIEWS:
        return _PREVIEWS[key]
    scene = load_scene(entry)
    if scene is None or scene.world is None:
        _PREVIEWS[key] = None
        return None

    world = scene.world
    rows = world.height_in_blocks + 2          # 可玩行 + 地面 + 天花板
    tile = min(size[0] / world.width_in_blocks, size[1] / rows)
    render_size = (
        max(1, round(world.width_in_blocks * tile)),
        max(1, round(rows * tile)),
    )
    band = pygame.Surface(render_size)
    band.fill(PREVIEW_BAND_BACKGROUND)
    RenderSystem().update(scene.objects, world, band, None, ViewMode.HORIZONTAL_EXPAND)

    surface = pygame.Surface(size)
    surface.fill(PREVIEW_BACKGROUND)
    surface.blit(band, ((size[0] - render_size[0]) // 2, (size[1] - render_size[1]) // 2))
    _PREVIEWS[key] = surface
    return surface
