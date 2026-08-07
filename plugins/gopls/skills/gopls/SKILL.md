---
name: gopls
description: 使用 gopls MCP 工具进行精确的 Go 代码语义分析。当处理 Go 语言项目时，遇到"找定义"、"找引用"、"谁调用了"、"重构重命名"、"编译错误"、"安全漏洞"、"包的 API"、"项目结构"等问题时使用。替代 grep/read 进行 Go 代码搜索，100% 精确无误报。仅适用于 Go 语言项目（存在 go.mod 的项目）。
---

# gopls 语义代码工具

## 核心原则

**gopls 是 Go 官方语言服务器，理解代码的 AST 和类型系统 — 不是文本搜索。**

在 Go 项目中，用 gopls MCP 工具替代 grep/read 做代码搜索和分析。gopls 基于编译器级别的语法树和类型绑定，100% 精确，零误报，且极度节省 Token。

## 前置检查

使用前确认项目是 Go 项目：
- 存在 `go.mod` 文件
- 或存在 `go.work` 文件（多模块工作区）

## 8 个工具速查

| 工具 | 用途 | 替代什么 |
|------|------|----------|
| `go_workspace` | 项目模块架构、依赖拓扑 | `ls` + 逐个读 `go.mod` |
| `go_search` | 全局符号搜索（结构体、接口、函数） | `grep` 搜代码 |
| `go_package_api` | 包的导出 API 签名和文档 | `read` 整个包的源码 |
| `go_symbol_references` | 查找符号的所有引用位置 | `grep` 搜引用 |
| `go_file_context` | 文件结构骨架（导入、类型、方法） | `read` 整个大文件 |
| `go_rename_symbol` | AST 级安全重命名 | 正则替换（危险） |
| `go_diagnostics` | 编译错误和类型检查 | `go build` |
| `go_vulncheck` | 调用链级别的安全漏洞扫描 | `govulncheck` CLI |

## 何时用 gopls vs 内置工具

**用 gopls：**
- 搜索 Go 符号定义 → `go_search`
- 查找某个符号被谁调用 → `go_symbol_references`
- 了解某个包提供了哪些公开 API → `go_package_api`
- 重构前评估影响范围 → `go_symbol_references`
- 重命名变量/函数/方法 → `go_rename_symbol`
- 编辑代码后验证正确性 → `go_diagnostics`
- 了解项目模块结构 → `go_workspace`
- 查看大文件的整体结构 → `go_file_context`
- 检查依赖中的安全漏洞 → `go_vulncheck`

**用内置工具：**
- 读取已知路径的文件内容 → `read`
- 搜索非 Go 文件（配置、前端代码等）→ `grep`
- 搜索日志、注释中的文本 → `grep`
- 运行 shell 命令 → `bash`

## 逐工具使用指南

### go_workspace — 项目架构地图

进入不熟悉的 Go 项目时第一个调用。

```
go_workspace()
```

返回：模块名、Go 版本、依赖列表、子包列表、`go.work` 拓扑（多模块项目）。

### go_search — 精准符号搜索

**替代 grep 搜 Go 代码。** grep 会返回注释、字符串、日志中的匹配；go_search 只返回真正的 AST 符号定义。

```
go_search(query="UserRepo")
go_search(query="HandleFunc")
go_search(query="Config struct")
```

返回：符号定义的文件、行号、类型（struct/interface/func/var/const）。

### go_package_api — 包的公开接口

只看一个包对外暴露了什么，隐藏所有私有实现。**极度节省 Token** — 一个 3000 行的包可能只需返回 50 行接口文档。

```
go_package_api(package="github.com/user/project/pkg/store")
```

返回：导出的类型、函数签名、方法签名及文档注释。

### go_symbol_references — 破坏半径评估

**重构前必调。** 精确找到符号在全局的所有使用位置，即使有 100 个同名方法也只返回目标的那个。

```
go_symbol_references(symbol="UserService.Create")
go_symbol_references(symbol="handler.ServeHTTP")
```

返回：每个引用位置的文件、行号、列号、上下文片段。

### go_file_context — 文件大纲

打开大文件前先看骨架，精准定位需要编辑的位置。

```
go_file_context(file="internal/handler/user.go")
```

返回：文件的 import 列表、struct 定义、method 列表及签名。

### go_rename_symbol — 安全重命名

AST 级别的重命名，不会误伤字符串或注释，自动更新跨包调用。

```
go_rename_symbol(symbol="usr", newName="user")
go_rename_symbol(symbol="Get", newName="Fetch")
```

### go_diagnostics — 编译验证

**编辑 Go 代码后必须调用。** 毫秒级增量编译检查，比 `go build` 快数倍。

```
go_diagnostics(file="internal/handler/user.go")
```

返回：编译错误、类型不匹配警告及其位置。如果返回空，说明代码编译通过。

### go_vulncheck — 安全漏洞扫描

基于调用链分析，只在代码真正调用了有漏洞的函数时才告警，**零假阳性**。

```
go_vulncheck()
```

返回：实际受影响的漏洞列表及调用路径。

## 典型工作流

### 场景：重构一个结构体字段

用户说："把 `store` 包的 `User.Name` 拆分为 `FirstName` 和 `LastName`"

```
1. go_search(query="User struct")         → 定位 User 结构体
2. go_symbol_references(symbol="User.Name") → 查出所有引用位置（评估破坏半径）
3. Edit 修改结构体定义和所有引用处
4. go_diagnostics(file="...")             → 验证无编译错误
5. (如有报错) 根据 diagnostics 继续修复
```

### 场景：理解一个不熟悉的包

```
1. go_workspace()                         → 了解项目整体结构
2. go_package_api(package="pkg/service")  → 看对外接口
3. go_file_context(file="...")            → 看关键文件骨架
4. go_search(query="具体函数名")           → 找到实现
```

### 场景：安全重命名

```
1. go_symbol_references(symbol="OldName") → 评估影响范围
2. go_rename_symbol(symbol="OldName", newName="NewName") → 一键重命名
3. go_diagnostics(file="...")             → 验证无编译错误
```

## 禁忌

1. **不要用 grep 搜索 Go 符号** — 用 `go_search`，它只返回真正的定义，不返回注释和字符串中的噪音
2. **不要用 read 读整个包来了解 API** — 用 `go_package_api`，它只返回导出接口，Token 消耗降低 10-50 倍
3. **不要用正则替换做重命名** — 用 `go_rename_symbol`，它在 AST 层面操作，不会误伤
4. **不要跳过 go_diagnostics** — 编辑 Go 代码后必须验证，确保无编译错误
5. **不要在非 Go 项目中使用** — 这些工具仅适用于有 `go.mod` 的项目
