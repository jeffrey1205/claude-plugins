---
description: "写入/修复 statusLine 配置（CodeBuddy 与 Claude Code 通用）"
argument-hint: "[--host codebuddy|claude] [--force]"
---

把当前安装的 statusline 脚本写入宿主的 settings.json，然后**重启会话**才会生效。

```bash
ROOT="$CODEBUDDY_PLUGIN_ROOT"
[ -n "$ROOT" ] || ROOT="$CLAUDE_PLUGIN_ROOT"
[ -n "$ROOT" ] || ROOT=$(ls -d "$HOME"/.codebuddy/plugins/cache/cc-hub/statusline/*/ 2>/dev/null | sort -V | tail -1)
[ -n "$ROOT" ] || ROOT=$(ls -d "$HOME"/.claude/plugins/cache/cc-hub/statusline/*/ 2>/dev/null | sort -V | tail -1)
python3 "$ROOT/scripts/setup-statusline.py" $ARGUMENTS
```

脚本是幂等的：目标一致时不做修改；插件升级后版本目录变化，重跑即可把 statusLine
指向新路径（用 `--check` 可以先看是否 stale）。若 settings.json 里已有别人的
statusLine 命令，脚本会拒绝覆盖，需要 `--force`。

拿到输出后，用一句话告诉用户：写入了哪个 settings.json、命令指向哪个脚本、需要重启会话。
