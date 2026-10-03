@echo off
rem 打包成單一 exe：需先執行 pip install -r requirements-dev.txt
python -m PyInstaller --onefile --windowed --name "檔案整理小幫手" ^
  --exclude-module unittest --exclude-module email --exclude-module xml ^
  --exclude-module http --exclude-module xmlrpc --exclude-module pydoc ^
  --exclude-module doctest --exclude-module distutils --exclude-module lib2to3 ^
  --exclude-module sqlite3 --exclude-module multiprocessing --exclude-module concurrent ^
  --exclude-module asyncio --exclude-module curses --exclude-module pdb ^
  --exclude-module difflib --exclude-module ensurepip --exclude-module venv ^
  --exclude-module test --exclude-module tkinter.test ^
  organizer_gui.py
echo.
echo 完成，exe 在 dist 資料夾裡。
