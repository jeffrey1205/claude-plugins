---
name: i18n
description: |
  将文档和文本文件从一种语言翻译为另一种语言，同时保留代码块、技术标识符、
  专业术语和文档结构。支持三种模式：粘贴文本翻译、文件路径翻译、目录批量翻译。
  只要用户提到翻译文档、本地化、国际化、转换语言、翻译文件夹、翻译文件、
  把某文件转为某语言、把某段文字翻译，都请使用此 skill。
  支持的输入包括：粘贴的文本片段、单个文件路径（.md/.txt/.json/.yaml/.conf 等）、
  整个目录。支持中文、英文、日文、韩文、法文、德文、西班牙文、俄文等语言互译。
  即使用户只说"翻译"或"translate"这样简单的词，只要上下文涉及文档或文本文件，也应使用此 skill。
---

# 文档翻译

在保持技术准确性、代码完整性和文档结构的前提下，将文档和文本文件在不同语言之间进行翻译。

## 翻译模式

自动识别用户意图，支持三种模式：

1. **粘贴文本翻译**：用户粘贴任意文本片段，指定目标语言后翻译并输出
2. **文件路径翻译**：用户指定文件路径，读取内容翻译后输出或写入新文件
3. **目录批量翻译**：用户指定源目录 + 目标目录 + 目标语言，批量翻译目录下所有支持的文件

## 支持的文件类型

| 可翻译 | `.md` `.txt` `.conf` `.ini` `.cfg` `.json` `.yaml` `.yml` `.rst` `.csv` `.log` `.xml` |
|--------|----------------------------------------------------------------------------------------|
| 不翻译（原样复制） | `.py` `.js` `.ts` `.tsx` `.go` `.html` `.jsx` `.vue` 及所有二进制文件 |

## 使用前准备

根据要翻译的文件类型，阅读对应的参考规则文件：

- 翻译 `.md` / `.rst` → 阅读 `references/file-rules/markdown.md`
- 翻译 `.txt` / `.conf` / `.ini` / `.cfg` / `.log` → 阅读 `references/file-rules/text.md`
- 翻译 `.json` / `.yaml` / `.yml` / `.csv` / `.xml` → 阅读 `references/file-rules/data.md`
- 需要了解哪些术语应保留 → 阅读 `references/terms.md`

所有术语翻译规则都在 `references/terms.md` 中，翻译前务必加载。

## 术语保护

翻译时必须保留英文的术语详见 `references/terms.md`。用户还可以在 `references/terms.md` 中添加项目专属术语，格式参考 `assets/terms.md.example`。

## 核心翻译规则

详细翻译规则按文件类型存放在 `references/file-rules/` 中，翻译前先阅读对应规则文件：

- `.md` / `.rst` → `references/file-rules/markdown.md`（YAML Front Matter、代码块免疫、标识符保护、结构保留、状态值保留）
- `.txt` / `.conf` / `.ini` / `.cfg` / `.log` → `references/file-rules/text.md`
- `.json` / `.yaml` / `.yml` / `.csv` / `.xml` → `references/file-rules/data.md`

通用规则：所有代码块不翻译，仅翻译注释；函数签名、参数名、JSON 字段名、CLI 参数、库/类名、日志字段名、DNS 记录值等标识符不翻译；表格结构、链接路径、标题层级保持不变。

## 目录批量翻译流程

1. **扫描分类**：递归扫描源目录，分为翻译类和复制类
2. **复制非翻译文件**：代码文件和二进制文件原样复制
3. **初始化状态**：创建 `translation_status.json` 追踪进度
4. **分批翻译**：每批 10-20 个文件，读取 → 应用规则 → 术语保护 → 写入 → 更新状态
5. **同步汇报**：每批后同步输出、修复路径错误、汇报进度
6. **最终报告**：输出扫描总数、成功/失败数量、复制数量、完成百分比

详细步骤参考各文件类型规则文件。

## 断点续传

如果翻译被中断：读取 `translation_status.json`，跳过 "success" 文件，继续翻译 "pending" 和 "failed" 文件。

## 翻译示例

**输入：**
```
## C2 Communication Detection

C2 beaconing is a common persistence technique used by APT groups.
By analyzing Zeek conn.log, we can identify anomalous C2 patterns.
```

**输出（中文）：**
```markdown
## C2 通信检测

C2 beaconing 是 APT 组织常用的持久化技术。
通过分析 Zeek conn.log，我们可以识别异常的 C2 通信模式。
```

## 错误处理

文件读取失败、翻译超时或写入失败时，记录为 "failed" 并继续处理下一个文件，不阻塞整个流程。
