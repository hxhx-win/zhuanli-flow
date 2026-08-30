# 资料可读性与工具映射

> **被两个 skill 共享**：
> - `cn-patent-repo-scout`：S2 资料可读性预检使用本表（人工对照）
> - `cn-patent-domain-runtime`：步骤 0.1 的 `patent-env-check.py --source-root` 使用本表的格式判定与工具命令（脚本内 `EXT_READABILITY` / `EXT_TOOLS` / `INSTALL_COMMANDS` 与本表保持同步，本表为权威来源）。修改时两边一起改。

S2 资料可读性预检使用本表。涵盖（1）按格式判断"当前环境能否完整读取"的规则，（2）按操作系统给出可执行的安装命令。

## 一、按格式判断可读性

| 后缀 | 默认 Read 工具支持 | 完整读取依赖 | 缺工具时的退路 |
|------|--------------------|--------------|----------------|
| `.md` / `.txt` / `.json` / `.yaml` / `.toml` / `.csv` / `.tsv` / `.log` | ✅ 完整 | 无 | — |
| `.py` / `.js` / `.ts` / `.go` / `.java` / `.c` / `.cpp` / `.rs` / `.sh` / `.rb` 等源码 | ✅ 完整 | 无 | — |
| `.png` / `.jpg` / `.jpeg` / `.gif` / `.webp` / `.bmp` | ⚠ 加载到视觉上下文（无文本输出）；扫描件需 OCR | OCR 时需要 `tesseract`（含中文 `chi_sim` 包） | 让用户重新粘贴；或转为 base64/Data URI 后由模型直接看 |
| `.svg` | ✅ 文本即源码 | 无 | — |
| `.pdf`（数字化文本） | ⚠ Read 需要 `pdftoppm`；纯文本可用 `pdftotext` | `poppler-utils` | 用 `libreoffice --headless --convert-to txt` 兜底 |
| `.pdf`（扫描件） | ❌ 文本提取无效 | `poppler-utils` + `tesseract-ocr`（+ `chi_sim`） | 单独发图给模型 |
| `.docx` / `.pptx` / `.xlsx` | ❌ Read 不直接支持 | `unzip` + Python 抽 `<w:t>`；或 `python-docx` / `openpyxl` / `python-pptx`；或 `pandoc` | `libreoffice --headless --convert-to txt/csv/html` 兜底 |
| `.doc` / `.ppt` / `.xls`（旧二进制） | ❌ | `libreoffice` / `antiword` / `catdoc` | 让用户另存为新版 |
| `.odt` / `.ods` / `.odp` | ❌ | `libreoffice` 或 `pandoc` | — |
| `.rtf` | ❌ | `unrtf` 或 `libreoffice` | — |
| `.epub` / `.mobi` / `.azw3` | ❌ | `pandoc` 或 `calibre`（`ebook-convert`） | — |
| `.tex` / `.bib` | ✅ 源码可读 | 渲染需 `texlive`、引用需 `pandoc` | — |
| `.ipynb` | ✅ Read 直接支持 | 无 | — |
| `.zip` / `.tar.gz` / `.7z` / `.rar` | ❌ 需先解压 | `unzip` / `tar` / `p7zip` / `unrar` | — |
| `.dwg` / `.dxf`（CAD） | ❌ | `libreoffice-draw` 或专用 CAD 工具 | 出图后转 PNG/PDF |
| `.mp4` / `.mov` / `.mp3` / `.wav`（音视频） | ❌（不是本 skill 该读） | 需用户提供文字稿或字幕 | — |

**判定流程**：
1. 列出扫描根目录所有出现过的后缀及计数。
2. 对每种后缀按上表标记 `full` / `text-only` / `partial` / `unreadable`。
3. 把 `partial` / `unreadable` 的文件清单和对应缺口写入 `readability-report.md`。
4. 每个缺口给出推荐工具 + 当前 OS 的安装命令。

## 二、按操作系统的安装命令

调用前先用 `uname -s`（Linux/macOS）或 `$env:OS`（PowerShell）判断 OS，并探测包管理器：

- Linux：先 `command -v apt` / `dnf` / `pacman` / `apk`；
- macOS：`command -v brew`；缺失时提示 `xcode-select --install` 或 `https://brew.sh`；
- Windows：先 `winget --version`；缺失时回退 `choco --version`、再回退 `scoop --version`；都缺则提示用户从官方安装包安装。

下表给"工具 → 各 OS 安装命令"。`pip install` 不区分 OS。

