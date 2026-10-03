# -*- coding: utf-8 -*-
"""核心邏輯測試。執行方式（在專案根目錄）：python -m unittest discover tests"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import organizer_core as core  # noqa: E402


def touch(path, text="x"):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class CoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_classification_by_extension(self):
        for name in ("a.PNG", "b.pdf", "c.zip", "d.exe", "e.mp3", "f.xyz"):
            touch(self.root / name)
        plan = core.build_plan(self.root)
        moves = {src.name: folder for src, folder in plan.file_moves}
        self.assertEqual(moves["a.PNG"], "1_圖片與設計素材")
        self.assertEqual(moves["b.pdf"], "2_上課與工作文件")
        self.assertEqual(moves["c.zip"], "3_壓縮壓縮包")
        self.assertEqual(moves["d.exe"], "4_軟體安裝程式")
        self.assertEqual(moves["e.mp3"], "5_多媒體影音")
        self.assertNotIn("f.xyz", moves)

    def test_protected_files_are_skipped(self):
        for name in ("run.py", "desktop.ini", "shortcut.lnk", "~$lock.docx", "dl.crdownload"):
            touch(self.root / name)
        plan = core.build_plan(self.root)
        self.assertEqual(plan.file_moves, [])

    def test_self_path_is_never_moved(self):
        me = touch(self.root / "tool.exe")
        touch(self.root / "other.exe")
        plan = core.build_plan(self.root, self_paths=[me])
        names = {src.name for src, _ in plan.file_moves}
        self.assertEqual(names, {"other.exe"})

    def test_keep_in_place(self):
        touch(self.root / "proj" / "f.txt")
        plan = core.build_plan(self.root, keep_in_place=["PROJ"])
        self.assertEqual(plan.old_dirs, [])
        self.assertIn(("proj", "你指定保留不動"), plan.skipped)

    def test_empty_and_nonempty_folders(self):
        (self.root / "empty" / "sub").mkdir(parents=True)
        touch(self.root / "full" / "f.txt")
        plan = core.build_plan(self.root)
        self.assertEqual([p.name for p in plan.empty_dirs], ["empty"])
        self.assertEqual([p.name for p in plan.old_dirs], ["full"])

    def test_execute_never_overwrites(self):
        touch(self.root / "1_圖片與設計素材" / "a.png", "OLD")
        touch(self.root / "a.png", "NEW")
        plan = core.build_plan(self.root)
        core.execute(self.root, plan, self.root / "log.csv")
        self.assertEqual((self.root / "1_圖片與設計素材" / "a.png").read_text(encoding="utf-8"), "OLD")
        self.assertEqual((self.root / "1_圖片與設計素材" / "a_1.png").read_text(encoding="utf-8"), "NEW")

    def test_empty_folder_removal_never_deletes_files(self):
        touch(self.root / "full" / "deep" / "f.txt")
        with self.assertRaises(OSError):
            core.remove_empty_tree(self.root / "full")
        self.assertTrue((self.root / "full" / "deep" / "f.txt").exists())

    def test_unsafe_targets_are_refused(self):
        self.assertIsNotNone(core.check_target_is_safe(Path(Path.home().anchor)))
        self.assertIsNotNone(core.check_target_is_safe(Path.home()))
        self.assertIsNotNone(core.check_target_is_safe(self.root / "missing"))
        self.assertIsNotNone(core.check_target_is_safe(Path.home() / "AppData" / "Local"))

    def test_base_name_of(self):
        self.assertEqual(core.base_name_of("王大明(1)"), "王大明")
        self.assertEqual(core.base_name_of("LUZ coffee (12)"), "LUZ coffee")
        self.assertEqual(core.base_name_of("Report_2"), "Report")
        self.assertEqual(core.base_name_of("photo (1) (2)"), "photo")
        self.assertEqual(core.base_name_of("single"), "single")

    def test_group_plan_and_execute(self):
        for n in (1, 2, 3):
            touch(self.root / f"王大明({n}).jpg")
        touch(self.root / "alone.jpg")
        groups = core.build_group_plan(self.root)
        self.assertEqual(list(groups), ["王大明"])
        core.execute_group_plan(self.root, groups)
        self.assertTrue((self.root / "王大明" / "王大明(2).jpg").exists())
        self.assertTrue((self.root / "alone.jpg").exists())


if __name__ == "__main__":
    unittest.main()
