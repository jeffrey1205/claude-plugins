# claude-plugins

个人 Claude Code / Codex 插件集合，包含 MCP 服务器、编程哲学 Skill、开发工具等扩展。

## 安装方式

### Claude Code

```bash
/plugin marketplace add jeffrey1205/claude-plugins

/plugin install codegraph@cc-hub
/plugin install golang-dev@cc-hub
/plugin install coder@cc-hub
/plugin install rtk@cc-hub
/plugin install statusline@cc-hub
/plugin install superpowers@cc-hub
```

### Codex

```bash
codex plugin marketplace add jeffrey1205/claude-plugins

codex plugin add codegraph@cc-hub
codex plugin add golang-dev@cc-hub
codex plugin add coder@cc-hub
codex plugin add superpowers@cc-hub
```

## 插件列表

| 插件名 | 类型 | 描述 |
|--------|------|------|
| [codegraph](./plugins/codegraph) | MCP Server + Skill | 代码图谱 MCP 服务器，提供语义搜索、调用图分析、影响分析 |
| [golang-dev](./plugins/golang-dev) | MCP Server + Skill | Go 开发工具集：gopls MCP 语义分析、MCP 编排工具、Rob Pike 的 Go Proverbs 编程哲学指导 |
| [coder](./plugins/coder) | Skill + Agent | 编程大师思维工具集：Karpathy 编码指南 + Linus Torvalds 的代码品味与架构哲学，含 worker/tester agent |
| [rtk](./plugins/rtk) | Hook | CLI 输出过滤工具，减少 LLM token 消耗（节省 60-90%） |
| [statusline](./plugins/statusline) | Command + Script | 自适应终端宽度的状态行插件，显示上下文窗口、Git、Token、Effort 等信息 |
| [superpowers](./plugins/superpowers) | Skill | 官方 Superpowers 技能扩展集，包含工作流拆解、系统化重构、设计规范等能力 |

## 目录结构

```
.
├── .agents/
│   └── plugins/
│       └── marketplace.json    # Codex 插件市场目录文件
├── .claude-plugin/
│   └── marketplace.json    # Claude Code 插件市场目录文件
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
    │   ├── agents/
    │   │   ├── worker.md     # 代码实施 agent
    │   │   └── tester.md     # 测试 agent
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
    │   │   └── plugin.json   # 插件清单
    │   ├── commands/
    │   │   └── setup.md      # setup 命令
    │   └── scripts/
    │       ├── statusline.py       # 状态行脚本
    │       └── setup-statusline.py # 配置脚本
    └── superpowers/
        ├── .codex-plugin/
        │   └── plugin.json   # 插件清单
        ├── assets/           # 静态资源文件
        └── skills/           # Superpowers 全套技能集
```

## superpowers

由于OpenAI官方仓库中 superpowers 插件版本更新缓慢，通过上游源码进行打包与替换。

在 superpowers 上游仓库根目录下运行（仅打包核心配置与技能，排除不必要的 hook 与调试脚本）：

``` bash
zip -r superpowers.zip .codex-plugin skills assets
```

## 添加新插件

以 Claude Code 插件为例，Codex 插件类似
在 `plugins/` 目录下新建插件目录，包含：
- `.claude-plugin/plugin.json` — 插件清单（name, description, version 等）
- `.mcp.json` — MCP 服务器配置（如适用）
- `skills/` — Skill 文件（如适用）
- `hooks/` — Hook 配置（如适用）

然后在 `.claude-plugin/marketplace.json` 的 `plugins` 数组中添加新条目。

codex创建插件流程类似。

## 参考文档

[Claude Code 插件](https://code.claude.com/docs/zh-CN/plugins)

[Claude Code 插件参考](https://code.claude.com/docs/zh-CN/plugins-reference)

[codex 插件](https://developers.openai.com/plugins/build/plugins)

## 许可证

MIT
