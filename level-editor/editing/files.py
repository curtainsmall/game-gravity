"""文件对话框小件。"""

from core.constants import FILE_FILTERS, LEVELS_DIR


def ask_open_path() -> str | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return None
    root = tk.Tk()
    root.withdraw()
    try:
        path = filedialog.askopenfilename(title="打开关卡", initialdir=LEVELS_DIR, filetypes=FILE_FILTERS)
    finally:
        root.destroy()
    return path or None


def ask_save_path() -> str | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return None
    root = tk.Tk()
    root.withdraw()
    try:
        path = filedialog.asksaveasfilename(
            title="保存关卡",
            initialdir=LEVELS_DIR,
            defaultextension=".json",
            filetypes=FILE_FILTERS,
        )
    finally:
        root.destroy()
    return path or None
