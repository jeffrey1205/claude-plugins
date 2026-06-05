# Word 处理指南

## 目录
- [读取 .docx](#读取-docx)
- [从零创建 .docx](#从零创建-docx)
- [编辑现有 .docx](#编辑现有-docx)
- [老版 .doc 转文本](#老版-doc-转文本)
- [高级技巧](#高级技巧)

> **相关文档**：环境依赖缺失时参见 `references/setup.md`

---

## 读取 .docx

```bash
# 读取 .docx（使用 uv 环境的 python）
~/.local/pyoffice/bin/python -c "
from docx import Document
doc = Document('file.docx')
for p in doc.paragraphs:
    print(p.text)
for t in doc.tables:
    for row in t.rows:
        print([c.text for c in row.cells])
"
```

---

## 从零创建 .docx

```bash
~/.local/pyoffice/bin/python << 'PYEOF'
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

doc = Document()

# 设置默认字体
style = doc.styles['Normal']
font = style.font
font.name = 'Arial'
font.size = Pt(12)
style.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

# 标题
doc.add_heading('文档标题', level=1)
doc.add_heading('子标题', level=2)

# 段落
p = doc.add_paragraph('这是正文段落。')
p.paragraph_format.space_after = Pt(6)

# 表格
table = doc.add_table(rows=3, cols=3, style='Light Shading Accent 1')
table.alignment = WD_TABLE_ALIGNMENT.CENTER
data = [['姓名', '部门', '业绩'], ['张三', '技术部', '100'], ['李四', '市场部', '85']]
for i, row_data in enumerate(data):
    for j, cell_text in enumerate(row_data):
        table.cell(i, j).text = cell_text

# 页眉
section = doc.sections[0]
header = section.header
header.paragraphs[0].text = '公司名称 | 机密文档'

# 保存
doc.save('output.docx')
print('已创建 output.docx')
PYEOF
```

---

## 编辑现有 .docx

```bash
~/.local/pyoffice/bin/python << 'PYEOF'
from docx import Document
from docx.shared import Pt

doc = Document('existing.docx')

# 替换特定段落的文本
for p in doc.paragraphs:
    if '旧文本' in p.text:
        # 保留格式，只替换文字
        for run in p.runs:
            if '旧文本' in run.text:
                run.text = run.text.replace('旧文本', '新文本')

# 修改表格内容
for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                if '待修改' in p.text:
                    for run in p.runs:
                        run.text = run.text.replace('待修改', '已更新')

# 添加新段落
p = doc.add_paragraph('新增内容')
p.style = doc.styles['Normal']

doc.save('output.docx')
PYEOF
```

---

## 老版 .doc 转文本

```bash
antiword file.doc 2>/dev/null || catdoc file.doc
```

---

## 高级技巧

### 页面尺寸设置

```bash
~/.local/pyoffice/bin/python << 'PYEOF'
from docx import Document
from docx.shared import Inches, Pt

doc = Document()
section = doc.sections[0]

# A4 页面（默认）
section.page_width = Inches(8.27)
section.page_height = Inches(11.69)

# US Letter 页面
# section.page_width = Inches(8.5)
# section.page_height = Inches(11)

# 页边距
section.top_margin = Inches(1)
section.bottom_margin = Inches(1)
section.left_margin = Inches(1.25)
section.right_margin = Inches(1.25)
PYEOF
```

### 表格列宽精确控制

```bash
~/.local/pyoffice/bin/python << 'PYEOF'
from docx import Document
from docx.shared import Inches, Pt
from docx.oxml.shared import qn
from docx.oxml import OxmlElement

doc = Document()
table = doc.add_table(rows=2, cols=3, style='Table Grid')

# 设置列宽
widths = [Inches(1.5), Inches(2), Inches(2.5)]
for row in table.rows:
    for idx, width in enumerate(widths):
        cell = row.cells[idx]
        cell.width = width
        # 确保宽度生效
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        tcW = tcPr.find(qn('w:tcW'))
        if tcW is None:
            tcW = OxmlElement('w:tcW')
            tcW.set(qn('w:type'), 'dxa')
            tcW.set(qn('w:w'), str(int(width / Pt(1) * 20)))
            tcPr.append(tcW)

doc.save('table.docx')
PYEOF
```

### 专业排版：smart quotes

使用 Unicode 字符而非 ASCII 引号：
- 左双引号: `"` (U+201C)
- 右双引号: `"` (U+201D)
- 右单引号: `'` (U+2019)

python-docx 直接输入 Unicode 字符即可。
