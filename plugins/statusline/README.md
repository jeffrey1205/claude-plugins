# Statusline

CodeBuddy Code / Claude Code 通用的三行状态行：第一行概览，第二行工具调用，第三行最近一次交互与最近调用。

- 以 CodeBuddy 的状态行实现为基座，同一份代码兼容 Claude Code 的 stdin 与 transcript 格式。
- 增量解析 transcript（主 + 子 Agent），缓存放在系统临时目录，单次渲染约几十毫秒。
- 只显示 Credits（CodeBuddy 的计费单位），**不显示任何货币金额**，原因见下文。

## 环境要求

- Python 3.6+
- CodeBuddy Code 或 Claude Code（两者均可，同一套代码）
- macOS / Linux / Git Bash；Windows 通过 PowerShell 安装插件，但 `statusLine` 命令会由 `sys.executable` 直接调用 Python，路径带引号，空格安全。

## 安装

```
/plugin marketplace add jeffrey1205/claude-plugins
/plugin install statusline@cc-hub
/statusline:setup
```

`/statusline:setup` 会按宿主把 `statusLine` 写入 `~/.codebuddy/settings.json` 或 `~/.claude/settings.json`，指向当前插件版本的 `scripts/statusline.py`，写入后**重启会话**生效。

- 幂等：目标一致时不修改；`--check` 可查看是否 stale。
- **插件升级后要重跑 `/statusline:setup`**：插件缓存的目录带版本号（`.../statusline/2.0.0/scripts/`），升级后路径变化，旧配置会失效。
- settings.json 里已有其他人的 `statusLine` 时脚本会拒绝覆盖，需要 `--force`。

## 效果

```
cwd on  main* | model | Effort:high | ████░░░░░░ 44% 56.7K/128.0K | Compact×2 | In:2.4M Out:10.7K Cache:2.2M(74%) | Req:29 | Credits:67.20 | Time:45s | Avg:24.3t/s | +156/-23
Tools: ✓ Bash×15 | ✓ Read×2 | ✓ Edit | ↑ Agent ✓ Agent×2
Recent: In:3.2K Out:856 Cache:2.1K(65%) Credits:1.50 Speed:24.3t/s | Bash apt-get install -y tmux | Read main.py | Edit config.yaml
```

第一行由可配置的「块」组成（顺序、显隐均可调）：

| 块 id | 内容 |
|-------|------|
| `cwd_git` | 目录名 + git 分支/脏标记/ahead-behind，worktree 会还原成主项目名 |
| `model` | 模型显示名 |
| `effort` | `effort.level`（仅 Claude Code 提供时显示） |
| `context_bar` | 上下文进度条 + 百分比 + 已用/上限 |
| `compact_periodic` | `Compact×N`（上下文压缩次数）、`Periodic×M`（阶段性摘要，仅 CodeBuddy） |
| `tokens` | `In` / `Out` / `Cache(命中率)` / `Think` |
| `requests` | `Req:` API 请求次数 |
| `credits` | `Credits:` 累计计费 credits（为 0 不显示） |
| `time` | 会话耗时（`Time:`） |
| `speed` | 会话平均输出吞吐 `Avg:`（累计 Out ÷ 累计 API 时长） |
| `lines` | 代码增删行数 |

第二行 `Tools:` 按固定顺序统计工具调用次数；`Agent` 区分运行中（`↑`）与已完成（`✓`）。
第三行 `Recent:` 是最近一次交互的 Token 明细 + 最近 3 次工具调用摘要（CJK/ANSI 安全截断）。

## 双宿主字段支持

| 能力 | CodeBuddy Code | Claude Code |
|------|----------------|-------------|
| stdin 的 model / workspace / context_window / cost 时长 | 有 | 有 |
| `cost.total_cost_usd` | 恒为 0（CLI 写死），不使用 | 真实美元，本插件不展示 |
| `rawUsage.credit` | 有（Credits 来源） | 无 |
| `effort.level` | 无 | 有（可选块） |
| transcript 格式 | `function_call` + `providerData.usage/rawUsage` | `assistant.message.usage` + `tool_use/tool_result` |
| 压缩事件 | `providerData.isCompactInternal && isSummary` | `system/compact_boundary` |
| 阶段摘要 Periodic | 有 | 无（不渲染） |
| 终端宽度 | `/dev/tty` | `COLUMNS` 环境变量（宿主设置） |
| 子 Agent token | `subagents/*.jsonl` 增量合并 | 同左；主 transcript 的 `isSidechain` 行跳过，避免双计 |