| 工具 | Linux (apt) | Linux (dnf) | macOS (brew) | Windows (winget) | Windows (choco) | Windows (scoop) |
|------|-------------|-------------|--------------|------------------|------------------|------------------|
| poppler-utils | `sudo apt-get install -y poppler-utils` | `sudo dnf install -y poppler-utils` | `brew install poppler` | `winget install --id oschwartz10612.Poppler` | `choco install poppler` | `scoop install poppler` |
| libreoffice (headless) | `sudo apt-get install -y libreoffice --no-install-recommends` | `sudo dnf install -y libreoffice` | `brew install --cask libreoffice` | `winget install --id TheDocumentFoundation.LibreOffice` | `choco install libreoffice-fresh` | `scoop bucket add extras && scoop install libreoffice` |
| pandoc | `sudo apt-get install -y pandoc` | `sudo dnf install -y pandoc` | `brew install pandoc` | `winget install --id JohnMacFarlane.Pandoc` | `choco install pandoc` | `scoop install pandoc` |
| antiword (.doc) | `sudo apt-get install -y antiword` | `sudo dnf install -y antiword` | `brew install antiword` | 无官方包，建议改用 LibreOffice | 无 | 无 |
| catdoc (.doc/.xls/.ppt) | `sudo apt-get install -y catdoc` | `sudo dnf install -y catdoc` | `brew install catdoc` | 改用 LibreOffice | 改用 LibreOffice | 改用 LibreOffice |
| unrtf | `sudo apt-get install -y unrtf` | `sudo dnf install -y unrtf` | `brew install unrtf` | 改用 LibreOffice / pandoc | — | — |
| imagemagick | `sudo apt-get install -y imagemagick` | `sudo dnf install -y ImageMagick` | `brew install imagemagick` | `winget install --id ImageMagick.ImageMagick` | `choco install imagemagick` | `scoop install imagemagick` |
| tesseract (英文) | `sudo apt-get install -y tesseract-ocr` | `sudo dnf install -y tesseract` | `brew install tesseract` | `winget install --id UB-Mannheim.TesseractOCR` | `choco install tesseract` | `scoop install tesseract` |
| tesseract 简中包 | `sudo apt-get install -y tesseract-ocr-chi-sim` | `sudo dnf install -y tesseract-langpack-chi_sim` | `brew install tesseract-lang` | 同上安装包内勾选 `chi_sim` 语言数据 | `choco install tesseract-languages` | 手动下载 `chi_sim.traineddata` 至 tessdata 目录 |
| p7zip / 7-Zip | `sudo apt-get install -y p7zip-full` | `sudo dnf install -y p7zip p7zip-plugins` | `brew install p7zip` | `winget install --id 7zip.7zip` | `choco install 7zip` | `scoop install 7zip` |
| unrar | `sudo apt-get install -y unrar` | `sudo dnf install -y unrar` | `brew install unrar` | `winget install --id RARLab.WinRAR` | `choco install winrar` | `scoop install unrar` |
| calibre (`ebook-convert`) | `sudo apt-get install -y calibre` | `sudo dnf install -y calibre` | `brew install --cask calibre` | `winget install --id calibre.calibre` | `choco install calibre` | `scoop install calibre` |

**Python 库（跨 OS）**：

| 用途 | 命令 |
|------|------|
| `.docx` 结构化解析 | `pip install python-docx` |
| `.xlsx` 解析 | `pip install openpyxl pandas` |
| `.pptx` 解析 | `pip install python-pptx` |
| 图像处理 | `pip install pillow` |
| OCR Python 绑定 | `pip install pytesseract`（仍依赖系统 `tesseract`） |
| PDF 文本提取 | `pip install pdfminer.six pypdf` |

## 三、推荐分档

预检发现缺口后，按下面的分档向用户给"一键命令"：

### 最小够用（覆盖 PDF + docx + 图片文字提取的常见缺口）

- **Linux (apt)**：
  ```bash
  sudo apt-get install -y poppler-utils libreoffice --no-install-recommends
  pip install python-docx
  ```
- **macOS (brew)**：
  ```bash
  brew install poppler
  brew install --cask libreoffice
  pip install python-docx
  ```
- **Windows (winget, 管理员 PowerShell)**：
  ```powershell
  winget install --id oschwartz10612.Poppler
  winget install --id TheDocumentFoundation.LibreOffice
  pip install python-docx
  ```

### 完整办公文档套餐

在最小档基础上追加：

- **Linux (apt)**：`sudo apt-get install -y pandoc antiword imagemagick && pip install openpyxl pandas python-pptx`
- **macOS (brew)**：`brew install pandoc antiword imagemagick && pip install openpyxl pandas python-pptx`
- **Windows (winget)**：`winget install --id JohnMacFarlane.Pandoc ImageMagick.ImageMagick && pip install openpyxl pandas python-pptx`

### 含 OCR（扫描件 / 截图里的文字）

- **Linux (apt)**：`sudo apt-get install -y tesseract-ocr tesseract-ocr-chi-sim`
- **macOS (brew)**：`brew install tesseract tesseract-lang`
- **Windows (winget)**：`winget install --id UB-Mannheim.TesseractOCR`，安装时勾选 `chi_sim` 语言数据。

## 四、回写到 readability-report.md 的字段

```yaml
os: linux | macos | windows
package_manager: apt | dnf | brew | winget | choco | scoop | none
extensions:
  - ext: ".pdf"
    count: 2
    files: ["a.pdf", "b.pdf"]
    readability: partial   # full | text-only | partial | unreadable
    missing: ["page-images"]
    impact: "附图缺失，可能削弱『证据完备性』评分"
    install_recommendation:
      tier: "最小够用"
      command: "sudo apt-get install -y poppler-utils"
user_choice: install | accept-as-unreadable | manual-supplement
```

`recommendation-report.md` 中每个方向的"证据线索"必须引用本字段，标注哪些证据来自 `partial`/`unreadable` 资料。
