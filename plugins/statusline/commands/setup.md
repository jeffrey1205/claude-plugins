---
name: statusline-setup
description: 配置 Claude Code 状态行，将 statusLine 设置写入 ~/.claude/settings.json
---

运行以下命令配置 statusline：

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup-statusline.py"
```

该脚本会将 statusLine 配置写入 ~/.claude/settings.json，指向当前插件的 statusline.py 脚本。