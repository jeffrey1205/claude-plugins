---
name: codegraph
description: 使用 CodeGraph 语义代码图谱（codegraph_explore）来理解代码结构、调用链和影响范围。当用户问"怎么工作"、"调用链"、"影响范围"、"架构"、"谁调用了"、"改了会怎样"、"how does X work"、"blast radius"、"callers"、"callers of"、"what calls"、"impact of changing"等结构性代码理解问题时使用。也适用于探索不熟悉的代码库、追踪跨文件调用路径、分析修改影响面。不适用于简单的文件内容读取、语法问题、非代码任务。
---

# CodeGraph 语义代码图谱

## 核心原则

**CodeGraph 已经做过探索工作了 — 你不需要重复它。**

当项目存在 `.codegraph/` 目录时，CodeGraph 已经预构建了整个代码库的知识图谱（符号、调用边、依赖关系）。用一次 `codegraph_explore` 调用就能返回精确的源码和调用路径，替代 5-30 次 grep/read/glob 的文件逐个探索。

## 何时使用 codegraph_explore

**使用 codegraph_explore：**
- "X 是怎么工作的？" — 理解模块/功能的实现
- "请求从 A 怎么到达 B？" — 追踪调用流程
- "谁调用了 X？" — 查找调用者
- "改 X 会影响什么？" — 影响范围分析
- "这个代码库的架构是什么？" — 整体结构理解
- 探索不熟悉的代码区域
- 需要跨多个文件理解调用路径

**使用内置工具（grep/read/glob）：**
- 读取已知路径的单个文件内容
- 搜索配置文件、非代码文件
- 简单的字符串匹配（如找某个环境变量名）
- 项目没有 `.codegraph/` 目录时

**判断方法：** 如果问题需要理解"代码之间的关系"（调用、依赖、影响），用 codegraph_explore。如果只是"找到某个文件/字符串"，用内置工具。

## 如何调用

```
工具: codegraph_explore
参数:
  query: 自然语言描述你要理解的内容
         - "How does the authentication middleware work?"
         - "What calls UserService.create and what does it call?"
         - "How does a request flow from the router to the database?"
         - "src/auth/login.ts" （直接传文件路径也能读取源码）
         - "handleLogin" （传符号名获取其源码和调用关系）
  projectPath: (可选) 项目路径，默认当前目录
```

**调用示例：**

```
# 理解一个功能怎么工作
codegraph_explore(query="How does the payment processing flow work?")

# 追踪调用链
codegraph_explore(query="What calls validateUser and what does it call?")

# 分析修改影响
codegraph_explore(query="What would be affected if I change the DatabaseConnection class?")

# 读取特定文件/符号的源码
codegraph_explore(query="src/services/auth.ts")
codegraph_explore(query="handleLogin function")
```

## 如何解读结果

codegraph_explore 返回：
1. **相关符号的源码** — 按文件分组，带行号，可直接引用
2. **调用路径** — 符号之间的调用关系（包括动态分发，如回调、接口实现）
3. **影响范围摘要** — 修改某符号会影响的代码范围

**关键：将返回的源码视为已经用 Read 工具读过的内容。** 不需要再用 `read` 工具重新读取同样的文件来"验证"。

## 禁忌

1. **不要用 grep/read 验证 codegraph_explore 的结果** — 信任返回的源码，它来自预构建的索引，是准确的
2. **不要委派给 explore 子 agent** — 子 agent 看不到 MCP 工具，会退回到文件逐个读取，完全失去 CodeGraph 的优势。直接在主 agent 中调用 codegraph_explore
3. **不要在没有 `.codegraph/` 的项目中尝试** — 先用 `ls .codegraph` 确认索引存在
4. **不要用 codegraph_explore 做简单的文件查找** — 如果你已经知道文件路径，直接用 read 工具

## CLI 回退

如果 MCP 工具不可用，可以用 bash 调用等效的 CLI 命令：

```bash
# 语义探索（等同 codegraph_explore MCP 工具）
codegraph explore "How does the auth flow work?"

# 查看符号的调用者
codegraph callers UserService.create

# 查看符号调用了什么
codegraph callees handleLogin

# 影响分析
codegraph impact DatabaseConnection

# 全文搜索符号
codegraph query "UserService"
```
