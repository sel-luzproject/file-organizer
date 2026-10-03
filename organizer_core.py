# -*- coding: utf-8 -*-
"""
organizer_core.py - 檔案分類的核心邏輯（被 organizer.py 命令列版本
與 organizer_gui.py 視窗版本共用，兩邊規則永遠一致）。

這個檔案本身不會被直接執行，也不會被任何規則搬動或刪除。
"""

import csv
import os
import re
import shutil
from pathlib import Path

# ---------------- 分類規則（可自行增減副檔名，一律小寫、含點） ----------------
CATEGORIES = {
    "1_圖片與設計素材": {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".heic", ".psd", ".ai"},
    "2_上課與工作文件": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".csv", ".odt"},
    "3_壓縮壓縮包": {".zip", ".rar", ".7z", ".tar", ".gz"},
    "4_軟體安裝程式": {".exe", ".msi"},
    "5_多媒體影音": {".mp4", ".mp3", ".wav", ".mkv", ".avi", ".mov", ".flac", ".m4a"},
}
OLD_FOLDERS_NAME = "6_未分類舊資料夾"
MANAGED_FOLDERS = set(CATEGORIES) | {OLD_FOLDERS_NAME}

# ---------------- 安全防護：這些一律不碰 ----------------
# 1. 絕對不移動的副檔名（腳本、系統檔、下載到一半的暫存檔、捷徑）
PROTECTED_EXTENSIONS = {
    ".py", ".pyw", ".pyc", ".pyo",
    ".sys", ".dll", ".drv", ".inf", ".cat", ".mui", ".msc", ".ini", ".dat",
    ".bat", ".cmd", ".lnk", ".url",
    ".tmp", ".crdownload", ".part", ".partial", ".download",
}
# 2. 絕對不移動的檔名（小寫）
PROTECTED_NAMES = {
    "desktop.ini", "thumbs.db", ".ds_store",
    "pagefile.sys", "hiberfil.sys", "swapfile.sys", "ntuser.dat",
    "$recycle.bin", "system volume information", "recovery", "boot", "bootmgr",
}
# 2b. 絕對不移動的名稱開頭（小寫）：Windows 內建元件/應用程式留下的資料夾
PROTECTED_PREFIXES = ("microsoftwindows.", "microsoft.windows.", "windows.")
# 3. Windows 檔案屬性：隱藏 / 系統 / 符號連結(reparse point，資料夾才擋)
ATTR_HIDDEN = 0x2
ATTR_SYSTEM = 0x4
ATTR_REPARSE = 0x400

# 這幾個核心檔名一律跳過（保險用；真正可靠的排除方式是下面的 self_paths）
CORE_FILE_NAMES = {"organizer.py", "organizer_core.py", "organizer_gui.py"}


# ============================ 工具函式 ============================
def norm(p):
    """路徑正規化（Windows 不分大小寫）。"""
    return os.path.normcase(os.path.abspath(str(p)))


def file_attrs(entry):
    try:
        return entry.stat(follow_symlinks=False).st_file_attributes
    except (AttributeError, OSError):
        return 0


def unique_path(path, taken=()):
    """若 path 已存在（或已被本次計畫佔用），在檔名後加 _1, _2 ...，絕不覆蓋。"""
    path = Path(path)
    taken = set(taken)
    candidate = path
    n = 0
    while candidate.exists() or norm(candidate) in taken:
        n += 1
        candidate = path.with_name(f"{path.stem}_{n}{path.suffix}")
    return candidate


def category_of(ext):
    for folder, exts in CATEGORIES.items():
        if ext in exts:
            return folder
    return None


def check_target_is_safe(target):
    """拒絕整理磁碟根目錄、Windows / Program Files、使用者家目錄本身與其上層、AppData。"""
    if not target.is_dir():
        return f"找不到資料夾：{target}"
    t = norm(target.resolve())
    if os.path.dirname(t) == t:
        return "不可整理磁碟根目錄。"

    home = Path.home()
    no_go_trees = [home / "AppData"]
    for var in ("SystemRoot", "ProgramFiles", "ProgramFiles(x86)", "ProgramData"):
        if os.environ.get(var):
            no_go_trees.append(Path(os.environ[var]))
    for p in no_go_trees:
        pn = norm(p)
        if t == pn or t.startswith(pn + os.sep):
            return f"不可整理系統資料夾：{p}"

    if norm(home) == t or norm(home).startswith(t + os.sep):
        return f"不可整理使用者家目錄或其上層資料夾，請指定桌面/下載等子資料夾：{home}"
    return None


def tree_has_files(folder):
    """資料夾底下（任意深度）是否有任何檔案？無法確認時一律當作「有」，寧可不刪。"""
    failed = []
    for root, dirs, files in os.walk(folder, onerror=failed.append):
        if failed or files:
            return True
        for d in dirs:
            full = os.path.join(root, d)
            if os.path.islink(full):
                return True
            try:
                if os.lstat(full).st_file_attributes & ATTR_REPARSE:
                    return True
            except (AttributeError, OSError):
                pass
    return bool(failed)


