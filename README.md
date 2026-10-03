# 檔案整理小幫手 File Organizer

一個**安全優先**的 Windows 檔案自動分類工具：依副檔名把雜亂的資料夾（桌面、下載……）整理成分類資料夾。先預覽、你確認後才會動手，而且**不會覆蓋、不會刪除任何有內容的檔案**。

> A safety-first file organizer for Windows. It previews every change, asks for confirmation, never overwrites existing files, and never deletes anything except truly empty folders. Pure Python standard library (tkinter GUI + CLI).

## 功能

- **視窗版**：按兩下開啟，選資料夾 → 預覽 → 確認 → 開始整理。
- **命令列版**：適合想用指令或排程的人。
- **依副檔名分類**，在目標資料夾內建立：

  | 資料夾 | 副檔名 |
  |---|---|
  | `1_圖片與設計素材` | png jpg jpeg gif bmp webp svg heic psd ai |
  | `2_上課與工作文件` | pdf doc docx xls xlsx ppt pptx txt csv odt |
  | `3_壓縮壓縮包` | zip rar 7z tar gz |
  | `4_軟體安裝程式` | exe msi |
  | `5_多媒體影音` | mp4 mp3 wav mkv avi mov flac m4a |
  | `6_未分類舊資料夾` | 原本就存在、裡面有東西的舊資料夾 |

- **完全空的資料夾會被刪除**（只能刪空的，有任何檔案都刪不掉）。
- **再分堆（選用）**：把 `王大明(1).jpg`、`王大明(2).jpg` 這類同系列檔案收進 `王大明\` 子資料夾；只出現一次的檔案不動。
- 可指定「保留不動」的檔案/資料夾名稱（例如進行中的專案）。
- 每次整理都會留下 `organizer_log_日期時間.csv`，記錄每個檔案從哪搬到哪，方便還原。

## 安全設計

- 預覽與執行分開，預覽階段**完全不動任何檔案**。
- 同名檔案自動加序號（`a.png` → `a_1.png`），**絕不覆蓋**。
- 不碰：`.py` / 系統類副檔名（`.sys` `.dll` `.ini` `.lnk` `.bat`……）、隱藏或系統屬性的項目、`desktop.ini`、Office 暫存檔 `~$*`、下載到一半的 `.crdownload`、Windows 內建元件資料夾、符號連結/連接點，以及程式本身。
- 拒絕整理磁碟根目錄、`C:\Windows`、`Program Files`、`AppData`、使用者家目錄本身。
- 只搬移，不刪除（除了空資料夾）。單一項目失敗（例如檔案被占用）只會跳過那一項。

## 使用方式

### A. 下載 exe（最簡單）

到 [Releases](../../releases) 下載 `檔案整理小幫手.exe`，按兩下即可，不需要安裝 Python。

> 第一次開啟若出現「Windows 已保護您的電腦」，這是因為程式沒有付費的程式碼簽章。點「其他資訊」→「仍要執行」即可。你也可以自行檢視原始碼並用 `build.bat` 自己打包。

### B. 用 Python 執行

需要 Python 3.9 以上（含 tkinter，Windows 官方安裝包預設已附）。沒有任何第三方套件。

```bash
python organizer_gui.py              # 視窗版
python organizer.py --dry-run        # 命令列：只預覽
python organizer.py "D:\某個資料夾"    # 命令列：指定資料夾，預覽後輸入 y 才執行
```

命令列版預設整理「下載」資料夾，可在 `organizer.py` 最上方修改 `TARGET_PATH` 與 `KEEP_IN_PLACE`。

### 打包成 exe

```bash
pip install -r requirements-dev.txt
build.bat
```

### 測試

```bash
python -m unittest discover tests
```

## 專案結構

| 檔案 | 說明 |
|---|---|
| `organizer_core.py` | 分類規則、安全防護、規劃與執行（兩個介面共用） |
| `organizer_gui.py` | 視窗版（tkinter） |
| `organizer.py` | 命令列版 |
| `tests/` | 核心邏輯的單元測試 |

想新增或修改分類，編輯 `organizer_core.py` 最上方的 `CATEGORIES`，兩個版本會同步生效。

## 免責聲明

本軟體會搬移與（在空資料夾時）刪除檔案。雖然已盡力加入多重防護，仍建議**整理前先備份重要資料**，並務必先看過預覽。因使用本軟體造成的任何資料損失，作者不負責任（詳見 [LICENSE](LICENSE)）。

## 授權

[MIT License](LICENSE)
