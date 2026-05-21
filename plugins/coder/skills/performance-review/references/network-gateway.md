# 网络设备专项分析

针对 fw、ids、gap、gateway 等网络设备后端的性能分析指导。

## 目录
- [PPS/BPS 测试方法](#ppsbps-测试方法)
- [小包性能分析](#小包性能分析)
- [中断绑核指导](#中断绑核指导)
- [控制面/数据面分离检查清单](#控制面数据面分离检查清单)
- [队列积压分析](#队列积压分析)
- [零拷贝技术](#零拷贝技术)
- [定时任务分析](#定时任务分析)
- [调度漂移分析](#调度漂移分析)

---

## PPS/BPS 测试方法

### 测试仪配置

```
测试仪（如 Spirent/Ixia/Pktgen-DPDK）：
- 小包测试：64字节，测 PPS 上限
- 大包：1518字节，测 BPS 上限
- 混合包长：IMIX 模型
```

### 关键指标

```
PPS (Packets Per Second):
- 小包场景核心指标
- 10Gbps 线速 64 字节：~14.88 Mpps

BPS (Bits Per Second):
- 大包场景核心指标
- 网卡线速：1G/10G/25G/40G/100G

时延：
- P50: 中位数
- P95: 95分位
- P99: 99分位
- 最大值
```

### 采集方法

```bash
# 网卡统计
ethtool -S eth0

# /proc 统计
cat /proc/net/dev

# 中断统计
cat /proc/interrupts | grep eth

# CPU 使用
mpstat -P ALL 1
```

---

## 小包性能分析

小包场景下 per-packet 开销成为主要瓶颈：

### 热点分析

```
每个包的固定开销：
1. 网卡收包 → DMA → 内存
2. 中断处理 / softirq
3. 协议栈处理
4. 业务逻辑（查表、匹配、转发）
5. 发包 → DMA → 网卡

小包（64字节）时，数据处理占比极低，per-packet 开销占比极高
```

### 优化方向

```
1. 批量处理：recvmmsg/sendmmsg
2. 轮询模式：替代中断驱动（DPDK 思路）
3. 零拷贝：减少数据拷贝
4. 减少锁：per-CPU 数据结构
5. 批量查表：session_lookup_batch
6. 预取：prefetch 下一个包的数据
```

### 检查清单

- [ ] 是否使用批量收发（recvmmsg/sendmmsg）
- [ ] 是否有 per-packet 的内存分配
- [ ] 是否有 per-packet 的锁操作
- [ ] 是否有 per-packet 的日志
- [ ] 是否有 per-packet 的 syscall
- [ ] 是否使用预取（prefetch）
- [ ] 是否使用 per-CPU 数据结构

---

## 中断绑核指导

### 查看当前中断分布

```bash
cat /proc/interrupts
# 关注网卡中断号

# 查看中断亲和性
cat /proc/irq/<irq_num>/smp_affinity
cat /proc/irq/<irq_num>/smp_affinity_list
```

### 设置中断亲和性

```bash
# 方法1：smp_affinity（位图）
# CPU 0-3 = 0x0F
echo 0f > /proc/irq/<irq_num>/smp_affinity

# 方法2：smp_affinity_list（CPU 列表）
echo 0-3 > /proc/irq/<irq_num>/smp_affinity_list
```

### 推荐配置

```
场景1：数据面为主
- 网卡中断：绑定到数据面 CPU（如 CPU 2-N）
- 控制面：绑定到 CPU 0-1
- 系统中断：绑定到 CPU 0

场景2：控制面和数据面混合
- 网卡队列 0：绑定到 CPU 0-1（控制面）
- 网卡队列 1-N：绑定到 CPU 2-N（数据面）
```

### RPS/RFS 配置

```bash
# RPS（Receive Packet Steering）：软件层面的接收队列分散
echo f > /sys/class/net/eth0/queues/rx-0/rps_cpus

# RFS（Receive Flow Steering）：按流分散
echo 32768 > /sys/class/net/eth0/queues/rx-0/rps_flow_cnt
echo 32768 > /proc/sys/net/core/rps_sock_flow_entries
```

---

## 控制面/数据面分离检查清单

### 线程模型

- [ ] 控制面和数据面是否在独立线程
- [ ] 线程是否设置了 CPU 亲和性
- [ ] 数据面线程是否绑核（避免调度器迁移）

### 资源隔离

- [ ] CPU 隔离：数据面使用独立 CPU 核
- [ ] 内存隔离：数据面使用独立内存池
- [ ] 锁隔离：控制面和数据面不共享锁
- [ ] 日志隔离：数据面使用异步日志或采样日志

### 干扰源检查

- [ ] 定时任务是否在数据面 CPU 上运行
- [ ] 配置更新是否阻塞数据面
- [ ] 规则下发是否影响转发
- [ ] 日志输出是否在热路径
- [ ] 统计上报是否阻塞主路径

### 中断隔离

```bash
# 将数据面 CPU 从中断中隔离
# 内核启动参数（需重启）
isolcpus=2-N

# 或运行时调整：只将系统中断绑定到控制面 CPU（排除网卡中断）
for irq_dir in /proc/irq/*/; do
    irq_num=$(basename "$irq_dir")
    # 检查是否为网卡中断（通过 actions 文件）
    if [ -f "$irq_dir/actions" ]; then
        actions=$(cat "$irq_dir/actions")
        # 排除网卡中断，网卡中断应绑定到数据面 CPU
        if echo "$actions" | grep -q -E "(eth|ixgbe|i40e|mlx)"; then
            continue
        fi
    fi
    # 绑定系统中断到控制面 CPU（如 CPU 0-1）
    echo 03 > "$irq_dir/smp_affinity" 2>/dev/null
done
```

---

## 队列积压分析

### 网卡队列

```bash
# 查看网卡队列数
ethtool -l eth0

# 查看队列统计
ethtool -S eth0 | grep -i queue

# 关注：
# - rx_queue_N_drops：队列满丢包
# - rx_queue_N_bytes：队列吞吐
```

### Socket 队列

```bash
# 查看 socket 缓冲区
ss -m

# 查看系统限制
sysctl net.core.rmem_max
sysctl net.core.wmem_max
sysctl net.core.netdev_max_backlog

# 调整
sysctl -w net.core.netdev_max_backlog=10000
```

### softirq 积压

```bash
# 查看 softnet_stat
cat /proc/net/softnet_stat

# 字段2（dropped）：队列满丢包
# 字段3（time_squeeze）：处理时间不足

# 如果 time_squeeze 持续增长，说明 softirq 被频繁打断
# 解决：增加 netdev_budget
sysctl -w net.core.netdev_budget=600
sysctl -w net.core.netdev_budget_usecs=8000
```

### 应用层队列

```
检查点：
1. 网卡 → 应用：是否有积压（/proc/net/softnet_stat）
2. 应用内部：消息队列是否积压
3. 应用 → 下游：发送队列是否积压

如果 P99 延迟高，通常是队列积压导致
```

---

## 零拷贝技术

### sendfile

```c
// 适用于：转发文件内容、代理场景
#include <sys/sendfile.h>
sendfile(out_fd, in_fd, &offset, count);
```

### splice

```c
// 适用于：两个 fd 之间的数据移动
#include <fcntl.h>
splice(pipefd[0], NULL, out_fd, NULL, len, SPLICE_F_MOVE);
```

### mmap + send

```c
// 适用于：需要修改包内容再转发
void *buf = mmap(NULL, len, PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0);
// 修改 buf
send(fd, buf, len, 0);
```

### 用户态零拷贝（DPDK 思路）

```
1. 网卡 DMA 直接写入用户态 buffer
2. 应用直接操作 buffer，无内核态拷贝
3. 发送时 buffer 直接 DMA 到网卡

需要：UIO/VFIO 驱动、hugepage、轮询模式
```

### 检查点

- [ ] 是否有不必要的数据拷贝
- [ ] 是否可用 sendfile/splice 替代 read+write
- [ ] 是否可用 scatter-gather IO
- [ ] 是否可用用户态网络栈（如 DPDK）

---

## 定时任务分析

### 常见定时任务类型

```
1. 规则同步：从控制面同步规则到数据面
2. 签名更新：IDS/FW 的特征库更新
3. 统计上报：性能指标、流量统计
4. 会话清理：过期会话表清理
5. 日志轮转：日志文件切换
6. 健康检查：设备状态检测
```

### 影响分析

```
定时任务对主路径的影响：
1. CPU 抢占：定时任务占用数据面 CPU
2. 锁竞争：定时任务与转发线程抢锁
3. 内存压力：规则重建时内存翻倍
4. IO 干扰：日志写入影响转发
5. Cache 污染：大量数据遍历污染 CPU cache
```

### 检查清单

- [ ] 定时任务是否绑定到独立 CPU
- [ ] 定时任务是否降低优先级（nice）
- [ ] 规则更新是否使用双缓冲（无锁切换）
- [ ] 统计上报是否异步
- [ ] 日志是否使用异步写入
- [ ] 会话清理是否分批执行

---

## 调度漂移分析

### 概念

```
定时任务设计为每 T 秒执行一次，但由于：
- CPU 被其他任务占用
- 锁等待
- IO 阻塞
- GC 停顿

实际执行间隔可能是 T+δ，δ 就是漂移
```

### 采集方法

```bash
# 方法1：应用日志
# 定时任务每次执行时打印时间戳
# 对比相邻时间戳差值

# 方法2：/proc/[pid]/schedstat
cat /proc/<pid>/schedstat
# 字段1：运行时间（纳秒）
# 字段3：调度次数

# 方法3：perf sched
perf sched record -- sleep 10
perf sched latency
```

### 分析方法

```
1. 采集定时任务的执行时间戳序列
2. 计算相邻时间戳差值：δ_i = t_i - t_{i-1}
3. 统计：
   - 平均漂移：mean(δ_i) - T
   - 最大漂移：max(δ_i) - T
   - 漂移标准差：stddev(δ_i)
4. 关注：
   - 漂移是否可接受（通常 < 10% T）
   - 是否有周期性大漂移（与 GC、规则同步相关）
   - 是否有累积漂移（任务执行时间 > 周期）
```

### 优化建议

```
1. 任务执行时间 < 周期/2
2. 使用绝对时间触发，而非相对时间
3. 避免在同一秒扎堆触发多个任务
4. 长任务拆分为多个短任务
5. 使用 deadline 调度器（SCHED_DEADLINE）
```
