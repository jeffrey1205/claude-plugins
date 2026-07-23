# 安装指南

## 方法一：使用 npx skills add（推荐）

```bash
npx skills add linus-torvalds-perspective
```

## 方法二：手动安装

### 1. 下载并解压

```bash
# 下载打包文件
wget https://github.com/your-repo/linus-torvalds-perspective/releases/download/v1.0.0/linus-torvalds-perspective-v1.0.0.tar.gz

# 解压到 .claude/skills/ 目录
tar -xzvf linus-torvalds-perspective-v1.0.0.tar.gz -C .claude/skills/
```

### 2. 验证安装

```bash
# 检查目录结构
ls -la .claude/skills/linus-torvalds-perspective/

# 运行质量检查
python3 .claude/skills/linus-torvalds-perspective/scripts/quality_check.py \
  .claude/skills/linus-torvalds-perspective/SKILL.md
```

## 使用方法

安装完成后，在Claude Code中使用以下关键词触发：

- `linus`
- `torvalds`
- `linux`
- `good taste`
- `never break userspace`
- `好品味`
- `实用主义`

### 示例对话

```
用户: 用Linus的视角审查这段代码
Claude: [以Linus的身份回应，使用五层分析框架]

用户: Linus会怎么设计这个数据结构？
Claude: [以Linus的身份回应，使用数据优先原则]

用户: 这段代码有好品味吗？
Claude: [以Linus的身份回应，评估代码质量]
```

## 卸载

```bash
rm -rf .claude/skills/linus-torvalds-perspective/
```
