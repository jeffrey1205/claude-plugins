#!/usr/bin/env python3
"""
合并调研文件，生成摘要
用法: python3 merge_research.py <skill目录>
"""

import sys
from pathlib import Path

def merge_research(skill_dir):
    """合并所有调研文件"""
    research_dir = Path(skill_dir) / 'references' / 'research'
    
    if not research_dir.exists():
        print(f"错误: 找不到目录 {research_dir}")
        sys.exit(1)
    
    files = sorted(research_dir.glob('*.md'))
    
    print("# 调研摘要\n")
    print("| Agent | 文件 | 状态 |")
    print("|-------|------|------|")
    
    for f in files:
        status = "✅ 已完成" if f.stat().st_size > 100 else "⚠️ 内容较少"
        print(f"| {f.stem} | {f.name} | {status} |")
    
    print(f"\n总计: {len(files)} 个调研文件")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python3 merge_research.py <skill目录>")
        sys.exit(1)
    
    merge_research(sys.argv[1])
