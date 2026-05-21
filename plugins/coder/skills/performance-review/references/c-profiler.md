# C 语言性能调试指导

适用于 C 用户态程序和内核模块的性能分析。

## 目录
- [perf 使用指南](#perf-使用指南)
- [火焰图生成](#火焰图生成)
- [strace 分析 syscall](#strace-分析-syscall)
- [/proc 文件系统解读](#proc-文件系统解读)
- [内存分析](#内存分析)
- [常见瓶颈定位流程](#常见瓶颈定位流程)

---

## perf 使用指南

### 基本采样

```bash
# 采样指定进程，10秒，含调用栈
perf record -p <pid> -g -- sleep 10

# 采样全系统
perf record -a -g -- sleep 10

# 查看报告
perf report
```

### 嵌入式环境降级

如果 perf 不可用：

```bash
# 方案1：用 strace 采样 syscall
strace -c -p <pid> -e trace=all &
sleep 10
kill %1

# 方案2：用 /proc 采样
while true; do
    cat /proc/<pid>/stat
    cat /proc/<pid>/status
    sleep 1
done

# 方案3：用 top 采样
top -b -n 10 -p <pid> > top_output.txt
```

### perf stat

```bash
# 硬件计数器
perf stat -p <pid> -- sleep 10

# 关注：
# - cache-misses / cache-references → cache 命中率
# - branch-misses → 分支预测失败
# - context-switches → 上下文切换
# - page-faults → 缺页
```

### perf top

```bash
# 实时查看热点函数
perf top -p <pid>
```

---

## 火焰图生成

### 使用 perf + FlameGraph

```bash
# 1. 采样
perf record -p <pid> -g -- sleep 30

# 2. 生成折叠栈
perf script | stackcollapse-perf.pl > out.folded

# 3. 生成 SVG
flamegraph.pl out.folded > flamegraph.svg
```

### 无 FlameGraph 工具时

```bash
# 用 perf 自带的 report
perf report --stdio --call-graph=graph,0.5,caller
```

### 内核火焰图

```bash
# 采样内核栈
perf record -a -g -e cpu-cycles -- sleep 10
perf script | stackcollapse-perf.pl | flamegraph.pl > kernel.svg
```

---

## strace 分析 syscall

### syscall 统计

```bash
# 统计 syscall 调用次数和耗时
strace -c -p <pid> &
sleep 10
kill %1
```

输出示例：
```
% time     seconds  usecs/call     calls    errors syscall
------ ----------- ----------- --------- --------- ----------------
 45.00    0.123456          12     10000           write
 30.00    0.082304           8     10000           read
 15.00    0.041152          41      1000           futex
```

### syscall 跟踪

```bash
# 跟踪特定 syscall
strace -e trace=read,write,recvmsg,sendmsg -p <pid>

# 带时间戳
strace -T -e trace=read,write -p <pid>

# 输出到文件
strace -o strace.log -p <pid>
```

### 关注点

- **write/read 频率**：是否在热路径中频繁调用
- **futex**：锁竞争指标
- **nanosleep/clock_gettime**：定时器开销
- **mmap/munmap**：内存分配频率

---

## /proc 文件系统解读

### /proc/[pid]/status

```bash
cat /proc/<pid>/status
```

关键字段：
- `VmPeak`: 虚拟内存峰值
- `VmRSS`: 物理内存使用
- `VmSwap`: Swap 使用
- `Threads`: 线程数
- `voluntary_ctxt_switches`: 自愿上下文切换（IO 等待）
- `nonvoluntary_ctxt_switches`: 非自愿上下文切换（时间片用完）

### /proc/[pid]/stat

```bash
cat /proc/<pid>/stat
```

关键字段（按空格分隔，索引从1开始）：
- 14: utime（用户态 CPU 时间）
- 15: stime（内核态 CPU 时间）
- 19: num_threads
- 23: vsize（虚拟内存大小）
- 24: rss（驻留页数）

### /proc/[pid]/schedstat

```bash
cat /proc/<pid>/schedstat
```

三个字段：
1. 运行时间（纳秒）
2. 运行队列等待时间（纳秒）
3. 调度次数

### /proc/[pid]/smaps_rollup

```bash
cat /proc/<pid>/smaps_rollup
```

汇总内存映射信息，关注：
- Rss: 物理内存
- Pss: 按共享比例分摊的物理内存
- Private_Dirty: 私有脏页（最真实的内存占用）

### /proc/net/dev

```bash
cat /proc/net/dev
```

网卡收发统计，关注：
- RX packets / TX packets
- RX errors / TX errors
- RX dropped / TX dropped
- RX overruns / TX overruns

### /proc/net/softnet_stat

```bash
cat /proc/net/softnet_stat
```

每行对应一个 CPU，字段：
1. 已处理包数
2. dropped（队列满丢包）
3. time_squeeze（处理时间不足）

### /proc/interrupts

```bash
cat /proc/interrupts
```

中断分布，检查：
- 是否集中在少数 CPU
- 网卡中断是否均匀分布

---

## 内存分析

### jemalloc 统计

```bash
# 编译时启用 jemalloc
export MALLOC_CONF=stats_print:true
./your_program

# 或运行时
MALLOC_CONF=stats_print:true ./your_program
```

关注：
- `allocated`: 当前分配量
- `active`: 活跃页
- `resident`: 驻留内存
- `metadata`: 元数据开销
- `fragmentation`: 碎片率

### valgrind massif

```bash
# 堆分析（会显著变慢）
valgrind --tool=massif ./your_program
ms_print massif.out.<pid>
```

### ASAN

```bash
# 编译时启用
gcc -fsanitize=address -g your_program.c

# 检测：内存泄漏、越界、use-after-free
```

---

## 常见瓶颈定位流程

### CPU 高

```
1. top/pidstat 确认哪个进程 CPU 高
2. perf top -p <pid> 看热点函数
3. perf record -p <pid> -g -- sleep 10
4. 火焰图分析调用栈
5. 定位到具体函数
6. 检查：热循环中的锁、内存分配、syscall
```

### 内存增长

```
1. watch -n 1 'cat /proc/<pid>/status | grep VmRSS' 观察趋势
2. 确认是 RSS 增长还是 VSize 增长
3. jemalloc stats 或 valgrind massif 定位分配热点
4. 检查：缓存未清理、对象泄漏、定时任务累积
```

### 时延高

```
1. 确认时延分布（P50/P95/P99）
2. P99 高通常是队列堆积或锁竞争
3. strace -T 看 syscall 耗时
4. perf record 分析调用栈
5. 检查：锁等待、IO 阻塞、定时任务抢占
```

### 吞吐低

```
1. 确认 CPU 是否已满（top/mpstat）
2. CPU 未满：检查 IO 等待、锁、队列
3. CPU 已满：perf 分析热点
4. 检查：批量处理、零拷贝、中断分布
```
