"""打包：把游戏和关卡编辑器编成 bin/ 下的两个可执行文件。

运行：uv run build.py

产物：
  bin/gravity.exe        游戏
  bin/level-editor.exe   关卡编辑器
  bin/assets/            资源，会拷到 exe 旁边（关卡可以直接改）

两个程序都按「exe 旁边的 assets/」找资源，所以 assets/ 必须和 exe 放在一起，
单独挪走 exe 会找不到关卡。

打包参数都显式写出来，不依赖 PyInstaller 的自动推断：
  --paths           每个项目自己的模块根（core/、view/ 这些是顶层模块）
  --hidden-import   编辑器里 tkinter 是函数内 import，显式声明一份
  --exclude-module  游戏用不到 tkinter，明确排除，包更小
  --clean           每次清掉缓存重新分析，避免残留的旧分析结果

构建前先跑一次 uv sync，保证 .venv 和 pyproject.toml / uv.lock 一致；
用 uv run 启动时这步其实已经做过了，直接 python build.py 时它才是必要的。
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BIN_DIR = ROOT / "bin"
WORK_DIR = ROOT / "build" / "pyinstaller"

TARGETS = [
    {
        "name": "gravity",
        "entry": ROOT / "game" / "main.py",
        "paths": [ROOT / "game"],
        "hidden_imports": [],
        "excluded_modules": ["tkinter"],
    },
    {
        "name": "level-editor",
        "entry": ROOT / "level-editor" / "main.py",
        "paths": [ROOT / "level-editor"],
        "hidden_imports": ["tkinter", "tkinter.filedialog"],
        "excluded_modules": [],
    },
]


def sync_environment() -> None:
    """让 .venv 和 pyproject.toml / uv.lock 对齐，缺依赖时构建会失败得很奇怪。"""
    uv = shutil.which("uv")
    if uv is None:
        print("[build] 找不到 uv，跳过 uv sync（请自行保证 .venv 已就绪）", file=sys.stderr)
        return
    print(f"[build] uv sync  ({uv})")
    subprocess.run([uv, "sync"], cwd=ROOT, check=True)


def build(target: dict) -> None:
    name = target["name"]
    # 用当前解释器跑 -m PyInstaller，不依赖 pyinstaller 是否在 PATH 上，
    # 也保证分析和打包用的是项目 .venv 里那一份依赖（pygame-ce 在里面）。
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--console",
        "--name",
        name,
        "--distpath",
        str(BIN_DIR),
        "--workpath",
        str(WORK_DIR / name),
        "--specpath",
        str(WORK_DIR),
        "--log-level",
        "WARN",
    ]
    for path in target["paths"]:
        command += ["--paths", str(path)]
    for module in target["hidden_imports"]:
        command += ["--hidden-import", module]
    for module in target["excluded_modules"]:
        command += ["--exclude-module", module]
    command.append(str(target["entry"]))

    print(f"[build] {name}: {target['entry'].relative_to(ROOT)}")
    subprocess.run(command, cwd=ROOT, check=True)


def collect_assets() -> None:
    source = ROOT / "assets"
    if not source.is_dir():
        return
    target = BIN_DIR / "assets"
    shutil.copytree(source, target, dirs_exist_ok=True)
    print(f"[build] assets -> {target.relative_to(ROOT)}")


def main() -> None:
    sync_environment()
    BIN_DIR.mkdir(exist_ok=True)
    for target in TARGETS:
        build(target)
    collect_assets()

    print("[build] done:")
    for path in sorted(BIN_DIR.iterdir()):
        print(f"  {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