def remove_empty_tree(folder):
    """由內而外刪除空資料夾；os.rmdir 遇到非空資料夾會直接失敗，因此不可能誤刪檔案。"""
    for root, _dirs, _files in os.walk(folder, topdown=False):
        os.rmdir(root)


# ============================ 規劃階段（不動任何東西） ============================
class Plan:
    def __init__(self):
        self.file_moves = []      # (來源 Path, 分類資料夾名稱)
        self.empty_dirs = []      # 要刪除的空資料夾
        self.old_dirs = []        # 要搬進「6_未分類舊資料夾」的資料夾
        self.skipped = []         # (名稱, 原因)

    @property
    def is_empty(self):
        return not (self.file_moves or self.empty_dirs or self.old_dirs)


def build_plan(target, keep_in_place=(), self_paths=()):
    """規劃整理內容，完全唯讀，不會動任何檔案。
    target: 要整理的資料夾 (Path)
    keep_in_place: 使用者指定要保留不動的檔名/資料夾名稱（不分大小寫）
    self_paths: 絕對不能動的實際路徑（例如正在執行的 .py / .exe 本身）
    """
    plan = Plan()
    keep_lower = {str(k).lower() for k in keep_in_place}
    self_norm = {norm(p) for p in self_paths}
    with os.scandir(target) as it:
        entries = sorted(it, key=lambda e: e.name.lower())

    for e in entries:
        name = e.name
        lower = name.lower()
        attrs = file_attrs(e)

        if lower in CORE_FILE_NAMES or norm(e.path) in self_norm:
            continue
        if lower in keep_lower:
            plan.skipped.append((name, "你指定保留不動"))
            continue
        if lower in PROTECTED_NAMES or lower.startswith(PROTECTED_PREFIXES) or name.startswith("~$"):
            plan.skipped.append((name, "系統檔/暫存檔"))
            continue
        if attrs & (ATTR_HIDDEN | ATTR_SYSTEM):
            plan.skipped.append((name, "隱藏或系統屬性"))
            continue
        if e.is_symlink():
            plan.skipped.append((name, "符號連結"))
            continue

        if e.is_dir(follow_symlinks=False):
            if name in MANAGED_FOLDERS:
                continue                       # 自己建立的分類資料夾，不動
            if attrs & ATTR_REPARSE:
                plan.skipped.append((name, "連接點/重分析點資料夾"))
                continue
            if tree_has_files(e.path):
                plan.old_dirs.append(Path(e.path))
            else:
                plan.empty_dirs.append(Path(e.path))
            continue

        # ---- 一般檔案 ----
        ext = Path(name).suffix.lower()
        if ext in PROTECTED_EXTENSIONS:
            plan.skipped.append((name, "受保護類型（腳本/系統/暫存/捷徑）"))
            continue
        folder = category_of(ext)
        if folder is None:
            plan.skipped.append((name, "副檔名不在規則內，維持原位"))
            continue
        plan.file_moves.append((Path(e.path), folder))
    return plan


def format_plan(target, plan):
    """把 Plan 轉成人看的多行文字（CLI 與 GUI 共用）。"""
    lines = [f"整理目標：{target}", "-" * 60]
    taken = set()
    lines.append(f"[搬移檔案] {len(plan.file_moves)} 個")
    for src, folder in plan.file_moves:
        dst = unique_path(target / folder / src.name, taken)
        taken.add(norm(dst))
        note = "  (同名，自動改名)" if dst.name != src.name else ""
        lines.append(f"   {src.name}  ->  {folder}\\{dst.name}{note}")

    lines.append(f"[刪除空資料夾] {len(plan.empty_dirs)} 個")
    for d in plan.empty_dirs:
        lines.append(f"   {d.name}")

    lines.append(f"[舊資料夾集中到 {OLD_FOLDERS_NAME}] {len(plan.old_dirs)} 個")
    for d in plan.old_dirs:
        lines.append(f"   {d.name}")

    keep = [s for s in plan.skipped if s[1] != "副檔名不在規則內，維持原位"]
    other = len(plan.skipped) - len(keep)
    lines.append(f"[刻意跳過] {len(keep)} 個")
    for name, why in keep:
        lines.append(f"   {name}  ({why})")

    if other:
        lines.append(f"[副檔名不在規則內、維持原位] {other} 個")
        counts = {}
        for name, why in plan.skipped:
            if why == "副檔名不在規則內，維持原位":
                ext = Path(name).suffix.lower() or "(無副檔名)"
                counts[ext] = counts.get(ext, 0) + 1
        top = sorted(counts.items(), key=lambda kv: -kv[1])
        lines.append("   副檔名統計：" + "、".join(f"{e} x{n}" for e, n in top))
    lines.append("-" * 60)
    return "\n".join(lines)


