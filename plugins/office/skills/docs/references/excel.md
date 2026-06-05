# Excel 处理指南

## 目录
- [读取 .xlsx](#读取-xlsx)
- [读取 .xls（老版 Excel）](#读取-xls老版-excel)
- [编辑/创建 .xlsx](#编辑创建-xlsx)
- [行业标准规范](#行业标准规范)

> **相关文档**：环境依赖缺失时参见 `references/setup.md`

---

## 读取 .xlsx

### 使用 openpyxl

```bash
~/.local/pyoffice/bin/python -c "
import openpyxl
wb = openpyxl.load_workbook('file.xlsx')
ws = wb.active
for row in ws.iter_rows(values_only=True):
    print(row)
"
```

### 使用 pandas

```bash
~/.local/pyoffice/bin/python -c "
import pandas as pd
df = pd.read_excel('file.xlsx')
print(df.head())
"
```

---

## 读取 .xls（老版 Excel）

```bash
~/.local/pyoffice/bin/python -c "
import xlrd
wb = xlrd.open_workbook('file.xls')
ws = wb.sheet_by_index(0)
print(f'行数: {ws.nrows}, 列数: {ws.ncols}')
for row in range(ws.nrows):
    print(ws.row_values(row))
"
```

---

## 编辑/创建 .xlsx

```bash
~/.local/pyoffice/bin/python << 'PYEOF'
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

wb = openpyxl.Workbook()
ws = wb.active
ws.title = '数据表'

# 标题行
headers = ['项目', 'Q1', 'Q2', 'Q3', 'Q4', '合计']
for col, header in enumerate(headers, 1):
    cell = ws.cell(row=1, column=col, value=header)
    cell.font = Font(name='Arial', bold=True, color='FFFFFF', size=11)
    cell.fill = PatternFill(start_color='1A365D', end_color='1A365D', fill_type='solid')
    cell.alignment = Alignment(horizontal='center')

# 数据行 + 公式
data = [
    ['产品A', 100, 120, 130, 150],
    ['产品B', 80, 90, 85, 110],
    ['产品C', 60, 70, 90, 100],
]
for i, row_data in enumerate(data, 2):
    for col, value in enumerate(row_data, 1):
        ws.cell(row=i, column=col, value=value)
    # 合计列使用 Excel 公式，而非硬编码
    ws.cell(row=i, column=6, value=f'=SUM(B{i}:E{i})')

# 合计行
ws.cell(row=5, column=1, value='合计').font = Font(name='Arial', bold=True)
ws.cell(row=5, column=6, value='=SUM(B2:E5)').font = Font(name='Arial', bold=True)

# 列宽
for col in range(1, 7):
    ws.column_dimensions[get_column_letter(col)].width = 12

wb.save('report.xlsx')
print('已创建 report.xlsx')
PYEOF
```

---

## 行业标准规范

### 公式优先原则

所有计算使用 Excel 公式（如 `=SUM(B2:B9)`），不在 Python 中算出结果后硬编码。这确保用户在 Excel 中打开时可直接重新计算。

### 金融行业色彩编码

| 颜色 | 含义 | RGB |
|------|------|-----|
| 蓝色文字 | 硬编码输入/假设 | (0, 0, 255) |
| 黑色文字 | 公式计算结果 | (0, 0, 0) |
| 绿色文字 | 跨工作表引用 | (0, 128, 0) |
| 红色文字 | 外部文件链接 | (255, 0, 0) |
| 黄色背景 | 关键假设/需关注 | (255, 255, 0) |

### 数字格式

| 类型 | 格式 | 示例 |
|------|------|------|
| 年份 | 文本格式 | `"2024"` 而非 `"2,024"` |
| 被货币 | `$#,##0` | 表头注明单位如 `"收入 ($mm)"` |
| 零值 | `$#,##0;($#,##0);-` | 显示为 `-` |
| 百分比 | `0.0%` | 默认格式 |
| 倍数 | `0.0x` | EV/EBITDA、P/E |
| 负数 | 括号 `(123)` | 而非负号 `-123` |

### 交付前检查

确保无 `#REF!`、`#DIV/0!`、`#VALUE!`、`#N/A`、`#NAME?` 等公式错误。

```bash
# 检查公式错误
~/.local/pyoffice/bin/python -c "
import openpyxl
wb = openpyxl.load_workbook('report.xlsx')
for ws in wb.worksheets:
    for row in ws.iter_rows():
        for cell in row:
            if cell.value and isinstance(cell.value, str) and cell.value.startswith('#'):
                print(f'{ws.title}!{cell.coordinate}: {cell.value}')
"
```
