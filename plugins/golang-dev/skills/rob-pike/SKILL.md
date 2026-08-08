---
name: rob-pike
description: 基于 Go Proverbs 指导 agent 进行 Go 代码设计、代码审查、并发设计、错误处理、调试和重构。当用户明确提到 Rob Pike、Go Proverbs、某条 proverb，或任务需要审查 Go 接口、零值、并发、cgo、unsafe、reflection、错误、panic、文档和代码清晰度时使用。不应因普通 Go 文件编辑而自动全量加载。
---

# Go Proverbs 工程指导

这个 skill 将 Go Proverbs 作为编码和审查启发式。每条 proverb 的详细说明位于 `proverbs/`。先检查实际代码和任务，再只读取相关规则；不要为了应用 proverb 而制造问题。

## 加载原则

1. 先读取用户要求、相关代码、测试和 diff，识别真实主题。
2. 每次通常选择 2-5 条最相关的 proverb，使用宿主 agent 的文件读取工具按需加载对应文件。
3. 不要在代码审查时一次读取所有 `actionable` 文件；19 个文件合计超过两千行，会浪费上下文并诱发误报。
4. 用户明确询问某条 proverb 时，只读取对应文件。
5. 详细文件同时包含 proverb、Go 官方资料和其他工程师的延伸解释。引用观点时区分原始 proverb、官方规则和本 skill 的推导，不要全部归因于 Rob Pike。

## 主题路由

| 主题 | 优先读取 |
| --- | --- |
| 并发、goroutine、channel、锁、共享状态 | [#1](proverbs/01-share-memory-by-communicating.md)、[#2](proverbs/02-concurrency-is-not-parallelism.md)、[#3](proverbs/03-channels-orchestrate-mutexes-serialize.md) |
| 接口、零值、`any`、类型设计、包边界 | [#4](proverbs/04-bigger-interface-weaker-abstraction.md)、[#5](proverbs/05-make-the-zero-value-useful.md)、[#6](proverbs/06-interface-any-says-nothing.md)、[#17](proverbs/17-design-architecture-name-components-document-details.md) |
| 代码清晰度、抽象、依赖和普通实现 | [#8](proverbs/08-little-copying-better-than-little-dependency.md)、[#13](proverbs/13-clear-is-better-than-clever.md) |
| `syscall`、cgo、`unsafe`、reflection | [#9](proverbs/09-syscall-must-be-guarded-with-build-tags.md)、[#10](proverbs/10-cgo-must-be-guarded-with-build-tags.md)、[#11](proverbs/11-cgo-is-not-go.md)、[#12](proverbs/12-unsafe-has-no-guarantees.md)、[#14](proverbs/14-reflection-is-never-clear.md) |
| `error`、错误传播、panic、recover | [#15](proverbs/15-errors-are-values.md)、[#16](proverbs/16-handle-errors-gracefully.md)、[#19](proverbs/19-dont-panic.md) |
| gofmt、文档、命名和用户可见 API | [#7](proverbs/07-gofmt-is-everyones-favorite.md)、[#17](proverbs/17-design-architecture-name-components-document-details.md)、[#18](proverbs/18-documentation-is-for-users.md) |

如果一个任务横跨多个主题，先选择最可能影响正确性和设计的规则，再根据发现继续加载，不要预先把所有规则放入上下文。

## 编码工作流

### 设计或实现

1. 明确 Go API、数据所有权、零值行为、错误契约和并发边界。
2. 根据主题路由读取少量 proverb 文件。
3. 将 proverb 转换成当前代码的具体问题，例如“这个接口是否真的需要五个方法”，而不是机械套用口号。
4. 遵循项目现有约定，做最小一致修改。
5. 运行 gofmt、相关测试、构建和项目配置的静态检查。

### 调试

1. 先确定可复现症状和失败路径。
2. panic 或错误传播问题优先读取 #15、#16、#19；并发问题优先读取 #1、#2、#3。
3. 检查 goroutine 生命周期、channel 关闭责任、锁保护的不变量、error 是否丢失或重复处理。
4. 用测试、race detector、日志或可复现命令验证原因和修复，不要仅凭 proverb 下结论。

### 重构

1. 先确认需要改善的真实问题和必须保持的行为。
2. 接口与包边界优先读取 #4、#5、#6、#17；清晰度和依赖优先读取 #8、#13。
3. 不要为了“更 Go”而扩大公共 API、改变零值语义或破坏调用方。
4. 检查最终 diff，并运行相关测试确认行为未回归。

## 代码审查

先检查 diff，再选择 proverb。不要按 proverb 顺序罗列问题，也不要保证每条规则都产生 finding。

按以下优先级输出：

1. 正确性、数据竞争、安全、panic、资源泄漏和跨平台构建问题。
2. API 契约、错误语义、并发所有权和兼容性问题。
3. 不必要的接口、reflection、unsafe、cgo 或依赖复杂度。
4. 清晰度、文档和工具链问题。

每个 finding 使用：

```text
严重性：High | Medium | Low
位置：path/to/file.go:42
问题：可复现或有明确风险的缺陷
证据：相关代码路径、契约或缺失测试
修复：最小修改建议
参考：Proverb #N — <title>
```

Proverb 只是解释 finding 的工程依据。没有代码证据时，不得仅凭 proverb 生成问题。如果没有发现，明确说明并指出尚未运行的测试或未覆盖的平台。

## 应用边界

- “Share memory by communicating” 不表示 channel 永远优于 mutex；根据数据所有权和同步目标选择。
- “Make the zero value useful” 是设计目标，不要求把本应非法的状态伪装成有效值。
- `any`、reflection、unsafe、cgo 和 panic 不是绝对禁止；使用它们需要明确边界、理由和验证。
- `syscall` 和 cgo 的 build tag、fallback 要求取决于项目支持的平台和构建契约；不要假设所有包都承诺跨平台或 `CGO_ENABLED=0`。
- “Handle errors gracefully” 不要求每层都包装或记录错误；选择真正负责恢复、转换、记录或返回的边界，避免丢失上下文和重复日志。
- “A little copying” 不支持复制复杂、易漂移或涉及安全修复的实现。

## 完成标准

- 修改经过 gofmt。
- 运行与变更相关的测试、构建或静态检查。
- review finding 有文件位置、代码证据和可执行修复建议。
- 明确哪些结论来自当前代码，哪些只是 proverb 提供的启发式。
