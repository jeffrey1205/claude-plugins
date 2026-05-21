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

## 内核模块专项分析

内核模块无法使用 `perf -p <pid>` 直接采样，需要专项工具。

### 内核内存分析

#### /proc/slabinfo

```bash
# 查看 slab 分配器统计
cat /proc/slabinfo

# 关注字段：
# - objsize: 对象大小
# - objperslab: 每个 slab 的对象数
# - objects: 总对象数
# - objactive: 活跃对象数

# 查看特定 slab（如网络相关）
cat /proc/slabinfo | grep -E "skb|tcp|udp|conntrack"
```

#### kmalloc/vmalloc 区别

| 分配类型 | 特点 | 适用场景 |
|----------|------|----------|
| kmalloc | 物理连续，小对象 (< 4KB) | skb、结构体、DMA |
| vmalloc | 虚拟连续，大对象 | 大缓冲区、映射用户空间 |
| __get_free_pages | 物理连续，多页 | DMA、大块连续内存 |

```bash
# 查看 vmalloc 使用
cat /proc/vmallocinfo

# 关注：
# - 地址范围
# - 调用者（who分配）
# - 大小
```

#### 内核内存泄漏排查

```bash
# 方法1：slab 统计对比（低扰动）
cat /proc/slabinfo > slab_before.txt
# 运行一段时间后
cat /proc/slabinfo > slab_after.txt
diff slab_before.txt slab_after.txt

# 方法2：kmalloc 跟踪（需要 ftrace）
echo 1 > /sys/kernel/debug/tracing/events/kmem/kmalloc/enable
echo 1 > /sys/kernel/debug/tracing/events/kmem/kfree/enable
cat /sys/kernel/debug/tracing/trace_pipe

# 方法3：使用 kmemleak（需内核启用 CONFIG_DEBUG_KMEMLEAK）
echo scan > /sys/kernel/debug/kmemleak
cat /sys/kernel/debug/kmemleak
```

---

### 内核锁分析

#### spinlock 调试

```bash
# 查看 spinlock 统计（需内核启用 CONFIG_LOCK_STAT）
cat /proc/lock_stat

# 关注：
# - wait_time_total: 总等待时间
# - wait_time_max: 最大等待时间
# - acquisitions: 获取次数
# - contentions: 冲突次数
```

常见 spinlock 问题：
- 热路径中持有 spinlock 时间过长
- spinlock 与睡眠操作混用（会死锁）
- 多核竞争同一 spinlock

```c
// 问题：spinlock 临界区过长
spin_lock(&lock);
for (i = 0; i < 10000; i++) {  // 长循环
    process_packet(&pkts[i]);
}
spin_unlock(&lock);

// 修复：缩短临界区（per-packet 加锁）
for (i = 0; i < 10000; i++) {
    spin_lock(&lock);
    process_packet(&pkts[i]);
    spin_unlock(&lock);
}

// 或修复：使用 per-CPU 锁（需先获取当前 CPU）
int cpu = smp_processor_id();  // 或在进程上下文用 get_cpu()
spin_lock(&per_cpu_lock[cpu]);
process_packet(&pkts[i]);
spin_unlock(&per_cpu_lock[cpu]);
```

#### mutex 调试

```bash
# 查看 mutex 统计（需内核启用 CONFIG_LOCK_STAT）
cat /proc/lock_stat | grep mutex

# 使用 ftrace 跟踪 mutex
echo 1 > /sys/kernel/debug/tracing/events/lock/lock_acquire/enable
echo 1 > /sys/kernel/debug/tracing/events/lock/lock_release/enable
cat /sys/kernel/debug/tracing/trace_pipe
```

#### rwlock 调试

读写锁问题主要在写者阻塞读者：
- 写者持有锁时间过长，读者排队
- 读者过多，写者无法获取锁

```bash
# 查看 rwlock 统计
cat /proc/lock_stat | grep rwlock
```

#### ftrace 锁分析

```bash
# 跟踪锁等待时间
echo 1 > /sys/kernel/debug/tracing/events/lock/lock_contention_begin/enable
echo 1 > /sys/kernel/debug/tracing/events/lock/lock_contention_end/enable
cat /sys/kernel/debug/tracing/trace_pipe

# 输出格式：
# lock_contention_begin: lock=0xffff... type=spinlock
# lock_contention_end: wait_time=12345678 ns
```

---

### 内核模块 perf 分析

```bash
# 采样内核整体（不是特定模块）
perf record -a -g -e cpu-cycles -- sleep 10

# 采样特定内核函数
perf record -a -g -e cpu-cycles --call-graph dwarf \
    --filter='func:your_module_function' -- sleep 10

# 查看内核符号
perf report --stdio --sort symbol,dso | grep your_module

# 内核火焰图
perf script | stackcollapse-perf.pl | flamegraph.pl --color=kernel > kernel.svg
```

---

### 内核瓶颈定位流程

#### softirq 占用高

> 网络软中断分析（softirq、中断分布、队列积压）见 `network-gateway.md`

#### 内核 CPU 高

```
1. perf top -a 看内核热点符号
2. cat /proc/slabinfo 检查 slab 使用
3. cat /proc/lock_stat 检查锁竞争
4. ftrace 跟踪热点函数调用频率
5. 检查：spinlock 临界区、kmalloc 频率、软中断处理
```

#### 内核内存增长

```
1. cat /proc/slabinfo 定时采样，对比变化
2. cat /proc/vmallocinfo 检查 vmalloc 使用
3. kmemleak 检查泄漏（如可用）
4. ftrace 跟踪 kmalloc/kfree
5. 检查：skb 泄漏、结构体未释放、定时任务累积
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
