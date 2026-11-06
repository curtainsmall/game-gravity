"""关卡清单：game/levels/ 下每个文件夹是一关，按文件夹名排字母序。"""

from dataclasses import dataclass
from pathlib import Path

import pygame

from game_settings import LEVELS_DIR
from renderer.render_system import RenderSystem
from renderer.viewport import ViewMode
from scenes.scene import Scene

SCENE_FILE = "scene.json"


@dataclass(frozen=True)
class LevelEntry:
    folder: Path
    name: str

    @property
    def scene_path(self) -> Path:
        return self.folder / SCENE_FILE


def discover_levels() -> list[LevelEntry]:
    """扫 levels/ 下带 scene.json 的文件夹，按文件夹名不分大小写排字母序。"""
    if not LEVELS_DIR.is_dir():
        return []
    entries = [
        LevelEntry(folder=folder, name=folder.name)
        for folder in LEVELS_DIR.iterdir()
        if folder.is_dir() and (folder / SCENE_FILE).is_file()
    ]
    return sorted(entries, key=lambda entry: entry.name.lower())


def load_scene(entry: LevelEntry) -> Scene | None:
    try:
        return Scene.from_level_file(str(entry.scene_path))
    except (OSError, ValueError):
        return None


_PREVIEWS: dict[tuple[str, int, int], pygame.Surface | None] = {}

PREVIEW_BACKGROUND = (255, 255, 255)
PREVIEW_BAND_BACKGROUND = (235, 235, 235)


def level_preview(entry: LevelEntry, size: tuple[int, int]) -> pygame.Surface | None:
    """整关缩略图：横竖都塞进给定尺寸，居中留白，按尺寸缓存。"""
    if size[0] <= 0 or size[1] <= 0:
        return None
    key = (str(entry.scene_path), size[0], size[1])
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
