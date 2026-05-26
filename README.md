# claude-plugins

个人 Claude Code 插件集合，包含开发工具、文档处理 Skill 等扩展。

## 安装方式

### 通过 Marketplace 安装

先将本仓库添加为插件市场：

```bash
/plugin marketplace add jeffrey1205/claude-plugins

/plugin install serena@cc-hub
/plugin install coder@cc-hub
/plugin install docs@cc-hub
/plugin install html-lsp@cc-hub
/plugin install statusline@cc-hub
/plugin install rtk@cc-hub
/plugin install codegraph@cc-hub
```

## 插件列表

| 插件名 | 类型 | 描述 |
|--------|------|------|
| [serena](./plugins/serena) | MCP Server | 语义代码分析 MCP 服务器，提供智能代码理解、重构建议和代码库导航 |
| [coder](./plugins/coder) | Skill + Command | 面向 C/Go/Python 后端工程师的性能分析与代码审查工具集，覆盖 CPU、内存、吞吐/时延、定时任务等维度，适配网络设备（fw/ids/gap/gateway）场景；新增 `/coder:lsp-setup` 命令用于安装语言服务器 |
| [docs](./plugins/docs) | Skill | 面向直接处理文档与扫描件的工具集：支持 Word、PowerPoint、PDF、Excel、图片 OCR 等场景，以及多语言文档翻译（粘贴文本/单文件/目录批量，保留术语和代码块） |
| [html-lsp](./plugins/html-lsp) | LSP | HTML/CSS/ESLint 语言服务器集成，提供前端开发时的语法检查、代码补全和实时 lint 诊断 |
| [statusline](./plugins/statusline) | Command | 自适应终端宽度的状态行插件，显示上下文窗口、Git、Token、Effort 等信息 |
| [rtk](./plugins/rtk) | Hook | CLI 工具，过滤命令输出减少 LLM token 消耗（节省 60-90%） |
| [codegraph](./plugins/codegraph) | MCP Server | 代码图谱 MCP 服务器，使用 tree-sitter 构建知识图谱，提供语义搜索、调用图分析、影响分析等功能 |

## 目录结构

```
.
├── .claude-plugin/
│   └── marketplace.json    # 插件市场目录文件
└── plugins/
    ├── serena/
    │   ├── .claude-plugin/
    │   │   └── plugin.json   # 插件清单文件
    │   ├── .mcp.json         # MCP 服务器配置
    │   └── hooks/
    │       └── hooks.json    # Hook 配置
    ├── docs/
    │   ├── .claude-plugin/
    │   │   └── plugin.json   # 插件清单文件
    │   └── skills/
    │       ├── proc/
    │       │   ├── SKILL.md      # 文档处理技能指引
    │       │   └── references/   # 参考文档
    │       └── trans/
    │           ├── SKILL.md      # 文档翻译技能指引
    │           ├── assets/       # 示例文件
    │           └── references/   # 术语库和按文件类型的翻译规则
    ├── coder/
    │   ├── .claude-plugin/
    │   │   └── plugin.json   # 插件清单文件
    │   ├── commands/
    │   │   └── lsp-setup.md  # LSP 安装命令
    │   └── skills/
    │       ├── performance-review/
    │       │   ├── SKILL.md      # 性能分析技能指引
    │       │   ├── evals.json    # 评测配置
    │       │   ├── evals/        # 评测用例
    │       │   ├── references/   # 参考文档
    │       │   └── scripts/      # 采集脚本
    │       └── codebase-explainer/
    │           ├── SKILL.md      # 代码理解技能指引
    │           └── references/   # 参考文档
    ├── html-lsp/
    │   ├── .claude-plugin/
    │   │   └── plugin.json   # 插件清单文件
    │   └── .lsp.json         # LSP 服务器配置
    ├── statusline/
    │   ├── .claude-plugin/
    │   │   └── plugin.json   # 插件清单文件
    │   ├── commands/
    │   │   └── setup.md      # setup 命令
    │   └── scripts/
    │       ├── statusline.py       # 状态行脚本
    │       └── setup-statusline.py # 配置脚本
    ├── codegraph/
    │   ├── .claude-plugin/
    │   │   └── plugin.json   # 插件清单文件
    │   ├── .mcp.json         # MCP 服务器配置
    │   └── commands/
    │       ├── install.md    # 安装 CLI
    │       ├── init.md       # 初始化索引
    │       ├── sync.md       # 增量同步索引
    │       ├── status.md     # 索引状态
    │       └── reindex.md    # 全量重建索引
    └── rtk/
        ├── .claude-plugin/
        │   └── plugin.json   # 插件清单文件
        ├── commands/
        │   └── setup.md      # setup 命令
        ├── hooks/
        │   └── hooks.json    # PreToolUse hook 配置
        └── scripts/
            └── setup-rtk.py  # 安装脚本
```

## 添加新插件

在 `plugins/` 目录下新建插件目录，包含：
- `.claude-plugin/plugin.json` — 插件清单（name, description, version 等）
- `.mcp.json` — MCP 服务器配置（如适用）
- `hooks/hooks.json` — Hook 配置（如适用）

然后在 `.claude-plugin/marketplace.json` 的 `plugins` 数组中添加新条目。

## 参考文档
[创建插件](https://code.claude.com/docs/zh-CN/plugins)

[插件参考](https://code.claude.com/docs/zh-CN/plugins-reference)


## 许可证

MIT
