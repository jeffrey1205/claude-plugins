#!/bin/bash
# 定时任务专项采集脚本
# 用法: ./collect_scheduler.sh <pid> [duration_seconds]
# 输出: 纯文本，便于复制粘贴

PID=$1
DURATION=${2:-30}

if [ -z "$PID" ]; then
    echo "用法: $0 <pid> [duration_seconds]"
    echo "  建议 duration >= 30 秒，以捕获多个定时任务周期"
    exit 1
fi

if [ ! -d "/proc/$PID" ]; then
    echo "错误: 进程 $PID 不存在"
    exit 1
fi

echo "=========================================="
echo "定时任务专项采集"
echo "PID: $PID"
echo "时长: ${DURATION}s"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# 调度统计
echo ""
echo "--- 调度统计 ---"
echo "schedstat:"
cat /proc/$PID/schedstat 2>/dev/null
echo "字段含义: 运行时间(ns) | 运行队列等待时间(ns) | 调度次数"

echo ""
echo "上下文切换:"
cat /proc/$PID/status 2>/dev/null | grep -E "(voluntary|nonvoluntary)_ctxt_switches"

# 线程信息
echo ""
echo "--- 线程信息 ---"
echo "线程数: $(ls /proc/$PID/task 2>/dev/null | wc -l)"

echo ""
echo "各线程调度统计:"
for tid in $(ls /proc/$PID/task/ 2>/dev/null); do
    if [ -f "/proc/$PID/task/$tid/schedstat" ]; then
        THREAD_NAME=$(cat /proc/$PID/task/$tid/comm 2>/dev/null)
        SCHEDSTAT=$(cat /proc/$PID/task/$tid/schedstat 2>/dev/null)
        CTXT=$(cat /proc/$PID/task/$tid/status 2>/dev/null | grep -E "(voluntary|nonvoluntary)_ctxt_switches" | awk '{print $2}' | tr '\n' ' ')
        echo "TID $tid ($THREAD_NAME): schedstat=$SCHEDSTAT ctxt=$CTXT"
    fi
done

# 调度采样
echo ""
echo "--- 调度采样 (${DURATION}秒) ---"
echo "时间戳 schedstat_run schedstat_wait schedstat_count voluntary nonvoluntary"

INIT_SCHEDSTAT=$(cat /proc/$PID/schedstat 2>/dev/null)
INIT_VOL=$(cat /proc/$PID/status 2>/dev/null | grep voluntary_ctxt_switches | awk '{print $2}')
INIT_NVol=$(cat /proc/$PID/status 2>/dev/null | grep nonvoluntary_ctxt_switches | awk '{print $2}')

for i in $(seq 1 $DURATION); do
    SCHEDSTAT=$(cat /proc/$PID/schedstat 2>/dev/null)
    VOL=$(cat /proc/$PID/status 2>/dev/null | grep voluntary_ctxt_switches | awk '{print $2}')
    NVOL=$(cat /proc/$PID/status 2>/dev/null | grep nonvoluntary_ctxt_switches | awk '{print $2}')
    echo "$(date '+%H:%M:%S') $SCHEDSTAT $VOL $NVOL"
    sleep 1
done

# 定时器信息
echo ""
echo "--- 定时器信息 ---"
if [ -f "/proc/$PID/timers" ]; then
    echo "定时器列表:"
    cat /proc/$PID/timers 2>/dev/null | head -20
else
    echo "/proc/$PID/timers 不可用"
fi

if [ -f "/proc/$PID/timerslack_ns" ]; then
    echo "定时器松弛: $(cat /proc/$PID/timerslack_ns 2>/dev/null) ns"
fi

# perf sched（如果可用）
echo ""
echo "--- perf sched ---"
if command -v perf >/dev/null 2>&1; then
    echo "perf 可用，可运行:"
    echo "  perf sched record -p $PID -- sleep $DURATION"
    echo "  perf sched latency"
    echo "  perf sched map"
else
    echo "perf 不可用"
fi

# CPU 亲和性
echo ""
echo "--- CPU 亲和性 ---"
if command -v taskset >/dev/null 2>&1; then
    echo "进程 CPU 亲和性:"
    taskset -p $PID 2>/dev/null

    echo ""
    echo "各线程 CPU 亲和性:"
    for tid in $(ls /proc/$PID/task/ 2>/dev/null | head -10); do
        THREAD_NAME=$(cat /proc/$PID/task/$tid/comm 2>/dev/null)
        AFFINITY=$(taskset -p $tid 2>/dev/null | awk '{print $6}')
        echo "  TID $tid ($THREAD_NAME): $AFFINITY"
    done
else
    echo "taskset 不可用"
fi

# 优先级
echo ""
echo "--- 优先级 ---"
echo "进程优先级:"
cat /proc/$PID/stat 2>/dev/null | awk '{print "nice:", $19, "priority:", $18}'

# 实时调度信息
echo ""
echo "--- 实时调度 ---"
for tid in $(ls /proc/$PID/task/ 2>/dev/null | head -5); do
    if [ -f "/proc/$PID/task/$tid/sched" ]; then
        POLICY=$(cat /proc/$PID/task/$tid/sched 2>/dev/null | grep policy | awk '{print $3}')
        PRIO=$(cat /proc/$PID/task/$tid/sched 2>/dev/null | grep prio | awk '{print $3}')
        THREAD_NAME=$(cat /proc/$PID/task/$tid/comm 2>/dev/null)
        echo "TID $tid ($THREAD_NAME): policy=$POLICY prio=$PRIO"
    fi
done

echo ""
echo "=========================================="
echo "采集完成"
echo "=========================================="
