# claude-plugins

个人 Claude Code 插件集合，包含 MCP 服务器、编程哲学 Skill、开发工具等扩展。

## 安装方式

### 通过 Marketplace 安装

先将本仓库添加为插件市场：

```bash
/plugin marketplace add jeffrey1205/claude-plugins

/plugin install codegraph@cc-hub
/plugin install gopls@cc-hub
/plugin install coder@cc-hub
/plugin install rtk@cc-hub
/plugin install statusline@cc-hub
```

## 插件列表

| 插件名 | 类型 | 描述 |
|--------|------|------|
| [codegraph](./plugins/codegraph) | MCP Server + Skill | 代码图谱 MCP 服务器，基于 Rust 内核构建知识图谱，提供语义搜索、调用图分析、影响分析，支持 20+ 语言 |
| [gopls](./plugins/gopls) | MCP Server + Skill | 基于 Go 官方 gopls 语言服务器的 MCP 工具集，提供 AST 级符号搜索、引用查找、安全重命名、编译诊断、漏洞扫描 |
| [coder](./plugins/coder) | Skill | 编程大师思维工具集：Rob Pike 的 Go Proverbs 全阶段指导 + Linus Torvalds 的代码品味与架构哲学 |
| [rtk](./plugins/rtk) | Hook | CLI 输出过滤工具，减少 LLM token 消耗（节省 60-90%） |
| [statusline](./plugins/statusline) | Command + Script | 自适应终端宽度的状态行插件，显示上下文窗口、Git、Token、Effort 等信息 |

## 目录结构

```
.
├── .claude-plugin/
│   └── marketplace.json    # 插件市场目录文件
└── plugins/
    ├── codegraph/
    │   ├── .claude-plugin/
    │   │   └── plugin.json   # 插件清单
    │   ├── .mcp.json         # MCP 服务器配置
    │   ├── skills/
    │   │   └── codegraph/
    │   │       └── SKILL.md  # codegraph 使用指导
    │   └── commands/
    │       └── install.md    # 安装命令
    ├── gopls/
    │   ├── .claude-plugin/
    │   │   └── plugin.json   # 插件清单
    │   ├── .mcp.json         # MCP 服务器配置
    │   └── skills/
    │       └── gopls/
    │           └── SKILL.md  # gopls 使用指导
    ├── coder/
    │   ├── .claude-plugin/
    │   │   └── plugin.json   # 插件清单
    │   └── skills/
    │       ├── rob-pike/
    │       │   ├── SKILL.md      # Go Proverbs 全阶段指导
    │       │   └── proverbs/     # 19 条 proverb 详细规则
    │       └── linus-torvalds-perspective/
    │           └── SKILL.md      # Linus 编程哲学
    ├── rtk/
    │   ├── .claude-plugin/
    │   │   └── plugin.json   # 插件清单
    │   ├── hooks/
    │   │   └── hooks.json    # PreToolUse hook 配置
    │   └── README.md
    └── statusline/
        ├── .claude-plugin/
        │   └── plugin.json   # 插件清单
        ├── commands/
        │   └── setup.md      # setup 命令
        └── scripts/
            ├── statusline.py       # 状态行脚本
            └── setup-statusline.py # 配置脚本
```

## 添加新插件

在 `plugins/` 目录下新建插件目录，包含：
- `.claude-plugin/plugin.json` — 插件清单（name, description, version 等）
- `.mcp.json` — MCP 服务器配置（如适用）
- `skills/` — Skill 文件（如适用）
- `hooks/` — Hook 配置（如适用）

然后在 `.claude-plugin/marketplace.json` 的 `plugins` 数组中添加新条目。

## 参考文档

[创建插件](https://code.claude.com/docs/zh-CN/plugins) · [插件参考](https://code.claude.com/docs/zh-CN/plugins-reference)

## 许可证

MIT
