# claude-plugins

个人 Claude Code / Codex / CodeBuddy 插件集合，包含 MCP 服务器、编程哲学 Skill、开发工具等扩展。

## 安装方式

### Claude Code

```bash
/plugin marketplace add jeffrey1205/claude-plugins

/plugin install codegraph@cc-hub
/plugin install golang-dev@cc-hub
/plugin install coder@cc-hub
/plugin install rtk@cc-hub
/plugin install statusline@cc-hub
/plugin install docs@cc-hub
/plugin install agents@cc-hub
```

### Codex

```bash
codex plugin marketplace add jeffrey1205/claude-plugins

codex plugin add codegraph@cc-hub
codex plugin add golang-dev@cc-hub
codex plugin add coder@cc-hub
codex plugin add docs@cc-hub
```

### CodeBuddy

```bash
/plugin marketplace add jeffrey1205/claude-plugins

/plugin install codegraph@cc-hub
/plugin install golang-dev@cc-hub
/plugin install coder@cc-hub
/plugin install docs@cc-hub
/plugin install statusline@cc-hub
```

## 插件列表

| 插件名 | 类型 | 描述 |
|--------|------|------|
| [codegraph](./plugins/codegraph) | MCP Server + Skill | 代码图谱 MCP 服务器，提供语义搜索、调用图分析、影响分析 |
| [golang-dev](./plugins/golang-dev) | MCP Server + Skill | Go 开发工具集：gopls MCP 语义分析、MCP 编排工具、Rob Pike 的 Go Proverbs 编程哲学指导 |
| [coder](./plugins/coder) | Skill | 编程大师思维工具集：Karpathy 编码指南 + Linus Torvalds 的代码品味与架构哲学 |
| [rtk](./plugins/rtk) | Hook | CLI 输出过滤工具，减少 LLM token 消耗（节省 60-90%） |
| [statusline](./plugins/statusline) | Command + Script | 双宿主状态行（CodeBuddy Code / Claude Code）：上下文进度、Git、Token、请求数、Credits、Effort |
| [docs](./plugins/docs) | Skill | 写作辅助 Skill：基于 283 万字语料统计的去 AI 味改写，白名单式规则只改命中文字 |
| [agents](./plugins/agents) | Agent | Claude Code 专用开发 agent 集：worker 实施已确认计划的代码修改，tester 负责 Go/Python 测试 |

> codegraph / golang-dev / coder / docs / statusline 同时支持 Claude Code 与 CodeBuddy；rtk / agents 仅支持 Claude Code。


## 目录结构

```
.
├── .agents/
│   └── plugins/
│       └── marketplace.json    # Codex 插件市场目录文件
├── .claude-plugin/
│   └── marketplace.json    # Claude Code 插件市场目录文件
├── .codebuddy-plugin/
│   └── marketplace.json    # CodeBuddy 插件市场目录文件
└── plugins/
    ├── codegraph/
    │   ├── .claude-plugin/
    │   │   └── plugin.json   # 插件清单
    │   ├── .mcp.json         # MCP 服务器配置
    │   └── skills/
    │       └── codegraph/
    │           └── SKILL.md  # codegraph 使用指导
    ├── golang-dev/
    │   ├── .claude-plugin/
    │   │   └── plugin.json   # 插件清单
    │   ├── .mcp.json         # gopls MCP 服务器配置
    │   └── skills/
    │       ├── gopls/
    │       │   └── SKILL.md  # gopls 语义分析工具使用指导
    │       ├── mcp-orch/
    │       │   └── SKILL.md  # MCP 编排工具
    │       └── rob-pike/
    │           ├── SKILL.md      # Go Proverbs 全阶段指导
    │           └── proverbs/     # 19 条 proverb 详细规则
    ├── coder/
    │   ├── .claude-plugin/
    │   │   └── plugin.json   # 插件清单
    │   └── skills/
    │       ├── karpathy/
    │       │   └── SKILL.md  # Karpathy 编码指南
    │       └── linus-torvalds/
    │           └── SKILL.md  # Linus 编程哲学
    ├── rtk/
    │   ├── .claude-plugin/
    │   │   └── plugin.json   # 插件清单
    │   ├── hooks/
    │   │   └── hooks.json    # PreToolUse hook 配置
    │   └── README.md
    ├── statusline/
    │   ├── .claude-plugin/
    │   │   └── plugin.json   # Claude Code 插件清单
    │   ├── .codebuddy-plugin/
    │   │   └── plugin.json   # CodeBuddy 插件清单
    │   ├── commands/          # setup/config/cost-detail/uninstall
    │   └── scripts/           # 入口、解析、渲染、setup 与测试
    │       ├── statusline.py  # 入口（薄编排）
    │       ├── parsing.py     # 双宿主 transcript 解析
    │       ├── render.py      # 三行渲染 + 布局配置
    │       └── tests/         # 297 个用例
    ├── docs/
    │   ├── .claude-plugin/
    │   │   └── plugin.json      # 插件清单
    │   ├── .codex-plugin/
    │   │   └── plugin.json      # Codex 插件清单
    │   ├── .codebuddy-plugin/
    │   │   └── plugin.json      # CodeBuddy 插件清单
    │   └── skills/
    │       └── lieflat-less-ai-tone/
    │           ├── SKILL.md     # 去AI味规则集
    │           ├── README.md    # 研究说明文档
    │           ├── assets/      # 文档配图
    │           └── scripts/     # 语料测量脚本
    ├── agents/
    │   ├── .claude-plugin/
    │   │   └── plugin.json   # 插件清单
    │   └── agents/
    │       ├── worker.md     # 代码实施 agent
    │       └── tester.md     # 测试 agent
```

## 添加新插件

以 Claude Code 插件为例，Codex / CodeBuddy 插件流程类似
在 `plugins/` 目录下新建插件目录，包含：
- `.claude-plugin/plugin.json` — Claude Code 插件清单（name, description, version 等）
- `.codex-plugin/plugin.json` — Codex 插件清单（如支持 Codex）
- `.codebuddy-plugin/plugin.json` — CodeBuddy 插件清单（如支持 CodeBuddy）
- `.mcp.json` — MCP 服务器配置（如适用）
- `skills/` — Skill 文件（如适用）
- `hooks/` — Hook 配置（如适用）

然后在 `.claude-plugin/marketplace.json` 的 `plugins` 数组中添加新条目；Codex 和 CodeBuddy 分别同步到 `.agents/plugins/marketplace.json` 和 `.codebuddy-plugin/marketplace.json`。

## 参考文档

[Claude Code 插件](https://code.claude.com/docs/zh-CN/plugins)

[Claude Code 插件参考](https://code.claude.com/docs/zh-CN/plugins-reference)

[codex 插件](https://developers.openai.com/plugins/build/plugins)

[CodeBuddy 插件](https://www.codebuddy.cn/docs/cli/plugins)

[CodeBuddy 插件市场](https://www.codebuddy.cn/docs/cli/plugin-marketplaces)

## 许可证

MIT
