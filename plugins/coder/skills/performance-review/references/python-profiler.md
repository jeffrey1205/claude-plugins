# Python 性能调试指导

## 目录
- [py-spy 使用](#py-spy-使用)
- [cProfile 使用](#cprofile-使用)
- [tracemalloc 使用](#tracemalloc-使用)
- [asyncio 调试](#asyncio-调试)
- [线程分析](#线程分析)
- [常见瓶颈定位流程](#常见瓶颈定位流程)

---

## py-spy 使用

### 安装

```bash
pip install py-spy
# 或
cargo install py-spy
```

### 采样

```bash
# 实时 top
py-spy top --pid <pid>

# 生成火焰图
py-spy record -o flamegraph.svg --pid <pid>

# 采样 30 秒
py-spy record -o flamegraph.svg --pid <pid> --duration 30

# 采样 Python 程序
py-spy record -o flamegraph.svg -- python your_program.py
```

### 嵌入式环境

```bash
# 如果无法安装 py-spy，用 cProfile 替代
python -m cProfile -o profile.prof your_program.py
```

### 关注点

- **纯 Python 热点**：是否可用 C 扩展替代
- **IO 等待**：是否需要异步
- **锁等待**：GIL 竞争

---

## cProfile 使用

### 命令行

```bash
# 采集整个程序
python -m cProfile -o profile.prof your_program.py

# 查看结果
python -m pstats profile.prof
```

### pstats 交互

```python
import pstats
p = pstats.Stats('profile.prof')
p.sort_stats('cumulative').print_stats(20)  # 按累计时间排序前20
p.sort_stats('tottime').print_stats(20)     # 按自身时间排序
p.print_callers('process_packet')           # 查看谁调用了这个函数
```

### 代码中使用

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# ... 要测量的代码 ...

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('tottime')
stats.print_stats(20)
```

### 关注点

- **tottime**：函数自身耗时（不含子调用）
- **cumtime**：函数累计耗时（含子调用）
- **ncalls**：调用次数

---

## tracemalloc 使用

### 基本用法

```python
import tracemalloc

tracemalloc.start()

# ... 要测量的代码 ...

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

print("[ Top 10 ]")
for stat in top_stats[:10]:
    print(stat)
```

### 对比快照

```python
import tracemalloc

tracemalloc.start()

snapshot1 = tracemalloc.take_snapshot()

# ... 执行操作 ...

snapshot2 = tracemalloc.take_snapshot()

top_stats = snapshot2.compare_to(snapshot1, 'lineno')
print("[ Top 10 differences ]")
for stat in top_stats[:10]:
    print(stat)
```

### 按文件统计

```python
top_stats = snapshot.statistics('filename')
for stat in top_stats[:10]:
    print(stat)
```

### 关注点

- **内存增长点**：哪个文件哪行分配最多
- **分配频率**：是否在热循环中频繁分配
- **内存泄漏**：对比快照看增长

---

## asyncio 调试

### 开启调试模式

```python
import asyncio

asyncio.run(main(), debug=True)

# 或设置环境变量
# PYTHONASYNCIODEBUG=1 python your_program.py
```

### 事件循环监控

```python
import asyncio

loop = asyncio.get_event_loop()
loop.slow_callback_duration = 0.1  # 超过100ms的回调会打印警告
```

### task dump

```python
# 获取所有 task
for task in asyncio.all_tasks():
    print(f"Task: {task.get_name()}")
    print(f"  Coroutine: {task.get_coro()}")
    print(f"  Done: {task.done()}")
```

### 协程栈

```python
# Python 3.12+
for task in asyncio.all_tasks():
    task.print_stack()
```

### 常见问题

```python
# 1. 同步阻塞
async def bad():
    time.sleep(1)  # 阻塞事件循环！
    # 修复：await asyncio.sleep(1)

# 2. CPU 密集型任务
async def bad():
    heavy_computation()  # 阻塞事件循环！
    # 修复：await loop.run_in_executor(None, heavy_computation)

# 3. 未 await
async def bad():
    some_async_func()  # 创建了协程但未 await
    # 修复：await some_async_func()
```

---

## 线程分析

### 线程栈 dump

```python
import threading
import traceback

def dump_threads():
    for thread_id, frame in sys._current_frames().items():
        print(f"\nThread {thread_id}:")
        traceback.print_stack(frame)
```

### GIL 分析

```python
import sys

# 检查 GIL 切换间隔
sys.getswitchinterval()  # 默认 5ms

# 调整（增大可减少切换开销，但增加延迟）
sys.setswitchinterval(0.01)  # 10ms
```

### 线程 vs 进程选择

```python
# IO 密集型 → 线程
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor() as executor:
    results = list(executor.map(io_bound_func, data))

# CPU 密集型 → 进程
from concurrent.futures import ProcessPoolExecutor
with ProcessPoolExecutor() as executor:
    results = list(executor.map(cpu_bound_func, data))
```

---

## 常见瓶颈定位流程

### CPU 高

```
1. top 确认 Python 进程 CPU
2. py-spy top --pid <pid> 看热点
3. py-spy record -o flame.svg --pid <pid>
4. 分析火焰图
5. 检查：
   - 纯 Python 热循环
   - GIL 竞争
   - 频繁 IO/数据库操作
   - 异常处理在热路径
```

### 内存增长

```
1. tracemalloc 监控分配
2. 对比快照定位增长点
3. objgraph 查看引用关系（如可安装）
4. 检查：
   - 缓存无上限
   - 引用环
   - 定时任务累积数据
   - 全局变量增长
```

### 延迟高

```
1. 确认是同步还是异步代码
2. 同步：cProfile 找慢函数
3. 异步：asyncio debug 模式
4. 检查：
   - 同步阻塞在异步上下文
   - GIL 竞争
   - 数据库/IO 慢查询
   - 锁等待
```
