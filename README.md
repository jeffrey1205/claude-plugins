# claude-plugins

个人 Claude Code 插件集合，包含开发工具、文档处理 Skill 等扩展。

## 安装方式

### 通过 Marketplace 安装

先将本仓库添加为插件市场：

```bash
/plugin marketplace add jeffrey1205/claude-plugins

/plugin install serena@cc-hub

/plugin install docs@cc-hub
```

## 插件列表

| 插件名 | 类型 | 描述 |
|--------|------|------|
| [serena](./plugins/serena) | MCP Server | 语义代码分析 MCP 服务器，提供智能代码理解、重构建议和代码库导航 |
| [docs](./plugins/docs) | Skill | 文档处理工具集：支持 Word、PowerPoint、PDF、Excel、图片 OCR 等场景 |

## 前置依赖

### serena-agent 安装

serena 插件需要先安装 serena-agent：

```bash
# 安装
uv tool install --from git+https://github.com/oraios/serena serena-agent

# 更新
uv tool upgrade serena-agent
```

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
    └── docs/
        ├── .claude-plugin/
        │   └── plugin.json   # 插件清单文件
        └── skills/
            └── proc/
                ├── SKILL.md      # 技能指引
                └── references/   # 参考文档
```

## 添加新插件

在 `plugins/` 目录下新建插件目录，包含：
- `.claude-plugin/plugin.json` — 插件清单（name, description, version 等）
- `.mcp.json` — MCP 服务器配置（如适用）
- `hooks/hooks.json` — Hook 配置（如适用）

然后在 `.claude-plugin/marketplace.json` 的 `plugins` 数组中添加新条目。

## 许可证

MIT
