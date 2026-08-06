#!/usr/bin/env python3
"""CodeGraph 初始化配置脚本"""

import json
import os

# 路径常量
CLAUDE_DIR = ".claude"
SETTINGS_PATH = f"{CLAUDE_DIR}/settings.local.json"
CODEGRAPH_MD_PATH = f"{CLAUDE_DIR}/codegraph.md"
CLAUDE_MD_PATH = "CLAUDE.md"

# MCP 工具权限列表
MCP_PERMISSIONS = [
    "mcp__plugin_codegraph_codegraph__codegraph_explore",
]

CODEGRAPH_MD_CONTENT = """## CodeGraph

CodeGraph builds a semantic knowledge graph of codebases for faster, smarter code exploration.

**Answer directly with CodeGraph — don't delegate exploration to a file-reading sub-agent or a grep/read loop.** CodeGraph *is* the pre-built search index; re-deriving its answers with grep + Read repeats work it already did and costs more for the same result. For "how does X work?", architecture, trace, or where-is-X questions, answer in a handful of CodeGraph calls and stop — typically with **zero file reads**. The returned source is complete and authoritative: treat it as already read and do not re-open those files. Reach for raw Read/Grep only to confirm a specific detail CodeGraph didn't cover.

**Tool selection by intent:**

| Tool | Use For |
|------|---------|
| `codegraph_explore` | Survey several related symbols' source in ONE budget-capped call |

A direct CodeGraph answer is a handful of calls; a grep/read exploration is dozens.
"""


def setup_settings_local():
    """合并 MCP 工具权限到 settings.local.json"""
    try:
        with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
            settings = json.load(f)
    except FileNotFoundError:
        settings = {}
    except (json.JSONDecodeError, IOError) as e:
        print(f"✗ 读取 {SETTINGS_PATH} 失败: {e}")
        return False

    settings.setdefault('permissions', {})
    settings['permissions'].setdefault('allow', [])

    existing = set(settings['permissions']['allow'])
    added = [p for p in MCP_PERMISSIONS if p not in existing]

    if not added:
        print("✓ MCP 工具权限已配置，无需更新")
        return True

    settings['permissions']['allow'].extend(added)
    os.makedirs(CLAUDE_DIR, exist_ok=True)

    try:
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
            f.write('\n')
        print(f"✓ 已添加 {len(added)} 个 MCP 工具权限到 {SETTINGS_PATH}")
        return True
    except IOError as e:
        print(f"✗ 写入 {SETTINGS_PATH} 失败: {e}")
        return False


def setup_codegraph_md():
    """创建 .claude/codegraph.md"""
    if os.path.exists(CODEGRAPH_MD_PATH):
        print("✓ codegraph.md 已存在")
        return True

    os.makedirs(CLAUDE_DIR, exist_ok=True)

    try:
        with open(CODEGRAPH_MD_PATH, 'w', encoding='utf-8') as f:
            f.write(CODEGRAPH_MD_CONTENT)
        print(f"✓ 已创建 {CODEGRAPH_MD_PATH}")
        return True
    except IOError as e:
        print(f"✗ 创建 {CODEGRAPH_MD_PATH} 失败: {e}")
        return False


def setup_claude_md():
    """在 CLAUDE.md 中添加 codegraph.md 引用"""
    reference = f"@{CODEGRAPH_MD_PATH}"

    try:
        with open(CLAUDE_MD_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        content = ""
    except IOError as e:
        print(f"✗ 读取 {CLAUDE_MD_PATH} 失败: {e}")
        return False

    if reference in content:
        print("✓ CLAUDE.md 已包含 codegraph.md 引用")
        return True

    try:
        with open(CLAUDE_MD_PATH, 'a', encoding='utf-8') as f:
            if content and not content.endswith('\n'):
                f.write('\n')
            f.write(f'\n{reference}\n')
        print(f"✓ 已在 {CLAUDE_MD_PATH} 中添加 codegraph.md 引用")
        return True
    except IOError as e:
        print(f"✗ 写入 {CLAUDE_MD_PATH} 失败: {e}")
        return False


def main():
    print("配置 CodeGraph...")
    results = [
        setup_settings_local(),
        setup_codegraph_md(),
        setup_claude_md(),
    ]
    if all(results):
        print("\n✓ CodeGraph 配置完成")
    else:
        print("\n✗ CodeGraph 配置失败，请检查错误信息")


if __name__ == '__main__':
    main()
