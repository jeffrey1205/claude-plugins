# PDF 读取与提取指南

## 目录
- [文本型 PDF 提取](#文本型-pdf-提取)
- [扫描版 PDF OCR](#扫描版-pdf-ocr)
- [嵌入图片提取](#嵌入图片提取)
- [表格提取](#表格提取)

> **相关文档**：PDF 文件操作（合并/拆分/加密）参见 `references/pdf-ops.md`；独立的图片 OCR 预处理技巧参见 `references/image-ocr.md`

---

## 文本型 PDF 提取

### 快速查看 PDF 信息

```bash
pdfinfo file.pdf
```

### 快速提取文本（命令行）

```bash
pdftotext file.pdf output.txt
```

### 使用 PyMuPDF 提取

```bash
~/.local/pyoffice/bin/python << 'PYEOF'
import pymupdf

doc = pymupdf.open('file.pdf')
print(f'页数: {len(doc)}')

# 先试读第一页，判断是否有文本
first_page_text = doc[0].get_text().strip()
if first_page_text:
    print('文本型 PDF，可直接提取')
    for page in doc:
        print(page.get_text())
else:
    print('扫描版 PDF，需用 OCR，请参照下方扫描版处理流程')

doc.close()
PYEOF
```

### 中文字体问题

PyMuPDF 新版 (>=1.26) 已内置 CJK 字体支持，直接调用 `get_text()` 即可正常提取中文。

若遇乱码或特殊字体 PDF，可用备选方案：
- **命令行**: `pdftotext file.pdf output.txt`
- **OCR**: 渲染为图片后用 tesseract（见下方扫描版处理）

---

### get_text 参数详解

```python
import pymupdf
doc = pymupdf.open('file.pdf')
page = doc[0]

# 1. 基本提取（纯文本）
text = page.get_text()  # 或 page.get_text("text")

# 2. 按阅读顺序提取（多栏 PDF 推荐）
text = page.get_text("text", sort=True)

# 3. blocks 格式：返回坐标+文本列表，便于精确定位
blocks = page.get_text("blocks", sort=True)
# 每个 block: (x0, y0, x1, y1, text, block_no, block_type)
for b in blocks:
    print(f"位置: ({b[0]:.1f}, {b[1]:.1f}) → 文本: {b[4][:50]}")

# 4. dict 格式：包含字体、大小、颜色等详细信息
d = page.get_text("dict")
for block in d["blocks"]:
    for line in block["lines"]:
        for span in line["spans"]:
            print(f"字体: {span['font']}, 大小: {span['size']}, 文本: {span['text']}")

# 5. 常用 flags 组合
text = page.get_text("text", flags=pymupdf.TEXT_PRESERVE_WHITESPACE)
text = page.get_text("text", flags=pymupdf.TEXT_DEHYPHENATE)  # 去除连字符断行
```

---

## 扫描版 PDF OCR

### 单页 OCR

```bash
# 渲染 PDF 页面为图片
~/.local/pyoffice/bin/python << 'PYEOF'
import pymupdf

doc = pymupdf.open('file.pdf')
page = doc[0]  # 第 1 页，索引从 0 开始
pix = page.get_pixmap(dpi=200)
pix.save('/tmp/ocr_page.png')
print('已渲染为图片: /tmp/ocr_page.png')
doc.close()
PYEOF

# OCR 识别（中文+英文）
tesseract /tmp/ocr_page.png output -l chi_sim+eng
cat output.txt
```

### OCR 图像预处理（提升识别率）

> **更多预处理技巧**：参见 `references/image-ocr.md`

```bash
~/.local/pyoffice/bin/python << 'PYEOF'
import cv2
img = cv2.imread('/tmp/ocr_page.png')
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
# Otsu 二值化
_, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
# 降噪
denoised = cv2.fastNlMeansDenoising(binary)
cv2.imwrite('/tmp/ocr_page_preprocessed.png', denoised)
print('预处理完成: /tmp/ocr_page_preprocessed.png')
PYEOF

# 使用预处理后的图片进行 OCR
tesseract /tmp/ocr_page_preprocessed.png output -l chi_sim+eng
cat output.txt
```

### 批量 OCR 全部页面（含混合型 PDF）

```python
~/.local/pyoffice/bin/python << 'PYEOF'
import subprocess
import os
import pymupdf

doc = pymupdf.open('file.pdf')
os.makedirs('/tmp/ocr_pages', exist_ok=True)
all_text = []

for i in range(len(doc)):
    page = doc[i]
    # 先尝试直接提取文本
    text = page.get_text().strip()
    if text:
        all_text.append(text)
        print(f'[第{i+1}页] 直接提取: {len(text)} 字符')
    else:
        # 渲染为图片后 OCR
        pix = page.get_pixmap(dpi=200)
        img_path = f'/tmp/ocr_pages/page_{i+1}.png'
        pix.save(img_path)
        result = subprocess.run(
            ['tesseract', img_path, 'stdout', '-l', 'chi_sim+eng'],
            capture_output=True, text=True, timeout=60
        )
        ocr_text = result.stdout.strip()
        all_text.append(ocr_text)
        print(f'[第{i+1}页] OCR: {len(ocr_text)} 字符')

doc.close()

# 输出完整文本
with open('file_ocr_result.txt', 'w') as f:
    f.write('\n\n--- page break ---\n\n'.join(all_text))
print(f'\nOCR 完成，共 {len(doc)} 页，结果保存至 file_ocr_result.txt')
PYEOF
```

### 性能提示

- 扫描版 OCR 较慢，大文件建议先 `pdfinfo` 查看页数，按需处理部分页面
- `dpi=200` 是精度与速度的平衡点，可适当调整（150 更快，300 更准但更慢）

---

## 嵌入图片提取

### 使用 pdfimages 命令行工具

```bash
mkdir -p pdf_images
pdfimages -png file.pdf pdf_images/image
```

### 使用 PyMuPDF 提取

```bash
~/.local/pyoffice/bin/python << 'PYEOF'
import pymupdf
import os

doc = pymupdf.open('file.pdf')
os.makedirs('pdf_images', exist_ok=True)
img_count = 0

for page_num in range(len(doc)):
    page = doc[page_num]
    images = page.get_images(full=True)
    img_count += len(images)
    for img_index, img in enumerate(images):
        xref = img[0]
        pix = pymupdf.Pixmap(doc, xref)
        if pix.n - pix.alpha > 3:  # CMYK 转 RGB
            pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
        pix.save(f'pdf_images/page{page_num+1}_img{img_index}.png')
        print(f'提取: page{page_num+1}_img{img_index}.png ({pix.width}x{pix.height})')

doc.close()
print(f'共提取 {img_count} 张图片')
PYEOF
```

> **注意**：`pdfimages` 是命令行工具(poppler-utils 的一部分)，适合快速提取。PyMuPDF 方案可在代码中精确控制输出格式和路径。

---

## 表格提取

如需从 PDF 中提取结构化表格数据（尤其是带边框的表格），当前环境未安装 `pdfplumber`。

遇到此需求时安装：`pip install pdfplumber`

```python
import pdfplumber
with pdfplumber.open('file.pdf') as pdf:
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            print(table)
```
