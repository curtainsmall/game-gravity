"""打包：把游戏和关卡编辑器编成 bin/ 下的两个可执行文件。

运行：uv run build.py

产物：
  bin/gravity.exe        游戏
  bin/level-editor.exe   关卡编辑器

两个程序都按「exe 旁边的 assets/」找资源，所以 assets/ 必须和 exe 放在一起，
单独挪走 exe 会找不到关卡。打包不会往 bin/ 里拷资源：bin/assets 自己放、自己改，
重新打包不会把它盖掉。

打包参数都显式写出来，不依赖 PyInstaller 的自动推断：
  --paths           每个项目自己的模块根（core/、view/ 这些是顶层模块）
  --hidden-import   编辑器里 tkinter 是函数内 import，显式声明一份
  --exclude-module  游戏用不到 tkinter，明确排除，包更小
  --clean           每次清掉缓存重新分析，避免残留的旧分析结果
  --windowed        GUI 子系统，双击 exe 不弹 cmd 黑窗；代价是 stdout/stderr
                    没有去处，程序崩了看不到 traceback。要排查就把 TARGETS 里
                    对应条目的 windowed 改成 False，重打一次拿控制台版本

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
        "windowed": True,   # 不给控制台：双击不弹黑窗
    },
    {
        "name": "level-editor",
        "entry": ROOT / "level-editor" / "main.py",
        "paths": [ROOT / "level-editor"],
        "hidden_imports": ["tkinter", "tkinter.filedialog"],
        "excluded_modules": [],
        "windowed": True,
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
    # windowed 走 GUI 子系统，双击运行时不会先弹一个 cmd 控制台窗口
    subsystem_flag = "--windowed" if target["windowed"] else "--console"
    # 用当前解释器跑 -m PyInstaller，不依赖 pyinstaller 是否在 PATH 上，
    # 也保证分析和打包用的是项目 .venv 里那一份依赖（pygame-ce 在里面）。
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        subsystem_flag,
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


def main() -> None:
    sync_environment()
    BIN_DIR.mkdir(exist_ok=True)
    for target in TARGETS:
        build(target)

    print("[build] done:")
    for path in sorted(BIN_DIR.iterdir()):
        print(f"  {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
