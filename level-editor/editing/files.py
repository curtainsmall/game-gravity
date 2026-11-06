"""文件对话框小件。"""

from core.constants import BACKGROUND_FILTERS, DEFAULT_GAME_DIR, GAME_FILTERS, GAME_FILE_NAME


def ask_game_file(title: str, initial_dir: str = DEFAULT_GAME_DIR) -> str | None:
    """挑一份 game.json：它就是游戏的设置，关卡放在它旁边的 levels/ 里。"""
    return _ask_file(title, initial_dir, GAME_FILTERS, save=False)


def ask_game_file_to_create(title: str, initial_dir: str = DEFAULT_GAME_DIR) -> str | None:
    """新建 game.json：选保存位置，默认就叫 game.json。"""
    return _ask_file(title, initial_dir, GAME_FILTERS, save=True, default_name=GAME_FILE_NAME)


def ask_image_path(title: str, initial_dir: str) -> str | None:
    """挑一张图片（背景、贴图都用它）。"""
    return _ask_file(title, initial_dir, BACKGROUND_FILTERS, save=False)


def _ask_file(
    title: str,
    initial_dir: str,
    filters: list,
    save: bool,
    default_name: str = "",
) -> str | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return None
    root = tk.Tk()
    root.withdraw()
    try:
        if save:
            path = filedialog.asksaveasfilename(
                title=title,
                initialdir=initial_dir,
                initialfile=default_name,
                filetypes=filters,
            )
        else:
            path = filedialog.askopenfilename(
                title=title, initialdir=initial_dir, filetypes=filters
            )
    finally:
        root.destroy()
    return path or None
