#!/usr/bin/env python3
"""SessionStart hook：自动配置 statusline"""

import json
import os


def main():
    home = os.path.expanduser('~')
    plugin_root = os.environ.get('CLAUDE_PLUGIN_ROOT', '')

    if not plugin_root:
        # 优先使用插件市场缓存路径（包含版本号）
        cache_dir = f"{home}/.claude/plugins/cache/cc-hub/statusline"
        if os.path.exists(cache_dir):
            versions = sorted(
                [d for d in os.listdir(cache_dir) if os.path.isdir(os.path.join(cache_dir, d))],
                reverse=True
            )
            if versions:
                plugin_root = os.path.join(cache_dir, versions[0])

        # 回退到开发路径
        if not plugin_root:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            dev_plugin_root = os.path.dirname(script_dir)
            if os.path.exists(os.path.join(dev_plugin_root, 'scripts', 'statusline.py')):
                plugin_root = dev_plugin_root

    if not plugin_root:
        print("statusline: 无法确定插件路径，跳过自动配置")
        return

    statusline_script = os.path.join(plugin_root, 'scripts', 'statusline.py')
    settings_path = os.path.join(home, '.claude', 'settings.json')

    # 直接读取，不存在则使用空配置
    try:
        with open(settings_path, 'r') as f:
            settings = json.load(f)
    except FileNotFoundError:
        settings = {}
    except json.JSONDecodeError:
        print("statusline: settings.json 格式错误，跳过自动配置")
        return

    existing_cmd = settings.get('statusLine', {}).get('command', '')
    if existing_cmd == statusline_script:
        return

    settings['statusLine'] = {'type': 'command', 'command': statusline_script}

    try:
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=2)
            f.write('\n')
        print(f"statusline: 已配置 statusLine -> {statusline_script}")
    except IOError as e:
        print(f"statusline: 无法写入 settings.json: {e}")


if __name__ == '__main__':
    main()