# -*- coding: utf-8 -*-
"""
organizer.py - 安全的檔案自動分類腳本（Windows，命令列版本）

流程：先「規劃」→ 顯示預覽 → 你輸入 y 確認後才「執行」。
規劃階段完全不會動任何檔案，所以可以放心先跑一次看看。

用法：
    python organizer.py                      # 使用下方 TARGET_PATH
    python organizer.py "D:\\某個資料夾"       # 臨時指定路徑
    python organizer.py --dry-run            # 只預覽，不詢問、不執行

也可以直接用視窗版本 organizer_gui.py（或打包好的 .exe），不用打指令。
分類規則、安全防護都寫在 organizer_core.py，兩邊共用，改一次就同步生效。
"""

import argparse
import sys
from pathlib import Path

import organizer_core as core

# =====================================================================
#  只需要改這裡：要整理的資料夾路徑
#  注意：路徑字串前面的 r 不能刪（代表反斜線 \ 不轉義）。
# =====================================================================
TARGET_PATH = str(Path.home() / "Downloads")      # 預設：下載資料夾

# 指定「不要動」的檔案或資料夾名稱（不分大小寫，要完整名稱）。
# 例如正在進行中的專案資料夾，放在這裡就會留在原位。
KEEP_IN_PLACE = set()                              # 例如 {"my-project", "notes"}
# TARGET_PATH = str(Path.home() / "Desktop")      # 桌面：拿掉最前面的 # 並把上一行加 #
# TARGET_PATH = r"C:\Users\你的名字\OneDrive\桌面"  # 桌面被 OneDrive 接管時用這種寫法
# =====================================================================


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    parser = argparse.ArgumentParser(description="安全的檔案自動分類腳本")
    parser.add_argument("path", nargs="?", default=TARGET_PATH, help="要整理的資料夾")
    parser.add_argument("--dry-run", action="store_true", help="只預覽，不執行")
    parser.add_argument("--yes", action="store_true", help="略過確認直接執行")
    args = parser.parse_args()

    target = Path(args.path).expanduser()
    problem = core.check_target_is_safe(target)
    if problem:
        print(f"已中止：{problem}")
        return 1
    target = target.resolve()

    self_paths = [Path(__file__).resolve(), Path(core.__file__).resolve()]
    plan = core.build_plan(target, KEEP_IN_PLACE, self_paths)
    print(core.format_plan(target, plan))

    if plan.is_empty:
        print("沒有需要整理的項目。")
        return 0
    if args.dry_run:
        print("（--dry-run：僅預覽，未做任何變更）")
        return 0
    if not args.yes:
        try:
            answer = input("以上內容確認無誤，要正式執行嗎？(y/N)：").strip().lower()
        except EOFError:
            answer = ""
        if answer != "y":
            print("已取消，沒有變更任何檔案。")
            return 0

    from datetime import datetime
    log_path = Path(__file__).resolve().parent / f"organizer_log_{datetime.now():%Y%m%d_%H%M%S}.csv"
    core.execute(target, plan, log_path, on_progress=print)
    return 0


if __name__ == "__main__":
    code = main()
    if sys.stdin and sys.stdin.isatty() and not any(a in sys.argv for a in ("--yes", "--dry-run")):
        try:
            input("\n按 Enter 關閉視窗...")
        except EOFError:
            pass
    sys.exit(code)
