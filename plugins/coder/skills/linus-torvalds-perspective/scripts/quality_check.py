#!/usr/bin/env python3
"""
质量检查脚本
用法: python3 quality_check.py <SKILL.md路径>
"""

import re
import sys
from pathlib import Path

def check_skill(skill_path):
    """检查SKILL.md质量"""
    with open(skill_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        '心智模型数量': len(re.findall(r'### \d+\.', content)) >= 3,
        '决策启发式': '决策启发式' in content,
        '表达DNA': '表达DNA' in content,
        '诚实边界': '诚实边界' in content,
        '时间线': '时间线' in content,
        '调研来源': '调研来源' in content,
        '创建者归属': '女娲' in content or 'nuwa-skill' in content,
    }
    
    print("# 质量检查\n")
    print("| 检查项 | 状态 |")
    print("|--------|------|")
    
    passed = 0
    for item, status in checks.items():
        mark = "✅ PASS" if status else "❌ FAIL"
        print(f"| {item} | {mark} |")
        if status:
            passed += 1
    
    print(f"\n通过率: {passed}/{len(checks)} ({passed/len(checks)*100:.0f}%)")
    
    return passed == len(checks)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python3 quality_check.py <SKILL.md路径>")
        sys.exit(1)
    
    skill_path = sys.argv[1]
    if check_skill(skill_path):
        print("\n✅ 所有检查通过！")
        sys.exit(0)
    else:
        print("\n⚠️ 部分检查未通过")
        sys.exit(1)
