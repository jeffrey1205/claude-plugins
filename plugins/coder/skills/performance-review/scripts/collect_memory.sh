#!/bin/bash
# 内存专项采集脚本
# 用法: ./collect_memory.sh <pid> [duration_seconds]
# 输出: 纯文本，便于复制粘贴

PID=$1
DURATION=${2:-10}

if [ -z "$PID" ]; then
    echo "用法: $0 <pid> [duration_seconds]"
    exit 1
fi

if [ ! -d "/proc/$PID" ]; then
    echo "错误: 进程 $PID 不存在"
    exit 1
fi

echo "=========================================="
echo "内存专项采集"
echo "PID: $PID"
echo "时长: ${DURATION}s"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# 进程内存信息
echo ""
echo "--- 进程内存信息 ---"
echo "status:"
cat /proc/$PID/status 2>/dev/null | grep -E "^(VmPeak|VmSize|VmRSS|VmSwap|VmData|VmStk|VmLib|VmPTE|VmHWM)"

echo ""
echo "smaps_rollup:"
cat /proc/$PID/smaps_rollup 2>/dev/null

echo ""
echo "oom_score:"
cat /proc/$PID/oom_score 2>/dev/null
cat /proc/$PID/oom_score_adj 2>/dev/null

# 内存映射
echo ""
echo "--- 内存映射统计 ---"
echo "映射数量:"
cat /proc/$PID/maps 2>/dev/null | wc -l

echo ""
echo "映射类型分布:"
cat /proc/$PID/maps 2>/dev/null | awk '{print $6}' | sort | uniq -c | sort -rn | head -10

# 系统内存
echo ""
echo "--- 系统内存 ---"
cat /proc/meminfo | grep -E "^(MemTotal|MemFree|MemAvailable|Buffers|Cached|SwapTotal|SwapFree|Slab|SReclaimable|SUnreclaim)"

echo ""
echo "slab 信息:"
cat /proc/slabinfo 2>/dev/null | head -20

# 内存采样
echo ""
echo "--- 内存采样 (${DURATION}秒) ---"
echo "时间戳 VmRSS_kb VmSize_kb VmSwap_kb"

for i in $(seq 1 $DURATION); do
    STATUS=$(cat /proc/$PID/status 2>/dev/null)
    RSS=$(echo "$STATUS" | grep VmRSS | awk '{print $2}')
    VSZ=$(echo "$STATUS" | grep VmSize | awk '{print $2}')
    SWAP=$(echo "$STATUS" | grep VmSwap | awk '{print $2}')
    echo "$(date '+%H:%M:%S') $RSS $VSZ $SWAP"
    sleep 1
done

# jemalloc 统计（如果可用）
echo ""
echo "--- jemalloc 统计 ---"
if [ -f "/proc/$PID/environ" ]; then
    MALLOC_CONF=$(cat /proc/$PID/environ 2>/dev/null | tr '\0' '\n' | grep MALLOC_CONF)
    if [ -n "$MALLOC_CONF" ]; then
        echo "MALLOC_CONF: $MALLOC_CONF"
        echo "如需 jemalloc 统计，运行时设置: MALLOC_CONF=stats_print:true"
    else
        echo "未设置 MALLOC_CONF"
    fi
fi

# 内存分配热点（如果有 valgrind）
echo ""
echo "--- 内存分析工具 ---"
if command -v valgrind >/dev/null 2>&1; then
    echo "valgrind 可用，可运行:"
    echo "  valgrind --tool=massif ./your_program"
    echo "  ms_print massif.out.<pid>"
else
    echo "valgrind 不可用"
fi

if command -v pmap >/dev/null 2>&1; then
    echo ""
    echo "pmap 信息:"
    pmap -x $PID 2>/dev/null | tail -5
fi

echo ""
echo "=========================================="
echo "采集完成"
echo "=========================================="
