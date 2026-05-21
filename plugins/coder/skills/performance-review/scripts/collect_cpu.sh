#!/bin/bash
# CPU 专项采集脚本
# 用法: ./collect_cpu.sh <pid> [duration_seconds]
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
echo "CPU 专项采集"
echo "PID: $PID"
echo "时长: ${DURATION}s"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# 进程 CPU 信息
echo ""
echo "--- 进程 CPU 信息 ---"
echo "stat 信息:"
cat /proc/$PID/stat 2>/dev/null

echo ""
echo "调度统计:"
cat /proc/$PID/schedstat 2>/dev/null

echo ""
echo "上下文切换:"
cat /proc/$PID/status 2>/dev/null | grep -E "(voluntary|nonvoluntary)_ctxt_switches"

# 线程信息
echo ""
echo "--- 线程信息 ---"
echo "线程数:"
ls /proc/$PID/task 2>/dev/null | wc -l

echo ""
echo "各线程 CPU 使用:"
for tid in $(ls /proc/$PID/task/ 2>/dev/null | head -20); do
    if [ -f "/proc/$PID/task/$tid/stat" ]; then
        THREAD_STAT=$(cat /proc/$PID/task/$tid/stat 2>/dev/null)
        THREAD_NAME=$(cat /proc/$PID/task/$tid/comm 2>/dev/null)
        echo "TID $tid ($THREAD_NAME): $THREAD_STAT"
    fi
done

# 系统 CPU 使用
echo ""
echo "--- 系统 CPU 使用 ---"
echo "CPU 统计:"
cat /proc/stat | head -1

echo ""
echo "各 CPU 统计:"
cat /proc/stat | grep "^cpu"

# CPU 采样
echo ""
echo "--- CPU 采样 (${DURATION}秒) ---"
echo "时间戳 用户态 内核态 空闲 中断 softirq"

for i in $(seq 1 $DURATION); do
    CPU_LINE=$(cat /proc/stat | head -1)
    # user nice system idle iowait irq softirq steal
    echo "$(date '+%H:%M:%S') $(echo $CPU_LINE | awk '{print $2, $4, $5, $7, $8}')"
    sleep 1
done

# syscall 统计（如果有 strace）
echo ""
echo "--- syscall 统计 ---"
if command -v strace >/dev/null 2>&1; then
    echo "strace 可用，可运行: strace -c -p $PID -e trace=all &
    sleep 5; kill %1"
    echo "注意：strace 会显著影响性能，仅用于调试"
else
    echo "strace 不可用"
fi

# perf 统计（如果有 perf）
echo ""
echo "--- perf 统计 ---"
if command -v perf >/dev/null 2>&1; then
    echo "perf 可用，可运行:"
    echo "  perf stat -p $PID -- sleep 5"
    echo "  perf record -p $PID -g -- sleep 10"
    echo "  perf report"
else
    echo "perf 不可用"
fi

# top 信息
echo ""
echo "--- top 信息 ---"
if command -v top >/dev/null 2>&1; then
    top -b -n 1 -p $PID 2>/dev/null | head -20
else
    echo "top 不可用"
fi

echo ""
echo "=========================================="
echo "采集完成"
echo "=========================================="
