# -*- coding: utf-8 -*-
"""
organizer_gui.py - 檔案整理小幫手（視窗版本）

按兩下開啟（或打包成 .exe 後按兩下開啟），選擇要整理的資料夾，
按「預覽」看清單，確認沒問題再按「開始整理」。
規則、安全防護跟命令列版本 organizer.py 完全共用 organizer_core.py。
"""

import json
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import organizer_core as core

APP_TITLE = "檔案整理小幫手"


def app_dir():
    """設定檔要存放的位置：打包成 .exe 時放在 .exe 旁邊，直接跑 .py 時放在腳本旁邊。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def self_paths():
    """絕對不能被自己掃到、搬走的路徑：這支程式本身 + 核心邏輯檔。"""
    paths = [Path(core.__file__).resolve()]
    if getattr(sys, "frozen", False):
        paths.append(Path(sys.executable).resolve())
    else:
        paths.append(Path(__file__).resolve())
    return paths


CONFIG_PATH = app_dir() / "organizer_settings.json"
DEFAULT_KEEP = ""


def load_settings():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("last_target", ""), data.get("keep_in_place", DEFAULT_KEEP)
    except (OSError, ValueError):
        return "", DEFAULT_KEEP


def save_settings(target, keep_in_place):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"last_target": target, "keep_in_place": keep_in_place}, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


class OrganizerApp:
    def __init__(self, root):
        self.root = root
        root.title(APP_TITLE)
        root.geometry("760x620")
        root.minsize(600, 420)

        self.target_var = tk.StringVar()
        self.keep_var = tk.StringVar()
        last_target, last_keep = load_settings()
        self.target_var.set(last_target)
        self.keep_var.set(last_keep)

        self.current_plan = None
        self.current_target = None
        self.group_folder = None
        self.current_group = None

        self._build_step1()
        self._build_step2()
        self._build_step3()
        self._build_log()

    # ---------------- 介面 ----------------
    def _build_step1(self):
        box = ttk.LabelFrame(self.root, text="① 選擇要整理的資料夾", padding=10)
        box.pack(fill="x", padx=10, pady=(10, 5))

        btns = ttk.Frame(box)
        btns.pack(fill="x")
        ttk.Button(btns, text="瀏覽資料夾...", command=self.browse_target).pack(side="left")

        row = ttk.Frame(box)
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text="目前路徑：").pack(side="left")
        entry = ttk.Entry(row, textvariable=self.target_var)
        entry.pack(side="left", fill="x", expand=True)

        row2 = ttk.Frame(box)
        row2.pack(fill="x", pady=(8, 0))
        ttk.Label(row2, text="保留不動的資料夾/檔名（用逗號分隔）：").pack(anchor="w")
        ttk.Entry(row2, textvariable=self.keep_var).pack(fill="x", pady=(2, 0))

    def _build_step2(self):
        box = ttk.LabelFrame(self.root, text="② 依副檔名分類（先預覽，確認才執行）", padding=10)
        box.pack(fill="x", padx=10, pady=5)

        btns = ttk.Frame(box)
        btns.pack(fill="x")
        ttk.Button(btns, text="預覽", command=self.preview).pack(side="left")
        self.execute_btn = ttk.Button(btns, text="開始整理", command=self.execute, state="disabled")
        self.execute_btn.pack(side="left", padx=8)

    def _build_step3(self):
        box = ttk.LabelFrame(self.root, text="③（選用）再分堆：把同系列檔案收進子資料夾，例如: 王大明(1).jpg/(2).jpg", padding=10)
        box.pack(fill="x", padx=10, pady=5)

        row = ttk.Frame(box)
        row.pack(fill="x")
        ttk.Label(row, text="要再分堆的資料夾：").pack(side="left")
        self.group_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.group_var).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(row, text="瀏覽...", command=self.browse_group_folder).pack(side="left")

        btns = ttk.Frame(box)
        btns.pack(fill="x", pady=(8, 0))
        ttk.Button(btns, text="預覽再分堆", command=self.preview_group).pack(side="left")
        self.group_btn = ttk.Button(btns, text="開始再分堆", command=self.execute_group, state="disabled")
        self.group_btn.pack(side="left", padx=8)

    def _build_log(self):
        box = ttk.LabelFrame(self.root, text="結果", padding=6)
        box.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        self.log = tk.Text(box, wrap="word", font=("Consolas", 10))
        scroll = ttk.Scrollbar(box, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        self.log.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    # ---------------- 共用小工具 ----------------
    def write(self, text):
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.root.update_idletasks()

    def clear_log(self):
        self.log.delete("1.0", "end")

    def set_target(self, path):
        self.target_var.set(str(path))

    def browse_target(self):
        path = filedialog.askdirectory(title="選擇要整理的資料夾")
        if path:
            self.set_target(path)

    def browse_group_folder(self):
        start = self.current_target or Path(self.target_var.get()).expanduser()
        path = filedialog.askdirectory(title="選擇要再分堆的資料夾（例如整理後的 1_圖片與設計素材）", initialdir=str(start) if Path(str(start)).is_dir() else str(Path.home()))
        if path:
            self.group_var.set(path)

    def keep_list(self):
        return [s.strip() for s in self.keep_var.get().split(",") if s.strip()]

    # ---------------- 步驟②：分類 ----------------
    def preview(self):
        raw = self.target_var.get().strip()
        if not raw:
            messagebox.showwarning(APP_TITLE, "請先選擇要整理的資料夾。")
            return
        target = Path(raw).expanduser()
        problem = core.check_target_is_safe(target)
        if problem:
            self.clear_log()
            self.write(f"已中止：{problem}")
            self.execute_btn.config(state="disabled")
            self.current_plan = None
            return
        target = target.resolve()

        plan = core.build_plan(target, self.keep_list(), self_paths())
        self.clear_log()
        self.write(core.format_plan(target, plan))
        self.current_plan = plan
        self.current_target = target
        save_settings(str(target), self.keep_var.get())

        if plan.is_empty:
            self.write("沒有需要整理的項目。")
            self.execute_btn.config(state="disabled")
        else:
            self.execute_btn.config(state="normal")
            self.write("\n（以上僅為預覽，尚未變更任何檔案。確認沒問題再按「開始整理」。）")

    def execute(self):
        if not self.current_plan or self.current_plan.is_empty:
            return
        n_move = len(self.current_plan.file_moves)
        n_del = len(self.current_plan.empty_dirs)
        n_old = len(self.current_plan.old_dirs)
        ok = messagebox.askyesno(
            APP_TITLE,
            f"確定要整理「{self.current_target}」嗎？\n\n"
            f"搬移檔案：{n_move} 個\n刪除空資料夾：{n_del} 個\n舊資料夾集中：{n_old} 個\n\n"
            "此動作只會搬移／刪除空資料夾，不會刪除任何有內容的檔案或資料夾。",
        )
        if not ok:
            return

        from datetime import datetime
        log_path = app_dir() / f"organizer_log_{datetime.now():%Y%m%d_%H%M%S}.csv"
        self.write("\n開始整理...")
        core.execute(self.current_target, self.current_plan, log_path, on_progress=self.write)
        self.execute_btn.config(state="disabled")
        self.current_plan = None
        messagebox.showinfo(APP_TITLE, "整理完成！可以到資料夾確認結果，或查看下方紀錄。")

    # ---------------- 步驟③：再分堆 ----------------
    def preview_group(self):
        raw = self.group_var.get().strip()
        if not raw:
            messagebox.showwarning(APP_TITLE, "請先選擇要再分堆的資料夾。")
            return
        folder = Path(raw).expanduser()
        problem = core.check_target_is_safe(folder)
        if problem:
            self.clear_log()
            self.write(f"已中止：{problem}")
            self.group_btn.config(state="disabled")
            self.current_group = None
            return
        folder = folder.resolve()
        groups = core.build_group_plan(folder)
        self.clear_log()
        self.write(core.format_group_plan(folder, groups))
        self.current_group = groups
        self.group_folder = folder
        self.group_btn.config(state="normal" if groups else "disabled")
        if groups:
            self.write("\n（以上僅為預覽，尚未變更任何檔案。確認沒問題再按「開始再分堆」。）")

    def execute_group(self):
        if not self.current_group:
            return
        n = sum(len(v) for v in self.current_group.values())
        ok = messagebox.askyesno(
            APP_TITLE,
            f"確定要在「{self.group_folder}」裡，把 {len(self.current_group)} 個系列、共 {n} 個檔案分進子資料夾嗎？",
        )
        if not ok:
            return
        self.write("\n開始再分堆...")
        core.execute_group_plan(self.group_folder, self.current_group, on_progress=self.write)
        self.group_btn.config(state="disabled")
        self.current_group = None
        messagebox.showinfo(APP_TITLE, "再分堆完成！")


def main():
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
    except tk.TclError:
        pass
    OrganizerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