# ============================ 執行階段 ============================
def execute(target, plan, log_path, on_progress=None):
    """實際搬移/刪除。on_progress(text) 會在每個步驟被呼叫，可用來即時顯示進度。"""
    def report(msg):
        if on_progress:
            on_progress(msg)

    moved = deleted = failed = 0
    rows = []

    def safe_move(src, dst_dir):
        nonlocal moved, failed
        try:
            dst_dir.mkdir(exist_ok=True)
            dst = unique_path(dst_dir / src.name)
            shutil.move(str(src), str(dst))
            rows.append(("MOVE", str(src), str(dst)))
            moved += 1
        except OSError as err:
            rows.append(("FAIL", str(src), str(err)))
            failed += 1
            report(f"   [失敗，已跳過] {src.name}：{err}")

    for src, folder in plan.file_moves:
        safe_move(src, target / folder)

    for d in plan.empty_dirs:
        try:
            remove_empty_tree(d)
            rows.append(("DELETE_EMPTY", str(d), ""))
            deleted += 1
        except OSError as err:
            rows.append(("FAIL", str(d), str(err)))
            failed += 1
            report(f"   [失敗，已跳過] {d.name}：{err}")

    for d in plan.old_dirs:
        safe_move(d, target / OLD_FOLDERS_NAME)

    try:
        with open(log_path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["動作", "來源", "目的地/訊息"])
            w.writerows(rows)
        report(f"操作紀錄已存到：{log_path}")
    except OSError as err:
        report(f"（無法寫入紀錄檔：{err}）")

    summary = f"完成：搬移 {moved} 項、刪除空資料夾 {deleted} 個、失敗/跳過 {failed} 項。"
    report(summary)
    return moved, deleted, failed


# ============================ 再分堆：把同一系列的檔案收進子資料夾 ============================
# 例如「LUZ coffee (1).jpg」「LUZ coffee (2).jpg」會被視為同一系列「LUZ coffee」，
# 只在一個分類資料夾「內部」動作，不會跨資料夾搬動、不會影響 1~6 的大分類。
_TRAILING_NUMBER = re.compile(r"""
    (?:\s*\(\d+\))          # 結尾像 " (1)" "(23)"
    | (?:[ _-]\d{1,4})       # 結尾像 " 1" "_1" "-12"（1~4 位數，避免誤吃年份/型號）
    $""", re.VERBOSE)


def base_name_of(stem):
    """把檔名（不含副檔名）去掉結尾的編號，回傳「系列名稱」。反覆去除以處理 "xxx (1) (2)" 這種情況。"""
    prev = None
    base = stem.strip()
    while base != prev:
        prev = base
        base = _TRAILING_NUMBER.sub("", base).strip()
    return base


SAFE_NAME_CHARS = re.compile(r'[\\/:*?"<>|]')


def sanitize_folder_name(name, fallback="未命名系列"):
    name = SAFE_NAME_CHARS.sub("_", name).strip(" .")
    return name or fallback


def build_group_plan(folder, min_group=2):
    """規劃「再分堆」：只掃描 folder 這一層（不含子資料夾），把系列名稱相同、
    數量達到 min_group 的檔案分到以該系列命名的子資料夾。唯讀，不動檔案。
    回傳 dict：{ 系列名稱: [檔案 Path, ...] }，只包含真的要分堆的系列。
    """
    groups = {}
    with os.scandir(folder) as it:
        for e in it:
            if not e.is_file(follow_symlinks=False):
                continue
            attrs = file_attrs(e)
            if attrs & (ATTR_HIDDEN | ATTR_SYSTEM):
                continue
            p = Path(e.path)
            base = base_name_of(p.stem)
            if not base:
                continue
            groups.setdefault(base, []).append(p)
    return {base: files for base, files in groups.items() if len(files) >= min_group}


def format_group_plan(folder, groups):
    lines = [f"再分堆目標：{folder}", "-" * 60]
    if not groups:
        lines.append("沒有偵測到可以歸堆的系列（同系列至少要 2 個檔案）。")
    for base, files in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        lines.append(f"[{sanitize_folder_name(base)}] {len(files)} 個")
        for f in files:
            lines.append(f"   {f.name}")
    lines.append("-" * 60)
    return "\n".join(lines)


def execute_group_plan(folder, groups, on_progress=None):
    def report(msg):
        if on_progress:
            on_progress(msg)

    moved = failed = 0
    for base, files in groups.items():
        sub = Path(folder) / sanitize_folder_name(base)
        try:
            sub.mkdir(exist_ok=True)
        except OSError as err:
            report(f"   [失敗，已跳過整個系列 {base}]：{err}")
            failed += len(files)
            continue
        for f in files:
            try:
                dst = unique_path(sub / f.name)
                shutil.move(str(f), str(dst))
                moved += 1
            except OSError as err:
                report(f"   [失敗，已跳過] {f.name}：{err}")
                failed += 1
    summary = f"再分堆完成：搬移 {moved} 項、失敗/跳過 {failed} 項。"
    report(summary)
    return moved, failed
