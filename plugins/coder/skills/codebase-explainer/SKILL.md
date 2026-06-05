---
name: codebase-explainer
description: |
  分析陌生代码库，生成结构化的代码理解文档。支持 C/Go/Python/JavaScript/TypeScript/Bash。
  输出分层文档：概览层、结构层、流程层、API层、开发指南。
  
  **触发场景**：当用户需要理解陌生代码库、分析项目结构、梳理模块职责、生成代码文档时，务必使用此 skill。
  具体包括：用户提到"理解代码"、"分析项目"、"看懂模块"、"生成文档"、"梳理结构"、"这个项目是做什么的"、"帮我了解这个仓库"、"解释一下这个模块"、"代码结构是什么"等关键词，或用户刚接手一个新项目、需要在陌生代码库中快速定位、想要了解某个目录的功能边界。
  
  即使用户没有明确说"生成文档"，只要涉及代码理解、项目探索、模块分析的需求，都应优先使用此 skill。
  
  **不触发**：纯功能开发、Bug修复（用常规开发流程）、性能分析（用 performance-review）、文档编辑（用 office）。
---

# 代码理解 Skill

分析陌生代码库，生成结构化的代码理解文档。

## 使用原则

1. **分层输出**：按概览→结构→流程→API→指南的顺序，用户可通过 `--focus` 指定侧重。
2. **版本锁定**：文档头部标注生成时的源标识（git commit 或目录 hash），便于判断过期。
3. **双通道输出**：终端输出摘要，同时生成 Markdown 文件供存档。

## 读取路径

只在需要时读取对应参考文件：
- 需要识别语言入口/模块时，读取 `references/language-patterns.md`
- 需要生成文档时，读取 `references/doc-template.md`
- 需要提取核心流程时，读取 `references/flow-extraction.md`

## 触发示例

**应该触发**：
- "帮我理解这个项目是做什么的"
- "分析一下这个模块的代码结构"
- "看懂这个 gateway 服务的设计"
- "生成这个仓库的代码文档"
- "梳理一下 src/auth 目录的职责"

**不应该触发**：
- "帮我实现一个新功能"
- "修复这个 bug"
- "这个服务 CPU 很高，帮我分析"（用 performance-review）
- "把这个 PDF 转成 Word"（用 office）

## 工作流程

```
输入路径 → 探测阶段 → 入口分析 → 依赖分析 → 流程提取 → 文档生成
    ↓          ↓          ↓          ↓          ↓          ↓
  检测范围   识别语言栈  找入口文件  构建依赖图  跟踪调用链  输出 Markdown
```

**阶段说明**：
1. **探测阶段**：扫描目录结构，识别语言栈、构建工具、版本控制状态
2. **入口分析**：识别入口文件、模块边界、配置信息
3. **依赖分析**：构建依赖图、识别外部依赖、标记核心模块
4. **流程提取**：跟踪核心调用链、识别业务流程、提取数据模型
5. **文档生成**：按分层结构输出 Markdown，同时终端输出摘要

## 参数说明

```
/codebase-explainer [path] [--focus architecture|flow|api|guide|all] [--output <file>] [--include <path>]
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `path` | 分析目标路径 | 当前目录 |
| `--focus` | 侧重层级 | all |
| `--output` | 输出文件路径 | `<项目名>-explainer.md` |
| `--include` | 关联项目路径 | 无 |

**--focus 选项**：
- `architecture`：仅输出概览层 + 结构层
- `flow`：仅输出流程层
- `api`：仅输出 API 层
- `guide`：仅输出开发指南
- `all`：完整文档（默认）

## 输入范围

| 粒度 | 说明 | 示例 |
|------|------|------|
| 整个项目 | 分析整个代码库 | `/codebase-explainer .` |
| 单个模块 | 分析特定目录 | `/codebase-explainer ./src/auth` |
| 单个文件 | 分析特定文件 | `/codebase-explainer ./main.go` |
| 关联项目 | 包含关联目录 | `/codebase-explainer . --include ../shared` |

## 阶段1: 探测

### 1.1 目录扫描

扫描目标目录结构，识别：
- 文件扩展名分布
- 构建工具配置文件
- 版本控制状态

### 1.2 语言栈识别

根据 `references/language-patterns.md` 中的规则，识别主要语言：

| 检查项 | 标识文件 |
|--------|----------|
| Go | `go.mod` |
| Python | `pyproject.toml`, `requirements.txt`, `setup.py` |
| C | `Makefile`, `CMakeLists.txt` |
| JavaScript/TypeScript | `package.json` |
| Bash | `*.sh` 文件 |

### 1.3 版本标识

- Git 仓库：获取 `git rev-parse HEAD` 和 `git branch --show-current`
- 非 Git 目录：计算关键文件的 SHA256 hash 摘要

## 阶段2: 入口分析

根据 `references/language-patterns.md` 识别入口文件：

| 语言 | 入口特征 |
|------|----------|
| Go | `func main()`，`package main` |
| Python | `if __name__ == "__main__"`，`__init__.py` |
| C | `int main()` |
| JavaScript/TypeScript | `package.json` scripts.entry |
| Bash | 脚本文件本身 |

识别模块边界：
- Go：`package` 声明
- Python：`__init__.py` 目录
- C：头文件目录
- JS/TS：`import/export` 边界

## 阶段3: 依赖分析

构建依赖图：
- 读取 `import`/`include`/`source` 语句
- 识别外部依赖（第三方库）
- 标记核心模块（高频被依赖）

输出依赖关系图（ASCII 或 Mermaid）。

## 阶段4: 流程提取

根据 `references/flow-extraction.md` 提取核心流程：
- 跟踪入口到核心功能的调用链
- 识别数据流（输入→处理→输出）
- 提取关键数据结构

## 阶段5: 文档生成

根据 `references/doc-template.md` 生成文档：
- 按分层结构组织内容
- 在文档头部标注版本标识
- 同时在终端输出摘要

## 输出要求

**终端输出**：简洁摘要，包含：
- 项目定位（一句话）
- 技术栈清单
- 核心模块列表
- 文档保存路径

**Markdown 文件**：完整分层文档，包含：
- 版本标识头
- 概览层、结构层、流程层、API层、开发指南
- 架构图（ASCII/Mermaid）
- 依赖关系图

## 目录结构

```
codebase-explainer/
├── SKILL.md                    # 本文件
└── references/
    ├── language-patterns.md    # 语言识别规则
    ├── doc-template.md         # 文档模板
    └── flow-extraction.md      # 流程提取策略
```