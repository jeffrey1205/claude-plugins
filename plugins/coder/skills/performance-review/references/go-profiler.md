# Go 语言性能调试指导

## 目录
- [pprof 采集和分析](#pprof-采集和分析)
- [trace 使用指南](#trace-使用指南)
- [goroutine 泄漏检测](#goroutine-泄漏检测)
- [GC 日志分析](#gc-日志分析)
- [竞态检测](#竞态检测)
- [常见瓶颈定位流程](#常见瓶颈定位流程)

---

## pprof 采集和分析

### 启用 pprof

```go
import _ "net/http/pprof"

func main() {
    go func() {
        // 内部调试端口，生产环境注意限制访问
        http.ListenAndServe("localhost:6060", nil)
    }()
    // ... 业务代码
}
```

### 采集方式

```bash
# CPU profile（30秒）
go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30

# 内存 profile
go tool pprof http://localhost:6060/debug/pprof/heap

# goroutine dump
go tool pprof http://localhost:6060/debug/pprof/goroutine

# block profile（锁等待）
go tool pprof http://localhost:6060/debug/pprof/block

# mutex profile（锁竞争）
go tool pprof http://localhost:6060/debug/pprof/mutex

# 离线采集（无网络访问时）
# 先在目标机器采集
curl -o cpu.pb.gz http://localhost:6060/debug/pprof/profile?seconds=30
# 拷贝到开发机分析
go tool pprof cpu.pb.gz
```

### pprof 交互命令

```bash
# 进入 pprof 后
(pprof) top 20          # 前20热点
(pprof) top 20 -cum     # 按累计时间排序
(pprof) list processPacket  # 查看函数源码级热点
(pprof) web             # 生成调用图（需要 graphviz）
(pprof) png > pprof.png # 输出 PNG 图
```

### 嵌入式环境降级

如果无法启用 pprof HTTP 端口：

```go
import "runtime/pprof"

// CPU profile 文件采集
f, _ := os.Create("cpu.prof")
pprof.StartCPUProfile(f)
time.Sleep(30 * time.Second)
pprof.StopCPUProfile()
f.Close()

// 内存 profile 文件采集
f, _ := os.Create("mem.prof")
pprof.WriteHeapProfile(f)
f.Close()
```

```bash
# 拷贝 .prof 文件到开发机分析
go tool pprof cpu.prof
go tool pprof mem.prof
```

---

## trace 使用指南

### 采集 trace

```go
import "runtime/trace"

f, _ := os.Create("trace.out")
trace.Start(f)
time.Sleep(10 * time.Second)
trace.Stop()
f.Close()
```

### 分析 trace

```bash
go tool trace trace.out
# 打开浏览器，可查看：
# - Goroutine 分析
# - 网络阻塞分析
# - 同步阻塞分析
# - 系统调用分析
# - 调度器分析
```

### 关注点

- **Goroutine 分析**：goroutine 数量趋势，是否有泄漏
- **同步阻塞**：channel 操作、锁等待
- **系统调用**：IO 耗时
- **调度器**：是否有调度延迟

---

## goroutine 泄漏检测

### 运行时监控

```go
import "runtime"

// 定期打印 goroutine 数量
go func() {
    for {
        log.Printf("goroutines: %d", runtime.NumGoroutine())
        time.Sleep(10 * time.Second)
    }
}()
```

### goroutine dump 分析

```bash
# 采集 goroutine dump
curl http://localhost:6060/debug/pprof/goroutine?debug=2 > goroutine.txt

# 关注：
# - goroutine 总数趋势
# - 阻塞在 channel 操作的 goroutine
# - 阻塞在 IO 的 goroutine
# - 阻塞在锁的 goroutine
```

### 常见泄漏模式

```go
// 1. 无退出的 goroutine
go func() {
    for {
        // 永远不退出
    }
}()

// 2. channel 无接收方
ch := make(chan int)
go func() {
    ch <- 1  // 永远阻塞
}()

// 3. context 未取消
ctx := context.Background()  // 应该用 WithCancel/WithTimeout
go func() {
    <-ctx.Done()  // 永远不触发
}()
```

---

## GC 日志分析

### 启用 GC 日志

```bash
# 环境变量
GODEBUG=gctrace=1 ./your_program
```

输出示例：
```
gc 1 @0.012s 2%: 0.027+1.2+0.028 ms clock, 0.22+0.35/0.95/0.45+0.22 ms cpu, 4->4->2 MB, 5 MB goal, 8 P
```

字段含义：
- `gc 1`: GC 序号
- `@0.012s`: 程序启动后时间
- `2%`: GC 占 CPU 比例
- `0.027+1.2+0.028 ms`: STW sweep + 并发 mark/scan + STW mark 终止
- `4->4->2 MB`: GC 前堆大小 -> GC 后存活 -> GC 后堆大小
- `5 MB goal`: 目标堆大小
- `8 P`: P 数量（GOMAXPROCS）

### 关注点

- **GC 频率**：是否过于频繁
- **GC 占 CPU**：是否超过 5%
- **STW 时间**：是否影响延迟
- **堆增长趋势**：是否有内存泄漏

### 调优

```bash
# 调整 GOGC（默认100，即堆增长100%触发GC）
GOGC=200 ./your_program  # 减少GC频率

# 设置内存限制（Go 1.19+）
GOMEMLIMIT=1GiB ./your_program
```

---

## 竞态检测

```bash
# 编译时启用竞态检测
go build -race ./...

# 运行时检测
go run -race main.go

# 测试时检测
go test -race ./...
```

注意：race detector 会增加 2-10x 开销，仅用于调试。

---

## 常见瓶颈定位流程

### CPU 高

```
1. top 确认进程 CPU 使用率
2. go tool pprof profile?seconds=30
3. top 查看热点函数
4. list <func> 查看源码级热点
5. 检查：
   - 热循环中的内存分配
   - 编解码热点
   - 锁竞争
   - 频繁 IO/数据库操作
```

### goroutine 爆炸

```
1. runtime.NumGoroutine() 监控趋势
2. pprof goroutine?debug=2 查看阻塞点
3. 检查：
   - goroutine 无退出条件
   - channel 无接收方
   - context 未取消
```

### 内存增长

```
1. pprof heap 查看分配热点
2. top -cum 查看累计分配
3. list <func> 查看分配位置
4. 检查：
   - 缓存无上限
   - slice 持续 append
   - 定时任务累积数据
```

### 延迟高

```
1. trace 分析调度和阻塞
2. pprof block 查看锁等待
3. pprof mutex 查看锁竞争
4. 检查：
   - 锁粒度过大
   - IO 阻塞
   - GC STW
```
