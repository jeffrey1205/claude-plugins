# PDF 文件操作指南

## 目录
- [合并 PDF](#合并-pdf)
- [拆分 PDF](#拆分-pdf)
- [旋转页面](#旋转页面)
- [加密解密](#加密解密)
- [从零创建](#从零创建)

> **相关文档**：PDF 内容读取与提取参见 `references/pdf-read.md`

---

## 合并 PDF

```python
~/.local/pyoffice/bin/python << 'PYEOF'
import pymupdf

def merge_pdfs(input_files, output_file):
    doc_out = pymupdf.open()
    for f in input_files:
        doc_in = pymupdf.open(f)
        doc_out.insert_pdf(doc_in)
        doc_in.close()
    doc_out.save(output_file)
    doc_out.close()
    print(f'合并完成: {output_file}')

# 使用示例：
# merge_pdfs(['a.pdf', 'b.pdf'], 'merged.pdf')
PYEOF
```

---

## 拆分 PDF

提取指定页面生成新 PDF：

```python
~/.local/pyoffice/bin/python << 'PYEOF'
import pymupdf

def extract_pages(input_file, output_file, pages):
    """pages: 页码列表，从 1 开始，如 [1, 3, 5]"""
    doc = pymupdf.open(input_file)
    doc_out = pymupdf.open()
    for p in pages:
        doc_out.insert_pdf(doc, from_page=p-1, to_page=p-1)
    doc_out.save(output_file)
    doc.close()
    doc_out.close()
    print(f'已提取页码 {pages} 到 {output_file}')

# 使用示例：
# extract_pages('input.pdf', 'extracted.pdf', [1, 3, 5])
PYEOF
```

---

## 旋转页面

```python
~/.local/pyoffice/bin/python << 'PYEOF'
import pymupdf

def rotate_pages(input_file, output_file, rotation=90):
    """rotation: 90, 180, 270"""
    doc = pymupdf.open(input_file)
    for page in doc:
        page.set_rotation(rotation)
    doc.save(output_file)
    doc.close()
    print(f'已旋转 {rotation}° 并保存到 {output_file}')

# 使用示例：
# rotate_pages('input.pdf', 'rotated.pdf', 90)
PYEOF
```

---

## 加密解密

### 加密 PDF

```python
~/.local/pyoffice/bin/python << 'PYEOF'
import pymupdf

def encrypt_pdf(input_file, output_file, user_pw='', owner_pw=''):
    doc = pymupdf.open(input_file)
    doc.save(output_file, encryption=pymupdf.PDF_ENCRYPT_AES_256,
             owner_pw=owner_pw or 'owner', user_pw=user_pw)
    doc.close()
    print(f'已加密并保存到 {output_file}')

# 使用示例：
# encrypt_pdf('input.pdf', 'encrypted.pdf', user_pw='user123', owner_pw='admin456')
PYEOF
```

### 解密 PDF（已知密码）

```python
~/.local/pyoffice/bin/python << 'PYEOF'
import pymupdf

def decrypt_pdf(input_file, output_file, password):
    doc = pymupdf.open(input_file)
    if doc.needs_pass:
        doc.authenticate(password)
    doc.save(output_file)
    doc.close()
    print(f'已解密并保存到 {output_file}')

# 使用示例：
# decrypt_pdf('encrypted.pdf', 'decrypted.pdf', 'user123')
PYEOF
```

---

## 从零创建

如需从零创建 PDF 文档（非合并/拆分），当前环境未安装 `reportlab`。

遇到此需求时安装：`uv pip install --python ~/.local/pyoffice/bin/python reportlab`

```python
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
c = canvas.Canvas('output.pdf', pagesize=A4)
c.drawString(100, 750, 'Hello PDF')
c.save()
```
