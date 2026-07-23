#!/usr/bin/env python3
"""
将SRT字幕文件转换为纯文本transcript
用法: python3 srt_to_transcript.py <input.srt> [output.txt]
"""

import re
import sys
from pathlib import Path

def srt_to_transcript(input_file, output_file=None):
    """将SRT文件转换为纯文本"""
    if output_file is None:
        output_file = input_file.replace('.srt', '.txt')
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 移除时间戳、序号、HTML标签
    lines = content.split('\n')
    transcript_lines = []
    
    for line in lines:
        # 跳过序号行
        if line.strip().isdigit():
            continue
        # 跳过时间戳行
        if '-->' in line:
            continue
        # 移除HTML标签
        line = re.sub(r'<[^>]+>', '', line)
        # 跳过空行
        if line.strip():
            transcript_lines.append(line.strip())
    
    # 移除连续重复行
    cleaned_lines = []
    prev_line = None
    for line in transcript_lines:
        if line != prev_line:
            cleaned_lines.append(line)
        prev_line = line
    
    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(cleaned_lines))
    
    print(f"转换完成: {output_file}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python3 srt_to_transcript.py <input.srt> [output.txt]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    srt_to_transcript(input_file, output_file)
