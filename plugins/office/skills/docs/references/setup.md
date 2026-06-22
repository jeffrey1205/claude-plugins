# 环境安装指南

## 目录
- [第一步：创建 uv 虚拟环境](#第一步创建-uv-虚拟环境)
- [第二步：安装基础 Office Python 库](#第二步安装基础-office-python-库)
- [第三步：安装基础 Office 系统命令行工具](#第三步安装基础-office-系统命令行工具需要-sudo)
- [第四步：可选安装 PDF / 图片 / OCR Python 库](#第四步可选安装-pdf--图片--ocr-python-库)
- [第五步：可选安装 PDF / OCR 系统命令行工具](#第五步可选安装-pdf--ocr-系统命令行工具需要-sudo)
- [第六步：按需安装扩展库](#第六步按需安装扩展库)
- [第七步：验证](#第七步验证)
- [注意事项](#注意事项)

---

## 第一步：创建 uv 虚拟环境

```bash
# 创建虚拟环境（如已存在可跳过）
uv venv ~/.local/pyoffice --python python3
```

---

## 第二步：安装基础 Office Python 库

默认只安装 Word、PowerPoint、Excel 相关 Python 库：

```bash
uv pip install --upgrade --python ~/.local/pyoffice/bin/python --no-cache --link-mode=copy \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    python-docx python-pptx openpyxl xlrd pandas
```

---

## 第三步：安装基础 Office 系统命令行工具（需要 sudo）

用于读取老版 `.doc` 文件：

```bash
sudo apt install -y antiword catdoc
```

---

## 第四步：可选安装 PDF / 图片 / OCR Python 库

仅当任务涉及 PDF、图片 OCR、扫描版 PDF OCR 或 PDF 嵌入图片提取时安装：

```bash
uv pip install --upgrade --python ~/.local/pyoffice/bin/python --no-cache --link-mode=copy \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    pymupdf pillow opencv-python-headless pytesseract
```

---

## 第五步：可选安装 PDF / OCR 系统命令行工具（需要 sudo）

仅当任务涉及 PDF 或 OCR 时安装：

```bash
sudo apt install -y poppler-utils \
    tesseract-ocr tesseract-ocr-eng tesseract-ocr-chi-sim
```

---

## 第六步：按需安装扩展库

### PDF 表格提取

当前基础环境不默认安装 `pdfplumber`。如需从 PDF 中提取结构化表格数据，可按需安装：

```bash
uv pip install --python ~/.local/pyoffice/bin/python pdfplumber
```

### 从零创建 PDF

当前基础环境不默认安装 `reportlab`。如需从零创建 PDF，可按需安装：

```bash
uv pip install --python ~/.local/pyoffice/bin/python reportlab
```

---

## 第七步：验证

重新运行 `SKILL.md` 中的环境检测脚本。

默认只需验证基础 Office 依赖：

```bash
~/.local/pyoffice/bin/python -c "import docx, pptx, openpyxl, xlrd, pandas; print('Base Office libs OK')" 2>/dev/null || echo "MISSING: base office python libs"

for cmd in antiword catdoc; do
  command -v $cmd >/dev/null 2>&1 || echo "MISSING: $cmd"
done
```

如果已安装可选依赖，再验证 PDF / 图片 / OCR：

```bash
~/.local/pyoffice/bin/python -c "import PIL, cv2, pytesseract, pymupdf; print('PDF/Image libs OK')" 2>/dev/null || echo "MISSING: pdf/image python libs"

for cmd in tesseract pdftotext pdfinfo pdfimages; do
  command -v $cmd >/dev/null 2>&1 || echo "MISSING: $cmd"
done
```

---

## 注意事项

- 如果当前机器没有 `uv`，先安装：`curl -LsSf https://astral.sh/uv/install.sh | sh`
- 所有 Python 库统一在 `~/.local/pyoffice` 虚拟环境中管理，使用 `~/.local/pyoffice/bin/python` 调用
- 默认安装只保证基础 Office 功能：Word、PowerPoint、Excel、老版 `.doc/.xls`
- PDF、图片和 OCR 依赖属于可选能力；默认不自动安装，安装前应先询问用户确认
- 如果用户不想安装 PDF / 图片 / OCR 依赖，只提供安装命令，不自动执行
- 如果是 Debian 系以外的 Linux，apt 包名可能不同，需酌情调整
