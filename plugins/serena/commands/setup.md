---
name: serena-setup
description: 配置 Serena MCP，检测安装状态并配置语言服务器
---

# Serena Setup

先检测 Serena 安装状态：

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/setup.js"
```

根据输出结果执行以下流程：

## 流程

**步骤 1：处理安装/更新**

- 如果 `installed: false`：询问用户是否安装 Serena，确认后执行：
  ```bash
  node "${CLAUDE_PLUGIN_ROOT}/scripts/setup.js" --install
  ```

- 如果 `installed: true`：显示当前版本，询问用户是否更新，确认后执行：
  ```bash
  node "${CLAUDE_PLUGIN_ROOT}/scripts/setup.js" --update
  ```

**步骤 2：配置语言服务器（必须询问）**

无论步骤 1 的结果如何，最后都要询问用户是否配置语言服务器路径。用户确认后执行：

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/setup.js" --config
```
