"""文件与文件夹对话框小件。"""

from core.constants import BACKGROUND_FILTERS, LEVELS_DIR


def ask_level_folder(title: str, initial_dir: str = LEVELS_DIR) -> str | None:
    """关卡是一个文件夹，打开和保存都选文件夹：文件夹名就是关卡名。"""
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return None
    root = tk.Tk()
    root.withdraw()
    try:
        folder = filedialog.askdirectory(title=title, initialdir=initial_dir, mustexist=False)
    finally:
        root.destroy()
    return folder or None


def ask_background_path(initial_dir: str) -> str | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return None
    root = tk.Tk()
    root.withdraw()
    try:
        path = filedialog.askopenfilename(
            title="选择背景图", initialdir=initial_dir, filetypes=BACKGROUND_FILTERS
        )
    finally:
        root.destroy()
    return path or None