解析按**行形状**分支，不按宿主开关；宿主只决定缓存目录与 setup 目标文件。因此即使宿主判断错了，也不会丢 token。

## 关于 Credits（为什么不显示金额）

- CodeBuddy 的计费单位是 **credits**：服务端在每次响应的 usage 里下发 `rawUsage.credit`，CLI 上报时是 `cost:{amount: credit, currency:""}`，**没有** credit 到货币的官方汇率。
- 早期版本用「credits × 0.01 当美元，再 × 7 当人民币」显示 `Cost`，两个系数都是拍脑袋，数字不可信，已移除。
- Claude Code 的 `total_cost_usd` 只对官方计价的模型有意义，三方模型下没有参考价值，也一并移除。
- 已知边界：插件只累加 transcript 里的 `rawUsage.credit`，**不含**图像/视频生成与 team_member 通道记账，因此可能小于 WebUI 的本轮 credits 汇总。

## 布局配置

配置文件：`<config>/plugins/data/statusline/config.json`（CodeBuddy 为 `~/.codebuddy/...`，Claude 为 `~/.claude/...`）。

```json
{
  "layout": {
    "line1_order": ["cwd_git", "model", "effort", "context_bar", "compact_periodic", "tokens", "requests", "credits", "time", "speed", "lines"],
    "line1_hidden": [],
    "tools": true,
    "recent": true
  }
}
```

- `line1_order`：第一行块的顺序；`line1_hidden`：隐藏指定块（优先级高于顺序）。
- `tools` / `recent`：第二、三行的整行开关。
- 新版本新增的块若未出现在配置里，会自动追加到末尾显示；要隐藏必须写进 `line1_hidden`。
- 配置损坏时回退默认布局，不会让状态行变空白；修改后下一次刷新即生效。

用命令调整（推荐）：

```
/statusline:config hide credits time
/statusline:config show credits
/statusline:config move tokens after model
/statusline:config disable tools
/statusline:config reset
/statusline:config list
```

> `cost` 块已移除。旧配置里若还留着 `cost`，会被当作未知块忽略，不会报错。

## 临时文件

- 运行时缓存（transcript 偏移、最近速率快照、更新标记）放在系统临时目录：`<tmp>/statusline-<host>-<uid>/cache/`，Unix 上是 `/tmp/statusline-codebuddy-1000/cache`，Windows 上是 `%TEMP%`。目录权限 0700，7 天自动清理。
- 布局配置是持久数据，留在 `<config>/plugins/data/statusline/config.json`。
- 临时目录丢失只会触发一次全量重解析，不影响结果正确性。

## 详细报告

```
/statusline:cost-detail
```

按模型汇总 In / Out / Cache Read / Cache Write / Reasoning / Requests / Credits（为 0 的项省略），不输出货币金额。

## 卸载

```
/statusline:uninstall     # 只删除 statusLine 配置，保留布局与缓存
```

卸载插件本身用 `/plugin` 面板。

## 从旧安装迁移

1. **旧 git-clone 版**（`~/.codebuddy/statusline/`）：先跑 `bash ~/.codebuddy/statusline/uninstall.sh`，否则它的 `statusLine` 命令仍会优先生效；再按上面的方式安装插件并执行 `/statusline:setup`。
2. **旧 Claude 单文件插件（1.0.4）**：升级后重跑 `/statusline:setup`，会把命令从 `.../statusline/1.0.4/scripts/statusline.py` 改到新版本目录。
3. 布局配置路径不变（`plugins/data/statusline/config.json`），块 id 除 `cost` 外保持兼容。

## 测试

```bash
cd plugins/statusline
python3 -m unittest discover -s scripts/tests -p 'test_*.py'
```

覆盖：双宿主解析、增量与截断、去重（同 message id / 同 tool id）、isSidechain 防双计、宿主判定、setup/uninstall、宽度与 ANSI 安全截断。

## License

MIT
