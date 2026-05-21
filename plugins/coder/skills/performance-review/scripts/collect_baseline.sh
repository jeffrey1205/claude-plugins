#!/bin/bash
# 基线数据采集脚本
# 用法: ./collect_baseline.sh <pid> [duration_seconds]
# 输出: 纯文本，便于复制粘贴

PID=$1
DURATION=${2:-10}

if [ -z "$PID" ]; then
    echo "用法: $0 <pid> [duration_seconds]"
    echo "  pid: 目标进程 PID"
    echo "  duration_seconds: 采集时长（默认10秒）"
    exit 1
fi

if [ ! -d "/proc/$PID" ]; then
    echo "错误: 进程 $PID 不存在"
    exit 1
fi

echo "=========================================="
echo "基线数据采集"
echo "PID: $PID"
echo "时长: ${DURATION}s"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# 进程信息
echo ""
echo "--- 进程信息 ---"
cat /proc/$PID/comm 2>/dev/null && echo ""
cat /proc/$PID/cmdline 2>/dev/null | tr '\0' ' ' && echo ""

# 进程级指标
echo ""
echo "--- 进程级指标 ---"
echo "状态:"
cat /proc/$PID/status 2>/dev/null | grep -E "^(Name|State|Tgid|Pid|PPid|Threads|VmPeak|VmSize|VmRSS|VmSwap|voluntary_ctxt_switches|nonvoluntary_ctxt_switches)"

echo ""
echo "内存汇总:"
cat /proc/$PID/smaps_rollup 2>/dev/null

echo ""
echo "FD 数量:"
ls /proc/$PID/fd 2>/dev/null | wc -l

echo ""
echo "stat 信息:"
cat /proc/$PID/stat 2>/dev/null

echo ""
echo "调度统计:"
cat /proc/$PID/schedstat 2>/dev/null

# 系统级指标
echo ""
echo "--- 系统级指标 ---"
echo "Load average:"
cat /proc/loadavg

echo ""
echo "CPU 信息:"
cat /proc/stat | head -1

echo ""
echo "内存信息:"
cat /proc/meminfo | grep -E "^(MemTotal|MemFree|MemAvailable|Buffers|Cached|SwapTotal|SwapFree)"

# 网络统计
echo ""
echo "--- 网络统计 ---"
echo "网卡统计:"
cat /proc/net/dev

echo ""
echo "softnet_stat:"
cat /proc/net/softnet_stat

echo ""
echo "TCP 连接数:"
cat /proc/net/tcp 2>/dev/null | wc -l
cat /proc/net/tcp6 2>/dev/null | wc -l

# 多次采样
echo ""
echo "--- 采样数据 (${DURATION}秒, 每秒1次) ---"
echo "时间戳 CPU_user CPU_system CPU_idle RSS_kb VSZ_kb"

for i in $(seq 1 $DURATION); do
    # CPU
    CPU_LINE=$(cat /proc/stat | head -1)
    CPU_USER=$(echo $CPU_LINE | awk '{print $2}')
    CPU_SYSTEM=$(echo $CPU_LINE | awk '{print $4}')
    CPU_IDLE=$(echo $CPU_LINE | awk '{print $5}')

    # 内存
    STATUS=$(cat /proc/$PID/status 2>/dev/null)
    RSS=$(echo "$STATUS" | grep VmRSS | awk '{print $2}')
    VSZ=$(echo "$STATUS" | grep VmSize | awk '{print $2}')

    echo "$(date '+%H:%M:%S') $CPU_USER $CPU_SYSTEM $CPU_IDLE $RSS $VSZ"
    sleep 1
done

echo ""
echo "=========================================="
echo "采集完成"
echo "=========================================="
