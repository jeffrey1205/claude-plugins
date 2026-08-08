---
name: gopls
description: 使用 gopls MCP 工具进行 Go 代码语义分析。当项目包含 Go 文件且 gopls 能加载对应 workspace，任务涉及符号搜索、引用、包 API、重命名、workspace 诊断、项目结构或 Go 漏洞检查时使用；优先确认 go.mod 或 go.work。适合 Go 特有的类型和 AST 分析，不用于非 Go 文件、普通文本搜索或行为验证。
---

# gopls 语义代码工具

## 核心原则

**gopls 是 Go 官方语言服务器，理解代码的 AST 和类型系统，不是文本搜索。**

在 Go 项目中，优先用 gopls MCP 工具做符号和类型相关的搜索分析。它依赖 workspace 加载状态、构建标签和可解析的依赖；结果应作为语义上下文，不能替代编译器、测试或人工确认。

## 前置检查

使用前确认目标文件属于 gopls 已加载的 Go workspace：
- 通常存在 `go.mod` 或 `go.work`
- 如果是 GOPATH 或 ad-hoc workspace，以 gopls 实际加载状态为准

## 8 个工具速查

| 工具 | 用途 | 替代什么 |
|------|------|----------|
| `go_workspace` | Go workspace 摘要 | `ls` + 逐个读 `go.mod` |
| `go_search` | 模糊匹配 Go 符号 | `grep` 搜代码 |
| `go_package_api` | 包的导出 API 签名和文档 | `read` 整个包的源码 |
| `go_symbol_references` | 从指定 Go 文件解析符号并查找引用 | `grep` 搜引用 |
| `go_file_context` | 文件的跨文件依赖摘要 | `read` 整个大文件 |
| `go_rename_symbol` | 生成 AST 级重命名 diff | 正则替换（危险） |
| `go_diagnostics` | workspace 解析、构建和相关诊断 | `go build` |
| `go_vulncheck` | Go workspace 漏洞检查 | `govulncheck` CLI |

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

进入不熟悉的 Go workspace 时第一个调用。

```
go_workspace()
```

返回：workspace 类型、根目录和主模块信息；它不等同于完整的依赖或包清单。

### go_search — 精准符号搜索

**替代 grep 搜 Go 符号。** 查询是大小写不敏感的模糊匹配，最多返回 100 个符号；结果需要结合文件和限定名进一步确认。

```
go_search(query="UserRepo")
go_search(query="HandleFunc")
go_search(query="Config struct")
```

返回：匹配符号、种类和文件路径，不保证只有一个候选。

### go_package_api — 包的公开接口

只看一个或多个包对外暴露了什么，隐藏私有实现。

```
go_package_api(packagePaths=["github.com/user/project/pkg/store"])
```

返回：导出的类型、函数签名、方法签名及文档注释。

### go_symbol_references — 破坏半径评估

重构前用于评估引用范围。必须提供包含目标符号的 Go 文件绝对路径，以及当前文件上下文中可解析的符号名；字段和方法可以使用限定名。

```
go_symbol_references(file="/absolute/path/internal/service/user.go", symbol="UserService.Create")
go_symbol_references(file="/absolute/path/internal/handler/http.go", symbol="handler.ServeHTTP")
```

返回：引用位置和上下文片段。若符号无法从指定文件解析，先用 `go_search` 或更准确的限定名定位。

### go_file_context — 文件大纲

打开或编辑大文件前先看其跨文件依赖摘要，定位需要继续读取的位置。

```
go_file_context(file="/absolute/path/internal/handler/user.go")
```

返回：文件所属包，以及该文件引用的其他文件和声明摘要；它不是完整源码读取工具。

### go_rename_symbol — 生成安全重命名修改

基于 AST 和类型信息生成跨 workspace 的重命名 diff，不会直接修改文件。调用后必须应用返回的修改，再运行 `go_diagnostics` 和相关测试。

```
go_rename_symbol(file="/absolute/path/internal/user/user.go", symbol="usr", new_name="user")
go_rename_symbol(file="/absolute/path/internal/api/api.go", symbol="Get", new_name="Fetch")
```

### go_diagnostics — 编译验证

编辑 Go 代码后调用。它检查整个 Go workspace；可通过 `files` 指定需要额外检查的活动文件。没有诊断不等同于测试通过。

```
go_diagnostics(files=["/absolute/path/internal/handler/user.go"])
```

返回：workspace 中的解析、构建和相关诊断及其位置。如果返回空，表示本次 gopls 检查没有报告诊断。

### go_vulncheck — 安全漏洞扫描

运行 Go workspace 的漏洞检查，基于调用链减少无关告警。它可能受依赖、构建配置和扫描范围影响，不应表述为零假阳性或完整安全审计。

```
go_vulncheck()
```

返回：漏洞发现、受影响的包和扫描日志。

## 典型工作流

### 场景：重构一个结构体字段

用户说："把 `store` 包的 `User.Name` 拆分为 `FirstName` 和 `LastName`"

```
1. go_search(query="User") → 定位 User 结构体
2. go_symbol_references(file="/absolute/path/user.go", symbol="User.Name") → 评估引用范围
3. Edit 修改结构体定义和引用处
4. go_diagnostics(files=["/absolute/path/user.go"]) → 检查 workspace 诊断
5. (如有报错) 根据 diagnostics 继续修复
```

### 场景：理解一个不熟悉的包

```
1. go_workspace() → 了解 Go workspace
2. go_package_api(packagePaths=["pkg/service"]) → 看对外 API
3. go_file_context(file="/absolute/path/service.go") → 看跨文件依赖摘要
4. go_search(query="具体函数名") → 找到候选实现
```

### 场景：安全重命名

```
1. go_symbol_references(file="/absolute/path/old.go", symbol="OldName") → 评估引用范围
2. go_rename_symbol(file="/absolute/path/old.go", symbol="OldName", new_name="NewName") → 生成重命名 diff
3. 应用 diff
4. go_diagnostics(files=["/absolute/path/old.go"]) → 检查 workspace 诊断
```

## 禁忌

1. **不要用 grep 搜索 Go 符号** — 用 `go_search`，再用文件和限定名确认候选
2. **不要用 read 读整个包来了解导出 API** — 用 `go_package_api`
3. **不要用正则替换做重命名** — 用 `go_rename_symbol`，应用它返回的 diff
4. **不要把 diagnostics 当作测试** — 编辑后检查 diagnostics，并运行相关测试
5. **不要在非 Go 代码任务中调用这些工具** — 配置、日志、文档和前端代码使用内置工具
6. **参数不确定时先遵循 MCP 的实际 schema** — 尤其是绝对路径、`packagePaths`、`new_name` 和 `files`
