# PowerPoint 处理指南

## 目录
- [读取 .pptx](#读取-pptx)
- [从零创建 .pptx](#从零创建-pptx)
- [设计规范](#设计规范)

> **相关文档**：环境依赖缺失时参见 `references/setup.md`

---

## 读取 .pptx

```bash
~/.local/pyoffice/bin/python -c "
from pptx import Presentation
prs = Presentation('file.pptx')
print(f'幻灯片数: {len(prs.slides)}')
for i, slide in enumerate(prs.slides):
    print(f'\n--- 幻灯片 {i+1} ---')
    for shape in slide.shapes:
        if shape.has_text_frame:
            print(shape.text)
"
```

> **注意**：`prs.slides` **不支持切片**（如 `prs.slides[:3]` 会报 `AttributeError`），必须逐张遍历。如需只读前 N 张，用计数器：

```python
from itertools import islice
for slide in islice(prs.slides, 3):  # 只读前 3 张
    ...
```

---

## 从零创建 .pptx

```bash
~/.local/pyoffice/bin/python << 'PYEOF'
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

prs = Presentation()
prs.slide_width = Inches(13.333)  # 16:9 宽屏
prs.slide_height = Inches(7.5)

# 添加标题幻灯片
slide_layout = prs.slide_layouts[0]  # 标题版式
slide = prs.slides.add_slide(slide_layout)

title = slide.shapes.title
title.text = '演示文稿标题'
title.text_frame.paragraphs[0].font.size = Pt(44)
title.text_frame.paragraphs[0].font.bold = True
title.text_frame.paragraphs[0].font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)

subtitle = slide.placeholders[1]
subtitle.text = '副标题 | 演讲者姓名'
subtitle.text_frame.paragraphs[0].font.size = Pt(24)

# 添加内容幻灯片
slide_layout = prs.slide_layouts[1]  # 标题+内容版式
slide = prs.slides.add_slide(slide_layout)

title = slide.shapes.title
title.text = '关键要点'

body = slide.placeholders[1]
tf = body.text_frame
tf.word_wrap = True

items = ['第一点核心信息', '第二点数据支撑', '第三点结论']
for i, item in enumerate(items):
    if i == 0:
        p = tf.paragraphs[0]
    else:
        p = tf.add_paragraph()
    p.text = item
    p.font.size = Pt(20)
    p.space_after = Pt(12)

prs.save('presentation.pptx')
print('已创建 presentation.pptx')
PYEOF
```

---

## 设计规范

### 字号标准

- 标题：36-44pt
- 副标题/分区标题：20-24pt
- 正文：14-16pt
- 备注/引用：12pt

### 布局建议

- 双栏布局
- 图文并排
- 图标+简短文字
- **避免**：纯文字幻灯片和居中大段正文

### 配色方案

| 主题 | 标题色 | 强调色 |
|------|--------|--------|
| 深蓝 | `#1A365D` | `#2B6CB0` |
| 深绿 | `#22543D` | `#38A169` |
| 活力橙 | `#C05621` | `#DD6B20` |

### 母版/布局

通过 `prs.slide_layouts[index]` 选择预设布局：
- `0`：标题版式
- `1`：标题+内容版式
- `2`：两栏内容版式
