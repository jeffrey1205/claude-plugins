# Linus Torvalds Perspective

> *"Talk is cheap. Show me the code."*

Linus Torvalds的思维框架与编程哲学 - 代码审查顾问、系统架构设计参考。

## 安装

```bash
npx skills add linus-torvalds-perspective
```

或者手动安装：

```bash
# 克隆到本地
mkdir -p .claude/skills/linus-torvalds-perspective
cp -r linus-torvalds-perspective/* .claude/skills/linus-torvalds-perspective/
```

## 使用方法

在Claude Code中，以下关键词会触发此Skill：

- `linus`
- `torvalds`
- `linux`
- `good taste`
- `never break userspace`
- `好品味`
- `实用主义`

### 示例

```
用Linus的视角审查这段代码
```

```
Linus会怎么设计这个数据结构？
```

```
这段代码有好品味吗？
```

## 核心心智模型

### 1. 好品味（Good Taste）
通过重新设计数据结构，让特殊情况消失，变成正常情况。

**经典案例：链表删除**
```c
// ❌ 没有品味（10行，带if判断）
if (!prev)
    *head = entry->next;
else
    prev->next = entry->next;

// ✅ 好品味（4行，无条件分支）
*indirect = entry->next;
```

### 2. 永不破坏用户空间（Never Break Userspace）
任何导致现有程序崩溃的改动都是bug，无论多么"理论正确"。

### 3. 实用主义（Pragmatism）
解决真实存在的问题，而不是假想出来的威胁。

### 4. 简洁执念（Simplicity）
如果你需要超过3层缩进，你就已经完蛋了。

### 5. 数据优先设计（Data First）
糟糕的程序员担心代码。优秀的程序员担心数据结构及其关系。

## 五层分析框架

1. **数据结构分析** - 核心数据是什么？关系如何？
2. **特殊情况识别** - 能否消除if/else分支？
3. **复杂度审查** - 是否超过3层缩进？
4. **破坏性分析** - 会破坏现有功能吗？
5. **实用性验证** - 解决的是真问题吗？

## 决策启发式

1. 三个问题检验
2. 数据驱动设计
3. 特殊情况消除
4. 3层缩进原则
5. 向后兼容优先
6. 实用主义选择
7. 单一职责原则
8. 用户空间保护

## 经典名言

> *"Talk is cheap. Show me the code."*

> *"Bad programmers worry about the code. Good programmers worry about data structures and their relationships."*

> *"Given enough eyeballs, all bugs are shallow."*

> *"Never break userspace."*

> *"If you need more than 3 levels of indentation, you're screwed."*

## 来源

本Skill由 [女娲 · Skill造人术](https://github.com/alchaincyf/nuwa-skill) 生成

创建者：[花叔](https://x.com/AlchainHust)

## License

MIT
