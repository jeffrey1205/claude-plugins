---
name: rob-pike
description: 基于 Rob Pike 的 Go Proverbs 指导 Go 开发全阶段 — 设计、编码、审查、调试、重构。当用户处理 Go 代码时使用，触发词包括"review with Go proverbs"、"Go proverbs"、"/rob-pike"、"rob pike"、"Go 代码审查"、"Go 设计"、"Go 并发"、"Go 错误处理"、"Go 重构"等。也适用于用户问及具体某条 proverb（如 "#13"、"clear is better than clever"）。仅适用于 Go 语言项目。
---

# Rob Pike's Go Proverbs

基于 Rob Pike 的 19 条 Go Proverbs (<https://go-proverbs.github.io/>)，指导 Go 开发的各个阶段。每条 proverb 对应 `proverbs/` 下的详细规则文件。

## 核心原则

**按需加载，不全量读取。** 根据当前开发阶段选择相关的 proverb 子集，用 read 工具读取对应的规则文件，将 proverb 智慧融入当前任务。不要一次加载全部 19 个文件。

## 按开发阶段使用

### 设计/架构

用户在做模块设计、接口定义、包结构规划时，加载：

| # | Proverb | 文件 |
|---|---------|------|
| 17 | Design the architecture, name the components, document the details | [proverbs/17-design-architecture-name-components-document-details.md](proverbs/17-design-architecture-name-components-document-details.md) |
| 4 | The bigger the interface, the weaker the abstraction | [proverbs/04-bigger-interface-weaker-abstraction.md](proverbs/04-bigger-interface-weaker-abstraction.md) |
| 5 | Make the zero value useful | [proverbs/05-make-the-zero-value-useful.md](proverbs/05-make-the-zero-value-useful.md) |
| 6 | interface{} says nothing | [proverbs/06-interface-any-says-nothing.md](proverbs/06-interface-any-says-nothing.md) |
| 1 | Don't communicate by sharing memory, share memory by communicating | [proverbs/01-share-memory-by-communicating.md](proverbs/01-share-memory-by-communicating.md) |

### 并发设计

用户在设计 goroutine、channel、锁策略时，加载：

| # | Proverb | 文件 |
|---|---------|------|
| 1 | Don't communicate by sharing memory, share memory by communicating | [proverbs/01-share-memory-by-communicating.md](proverbs/01-share-memory-by-communicating.md) |
| 2 | Concurrency is not parallelism | [proverbs/02-concurrency-is-not-parallelism.md](proverbs/02-concurrency-is-not-parallelism.md) |
| 3 | Channels orchestrate; mutexes serialize | [proverbs/03-channels-orchestrate-mutexes-serialize.md](proverbs/03-channels-orchestrate-mutexes-serialize.md) |

### 编码实现

用户在写新代码、实现功能时，加载：

| # | Proverb | 文件 |
|---|---------|------|
| 13 | Clear is better than clever | [proverbs/13-clear-is-better-than-clever.md](proverbs/13-clear-is-better-than-clever.md) |
| 8 | A little copying is better than a little dependency | [proverbs/08-little-copying-better-than-little-dependency.md](proverbs/08-little-copying-better-than-little-dependency.md) |
| 15 | Errors are values | [proverbs/15-errors-are-values.md](proverbs/15-errors-are-values.md) |
| 16 | Don't just check errors, handle them gracefully | [proverbs/16-handle-errors-gracefully.md](proverbs/16-handle-errors-gracefully.md) |
| 19 | Don't panic | [proverbs/19-dont-panic.md](proverbs/19-dont-panic.md) |

### 代码审查

用户要求 review Go 代码时，加载全部 `actionable` 类 proverb（#1, 3, 4, 5, 6, 8, 9, 10, 12, 13, 14, 15, 16, 17, 18, 19）。`philosophical`（#2, #11）和 `tooling`（#7）类不生成 finding，但可作为判断依据。

审查输出格式：

```
### Proverb #N — <short title>
- path/to/file.go:42 — <one-sentence finding>
  See: proverbs/NN-<slug>.md
```

### 调试/排错

用户在排查 panic、死锁、goroutine 泄漏、error 处理问题时，加载：

| # | Proverb | 文件 |
|---|---------|------|
| 1 | Don't communicate by sharing memory, share memory by communicating | [proverbs/01-share-memory-by-communicating.md](proverbs/01-share-memory-by-communicating.md) |
| 3 | Channels orchestrate; mutexes serialize | [proverbs/03-channels-orchestrate-mutexes-serialize.md](proverbs/03-channels-orchestrate-mutexes-serialize.md) |
| 12 | With the unsafe package there are no guarantees | [proverbs/12-unsafe-has-no-guarantees.md](proverbs/12-unsafe-has-no-guarantees.md) |
| 15 | Errors are values | [proverbs/15-errors-are-values.md](proverbs/15-errors-are-values.md) |
| 19 | Don't panic | [proverbs/19-dont-panic.md](proverbs/19-dont-panic.md) |

### 重构

用户在重构代码、提取接口、简化结构时，加载：

| # | Proverb | 文件 |
|---|---------|------|
| 13 | Clear is better than clever | [proverbs/13-clear-is-better-than-clever.md](proverbs/13-clear-is-better-than-clever.md) |
| 4 | The bigger the interface, the weaker the abstraction | [proverbs/04-bigger-interface-weaker-abstraction.md](proverbs/04-bigger-interface-weaker-abstraction.md) |
| 8 | A little copying is better than a little dependency | [proverbs/08-little-copying-better-than-little-dependency.md](proverbs/08-little-copying-better-than-little-dependency.md) |
| 17 | Design the architecture, name the components, document the details | [proverbs/17-design-architecture-name-components-document-details.md](proverbs/17-design-architecture-name-components-document-details.md) |

### 工具链

用户问及 lint、格式化、工具配置时，加载：

| # | Proverb | 文件 |
|---|---------|------|
| 7 | Gofmt's style is no one's favorite, yet gofmt is everyone's favorite | [proverbs/07-gofmt-is-everyones-favorite.md](proverbs/07-gofmt-is-everyones-favorite.md) |

### 单条 Proverb

用户问及具体某条 proverb（如 "explain #8"、"clear is better than clever 是什么意思"），直接加载对应的单个规则文件回答，无需加载其他文件。

## Proverb 总索引

| # | Proverb | Category |
|---|---------|----------|
| 1 | Don't communicate by sharing memory, share memory by communicating | actionable |
| 2 | Concurrency is not parallelism | philosophical |
| 3 | Channels orchestrate; mutexes serialize | actionable |
| 4 | The bigger the interface, the weaker the abstraction | actionable |
| 5 | Make the zero value useful | actionable |
| 6 | interface{} says nothing | actionable |
| 7 | Gofmt's style is no one's favorite, yet gofmt is everyone's favorite | tooling |
| 8 | A little copying is better than a little dependency | actionable |
| 9 | Syscall must always be guarded with build tags | actionable |
| 10 | Cgo must always be guarded with build tags | actionable |
| 11 | Cgo is not Go | philosophical |
| 12 | With the unsafe package there are no guarantees | actionable |
| 13 | Clear is better than clever | actionable |
| 14 | Reflection is never clear | actionable |
| 15 | Errors are values | actionable |
| 16 | Don't just check errors, handle them gracefully | actionable |
| 17 | Design the architecture, name the components, document the details | actionable |
| 18 | Documentation is for users | actionable |
| 19 | Don't panic | actionable |

| Category | 含义 |
|----------|------|
| actionable | 可生成具体的代码改进发现 |
| tooling | 验证工具配置，不标记代码问题 |
| philosophical | 指导判断，不直接生成 finding |
