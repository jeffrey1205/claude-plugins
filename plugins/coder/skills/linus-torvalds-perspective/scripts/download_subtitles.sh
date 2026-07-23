#!/bin/bash
# 下载YouTube视频字幕
# 用法: bash download_subtitles.sh <YouTube_URL> [输出目录]

URL=$1
OUTPUT_DIR=${2:-"../references/sources/transcripts"}

if [ -z "$URL" ]; then
    echo "用法: bash download_subtitles.sh <YouTube_URL> [输出目录]"
    exit 1
fi

# 使用yt-dlp下载字幕（如果已安装）
if command -v yt-dlp &> /dev/null; then
    yt-dlp --write-subs --write-auto-subs --sub-langs "en,zh" \
           --skip-download --output "${OUTPUT_DIR}/%(title)s.%(ext)s" "$URL"
    echo "字幕下载完成"
else
    echo "请先安装 yt-dlp: pip install yt-dlp"
    exit 1
fi
