---
name: docs
description: |
  当用户要直接处理文档或扫描件时触发：Word (.doc/.docx)、PowerPoint (.pptx)、PDF、Excel (.xlsx/.xls)、图片。典型任务包括读取或提取文本、OCR 识别、提取表格或图片、修改格式或内容、生成或转换文档、合并或拆分 PDF；只要用户的主要对象是文档文件本身，或最终交付物是这些文档或其内容结果，就使用此 skill。
  不触发：如果核心需求是开发脚本、网页应用、数据管道或数据库查询，而文档只是次要输入、附件或顺带导出结果，则不要触发。
---

# 文档处理工具 Skill

本 skill 提供宿主机上已安装的文档处理工具清单和使用指引，确保正确调用各库和命令行工具。

## 工作流程

1. **识别文件类型** → 选择对应的参考文档
2. **检测环境依赖** → 如缺失则读取 setup.md 安装
3. **调用合适工具** → 完成用户任务

## 按文件类型选择参考文档

用户任务涉及以下文件类型时，读取对应的参考文档：

| 文件类型 | 参考文档 | 典型任务 |
|----------|----------|----------|
| Word (.docx/.doc) | references/word.md | 读取、创建、编辑 Word 文档 |
| PowerPoint (.pptx) | references/ppt.md | 创建演示文稿、提取幻灯片内容 |
| PDF - 读取/提取 | references/pdf-read.md | 提取文本、OCR、图片、表格 |
| PDF - 操作 | references/pdf-ops.md | 合并、拆分、加密、从零创建 |
| Excel (.xlsx/.xls) | references/excel.md | 读取表格、创建报表、数据分析 |
| 图片/OCR | references/image-ocr.md | 图片处理、文字识别 |

> **环境依赖缺失？** 读取 `references/setup.md` 查看安装步骤。

## 环境依赖分组

本 skill 的依赖分为两组：

| 分组 | 用途 | 默认策略 |
|------|------|----------|
| 基础 Office | Word、PowerPoint、Excel、老版 `.doc/.xls` 读取 | 默认检测与安装 |
| PDF / 图片 / OCR | PDF 读取与操作、图片 OCR、扫描版 PDF OCR | 仅在任务涉及 PDF 或图片 OCR 时检测；安装前需用户确认，或只提供命令 |

## 环境检测

### 基础 Office 依赖检测

默认只检测基础 Office 依赖，用于确认 Word/PPT/Excel 处理能力是否可用：

```bash
# 检测 uv 虚拟环境中的基础 Office Python 库
~/.local/pyoffice/bin/python -c "import docx, pptx, openpyxl, xlrd, pandas; print('Base Office libs OK')" 2>/dev/null || echo "MISSING: base office python libs"

# 检测基础 Office 命令行工具
for cmd in antiword catdoc; do
  command -v $cmd >/dev/null 2>&1 || echo "MISSING: $cmd"
done
```

### PDF / 图片 / OCR 可选依赖检测

当任务涉及 PDF、图片 OCR、扫描版 PDF 或 PDF 嵌入图片提取时，再运行以下检测：

```bash
# 检测 uv 虚拟环境中的 PDF / 图片 / OCR Python 库
~/.local/pyoffice/bin/python -c "import PIL, cv2, pytesseract, pymupdf; print('PDF/Image libs OK')" 2>/dev/null || echo "MISSING: pdf/image python libs"

# 检测 PDF / OCR 命令行工具
for cmd in tesseract pdftotext pdfinfo pdfimages; do
  command -v $cmd >/dev/null 2>&1 || echo "MISSING: $cmd"
done
```

> **提示**：如果 PDF / 图片 / OCR 依赖缺失，先询问用户是否安装。用户确认后执行安装；如果用户不想安装，只提供安装命令。

## 工具速查

### Python 环境

所有 Python 库统一安装在 uv 虚拟环境中：

| 环境 | 路径 | 说明 |
|------|------|------|
| uv 虚拟环境 | `~/.local/pyoffice/bin/python` | 所有库需显式调用 |

### 可调用的 Python 库

**使用 uv 虚拟环境调用**（`~/.local/pyoffice/bin/python -c "import xxx"`）：

#### 基础 Office 库

| 库 | 用途 | 示例 |
|----|------|------|
| `docx` (python-docx) | Word .docx 读写、格式、表格、TOC | `from docx import Document` |
| `pptx` (python-pptx) | PowerPoint .pptx 读写、母版、布局 | `from pptx import Presentation` |
| `openpyxl` | Excel .xlsx 读写、格式化、公式 | `import openpyxl` |
| `xlrd` | Excel 旧版 .xls 读取 | `import xlrd` |
| `pandas` | 数据分析、表格导出 | `import pandas as pd` |

#### PDF / 图片 / OCR 可选库

这些库仅在处理 PDF、图片或 OCR 时安装和使用：

| 库 | 用途 | 示例 |
|----|------|------|
| `pymupdf` (PyMuPDF) | PDF 读写、文本提取、页面渲染、合并/拆分/加密 | `import pymupdf` |
| `PIL` (pillow) | 图片处理、格式转换、OCR 预处理 | `from PIL import Image` |
| `cv2` (opencv-headless) | 图像处理、OCR 预处理（二值化、去噪） | `import cv2` |
| `pytesseract` | OCR 引擎接口 | `import pytesseract` |

### 命令行工具

#### 基础 Office 工具

| 命令 | 路径 | 用途 |
|------|------|------|
| `antiword` | `/usr/bin/antiword` | 老版 `.doc` 文件转文本 |
| `catdoc` | `/usr/bin/catdoc` | 老版 `.doc` 备选读取（兼容性更好，尤其 WPS 创建的文档） |

#### PDF / OCR 可选工具

这些工具仅在处理 PDF、图片或 OCR 时安装和使用：

| 命令 | 路径 | 用途 |
|------|------|------|
| `tesseract` | `/usr/bin/tesseract` | OCR 识别（支持 `-l eng` / `-l chi_sim`） |
| `pdftotext` | `/usr/bin/pdftotext` | PDF 文本提取 |
| `pdfinfo` | `/usr/bin/pdfinfo` | PDF 元信息查看 |
| `pdfimages` | `/usr/bin/pdfimages` | PDF 嵌入图片提取 |

## 注意事项

1. **PyMuPDF 导入**：使用 `import pymupdf`（pip 安装的最新版）。
2. **调用路径**：所有 Python 库 **必须**使用 `~/.local/pyoffice/bin/python` 调用。
3. **中文 OCR**：tesseract 已安装 `chi_sim` 语言包，使用时加 `-l chi_sim` 或 `lang='chi_sim'`。
4. **老版 .doc**：先用 `antiword` 尝试，失败时换 `catdoc`（对 WPS 创建的 `.doc` 兼容性更好）。
5. **无 GUI**：opencv 使用的是 `opencv-python-headless`，不支持 `cv2.imshow()` 等需要显示器的操作，用 `cv2.imwrite()` 保存结果。
6. **PPT 幻灯片遍历**：`prs.slides` 不支持切片操作，需用计数器或 `itertools.islice`。
7. **Excel 公式**：使用 Excel 公式而非 Python 硬编码计算结果，确保文件可在 Excel 中重新计算。
