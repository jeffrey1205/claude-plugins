# 性能反模式扫描规则

扫描代码时按此文档中的规则逐项检查。每条规则包含：模式描述、问题代码、修复方案、检测方法。

---

## C 语言

### [高] 热循环中动态内存分配

**类别**: 内存 / CPU
**现象**: 在包处理主循环或高频调用函数中调用 malloc/free/new
**检测**: 搜索热路径中的 malloc/calloc/realloc/free/new/delete

```c
// 问题：每个包都分配释放
void process_packet(struct pkt *p) {
    char *buf = malloc(p->len);
    memcpy(buf, p->data, p->len);
    // ... 处理
    free(buf);
}
```

```c
// 修复：使用预分配的 buffer pool
static __thread char pkt_buf[MAX_PKT_SIZE];

void process_packet(struct pkt *p) {
    char *buf = pkt_buf;  // 或从 pool 获取
    memcpy(buf, p->data, p->len);
    // ... 处理
    // 无需 free
}
```

---

### [高] 热路径中的 syscall

**类别**: CPU / IO
**现象**: 在包处理循环中调用 gettimeofday、clock_gettime、write(日志) 等
**检测**: 搜索热路径中的系统调用，特别是时间相关和 IO 相关

```c
// 问题：每个包都取时间
void process_packet(struct pkt *p) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    log_packet(p, ts.tv_sec);
    // ... 转发
}
```

```c
// 修复：批量处理后统一取时间，或使用 TSC
static inline uint64_t rdtsc(void) {
    uint32_t lo, hi;
    asm volatile("rdtsc" : "=a"(lo), "=d"(hi));
    return ((uint64_t)hi << 32) | lo;
}
```

---

### [高] 锁粒度过大

**类别**: 锁 / 并发
**现象**: 用一把大锁保护整个数据结构，而不是细分锁粒度
**检测**: 搜索 pthread_mutex_lock 调用，检查临界区大小

```c
// 问题：全局锁，所有操作互斥
static pthread_mutex_t session_lock = PTHREAD_MUTEX_INITIALIZER;

struct session *find_session(uint32_t id) {
    pthread_mutex_lock(&session_lock);
    struct session *s = hash_lookup(sessions, id);
    pthread_mutex_unlock(&session_lock);
    return s;
}
```

```c
// 修复：分段锁（per-bucket lock）
#define BUCKET_LOCK(id) (&session_locks[(id) % NUM_LOCKS])

struct session *find_session(uint32_t id) {
    uint32_t bucket = id % NUM_BUCKETS;
    pthread_mutex_lock(BUCKET_LOCK(bucket));
    struct session *s = hash_lookup(&sessions[bucket], id);
    pthread_mutex_unlock(BUCKET_LOCK(bucket));
    return s;
}
```

---

### [中] 缺少批量处理

**类别**: CPU / 吞吐
**现象**: 逐包处理，没有利用批量操作减少开销
**检测**: 搜索 recv/send 调用，检查是否使用 recvmmsg/sendmmsg

```c
// 问题：逐包收发
while (running) {
    n = recv(fd, buf, sizeof(buf), 0);
    process_packet(buf, n);
    send(out_fd, buf, n, 0);
}
```

```c
// 修复：批量收发
struct mmsghdr msgs[32];
while (running) {
    int n = recvmmsg(fd, msgs, 32, MSG_DONTWAIT, NULL);
    for (int i = 0; i < n; i++) {
        process_packet(msgs[i]);
    }
    sendmmsg(out_fd, msgs, n, 0);
}
```

---

### [中] 缓存不友好的数据结构

**类别**: CPU
**现象**: 链表遍历、结构体过大导致 cache miss
**检测**: 搜索链表遍历、大结构体数组访问

```c
// 问题：链表遍历，cache 不友好
struct rule {
    struct rule *next;
    uint32_t src_ip;
    uint32_t dst_ip;
    uint16_t src_port;
    uint16_t dst_port;
    char payload[256];  // 大字段
    // ... 更多字段
};

struct rule *match_rule(struct rule *head, struct pkt *p) {
    for (struct rule *r = head; r; r = r->next) {
        if (rule_match(r, p)) return r;
    }
    return NULL;
}
```

```c
// 修复：数组 + 紧凑结构体
struct rule_key {
    uint32_t src_ip;
    uint32_t dst_ip;
    uint16_t src_port;
    uint16_t dst_port;
};

struct rule {
    struct rule_key key;  // 热数据放前面
    uint32_t action;
    // ... 冷数据放后面
};

// 使用数组，预取友好
struct rule rules[MAX_RULES];
```

---

### [中] 未对齐内存访问

**类别**: CPU
**现象**: 直接 cast 网络包头到结构体指针，可能未对齐
**检测**: 搜索对网络包数据的强制类型转换

```c
// 问题：可能未对齐
struct iphdr *iph = (struct iphdr *)(pkt->data + offset);
uint32_t src = iph->saddr;  // 未对齐访问
```

```c
// 修复：使用 memcpy
uint32_t src;
memcpy(&src, &iph->saddr, sizeof(src));
```

---

### [低] 日志在热路径

**类别**: IO / CPU
**现象**: 在包处理循环中调用 syslog/printf/fprintf
**检测**: 搜索热路径中的日志函数调用

```c
// 问题：每个包都打日志
void process_packet(struct pkt *p) {
    LOG_INFO("Processing packet from %s", ip_to_str(p->src));
    // ... 处理
}
```

```c
// 修复：采样日志或使用 ring buffer
static uint64_t pkt_count = 0;

void process_packet(struct pkt *p) {
    if (++pkt_count % 10000 == 0) {
        LOG_INFO("Processed %lu packets", pkt_count);
    }
    // ... 处理
}
```

---

## Go 语言

### [高] goroutine 泄漏

**类别**: 内存 / 调度
**现象**: 启动 goroutine 后无法退出，持续累积
**检测**: 搜索 `go func` 和 `go `，检查是否有退出机制

```go
// 问题：goroutine 永远不退出
func handleConn(conn net.Conn) {
    go func() {
        for {
            data := make([]byte, 1024)
            n, err := conn.Read(data)
            if err != nil {
                return  // 只退出这个 goroutine，但外层可能还在等
            }
            process(data[:n])
        }
    }()
    // 如果这里也有阻塞操作且没有 context 取消...
}
```

```go
// 修复：使用 context 控制生命周期
func handleConn(ctx context.Context, conn net.Conn) {
    go func() {
        defer conn.Close()
        for {
            select {
            case <-ctx.Done():
                return
            default:
            }
            conn.SetReadDeadline(time.Now().Add(time.Second))
            data := make([]byte, 1024)
            n, err := conn.Read(data)
            if err != nil {
                return
            }
            process(data[:n])
        }
    }()
}
```

---

### [高] 锁竞争热点

**类别**: 锁 / 并发
**现象**: 多个 goroutine 频繁竞争同一把锁
**检测**: 搜索 sync.Mutex/RWMutex，检查锁的持有时间和频率

```go
// 问题：全局锁保护计数器
var (
    mu       sync.Mutex
    counters map[string]int64
)

func Incr(key string) {
    mu.Lock()
    counters[key]++
    mu.Unlock()
}
```

```go
// 修复：分片计数器
const numShards = 64

type ShardedCounter struct {
    shards [numShards]struct {
        mu    sync.Mutex
        items map[string]int64
    }
}

func (c *ShardedCounter) Incr(key string) {
    shard := &c.shards[fnv32(key)%numShards]
    shard.mu.Lock()
    shard.items[key]++
    shard.mu.Unlock()
}
```

---

### [高] channel 使用不当

**类别**: 调度 / 内存
**现象**: 无缓冲 channel 导致 goroutine 阻塞，或缓冲区无限增长
**检测**: 搜索 `make(chan`，检查缓冲大小和使用模式

```go
// 问题：无缓冲 channel，发送方阻塞
ch := make(chan *Packet)
go func() {
    for pkt := range ch {
        process(pkt)
    }
}()
// 如果 process 很慢，发送方会阻塞
```

```go
// 修复：有缓冲 channel + 背压
ch := make(chan *Packet, 4096)

select {
case ch <- pkt:
default:
    // 队列满，丢弃或降级处理
    metrics.Incr("drop_full_queue")
}
```

---

### [中] 内存逃逸

**类别**: 内存
**现象**: 局部变量逃逸到堆上，增加 GC 压力
**检测**: `go build -gcflags='-m'` 检查逃逸分析

```go
// 问题：返回局部变量指针，逃逸到堆
func newBuffer() *[]byte {
    buf := make([]byte, 4096)
    return &buf  // 逃逸
}
```

```go
// 修复：使用 sync.Pool
var bufPool = sync.Pool{
    New: func() interface{} {
        buf := make([]byte, 4096)
        return &buf
    },
}

func getBuffer() *[]byte {
    return bufPool.Get().(*[]byte)
}

func putBuffer(buf *[]byte) {
    bufPool.Put(buf)
}
```

---

### [中] 字符串拼接

**类别**: CPU / 内存
**现象**: 循环中用 `+` 拼接字符串
**检测**: 搜索循环中的字符串 `+` 操作

```go
// 问题：循环拼接，每次分配新内存
var result string
for _, s := range parts {
    result += s  // O(n^2)
}
```

```go
// 修复：使用 strings.Builder
var builder strings.Builder
builder.Grow(totalLen)  // 预分配
for _, s := range parts {
    builder.WriteString(s)
}
result := builder.String()
```

---

### [中] map 未预分配

**类别**: 内存
**现象**: map 未指定初始容量，频繁扩容
**检测**: 搜索 `make(map[`，检查是否指定容量

```go
// 问题：未预分配
m := make(map[string]int)
for _, item := range items {
    m[item.Key] = item.Val  // 频繁扩容
}
```

```go
// 修复：预分配
m := make(map[string]int, len(items))
```

---

### [低] time.After 在循环中

**类别**: 内存
**现象**: select 中使用 time.After 导致每次循环创建新 timer
**检测**: 搜索循环中的 `time.After`

```go
// 问题：每次循环创建新 timer
for {
    select {
    case <-ch:
        // handle
    case <-time.After(time.Second):  // 每次都创建新 timer
        // timeout
    }
}
```

```go
// 修复：复用 timer
timer := time.NewTimer(time.Second)
defer timer.Stop()

for {
    timer.Reset(time.Second)
    select {
    case <-ch:
        // handle
    case <-timer.C:
        // timeout
    }
}
```

---

## Python 语言

### [高] 同步阻塞在异步上下文

**类别**: IO / 调度
**现象**: 在 asyncio 事件循环中调用阻塞操作
**检测**: 搜索 async def 中的 time.sleep、requests、socket.recv 等

```python
# 问题：阻塞调用卡住事件循环
async def handle_request(request):
    data = requests.get(url)  # 阻塞！
    result = await process(data)
    return result
```

```python
# 修复：使用异步库或 run_in_executor
import aiohttp

async def handle_request(request):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
    result = await process(data)
    return result

# 或者用线程池执行阻塞操作
import asyncio
loop = asyncio.get_event_loop()
data = await loop.run_in_executor(None, requests.get, url)
```

---

### [高] GIL 竞争

**类别**: CPU / 并发
**现象**: CPU 密集型任务在多线程中运行，受 GIL 限制
**检测**: 搜索 threading.Thread 用于 CPU 密集任务

```python
# 问题：CPU 密集型用线程，受 GIL 限制
import threading

def compute(data):
    # CPU 密集计算
    return heavy_computation(data)

threads = [threading.Thread(target=compute, args=(d,)) for d in data_list]
for t in threads:
    t.start()
```

```python
# 修复：使用多进程
from concurrent.futures import ProcessPoolExecutor

with ProcessPoolExecutor() as executor:
    results = list(executor.map(compute, data_list))
```

---

### [高] 纯 Python 热循环

**类别**: CPU
**现象**: 高频调用的函数是纯 Python，没有利用 C 扩展
**检测**: 搜索被频繁调用的 Python 循环（特别是包处理、协议解析）

```python
# 问题：纯 Python 解析，慢
def parse_packet(data: bytes) -> dict:
    result = {}
    result['version'] = data[0] >> 4
    result['ihl'] = data[0] & 0xF
    result['total_len'] = (data[2] << 8) | data[3]
    # ... 逐字节解析
    return result
```

```python
# 修复：使用 struct 模块或 C 扩展
import struct

def parse_packet(data: bytes) -> dict:
    ver_ihl, tos, total_len, ident, flags_frag, ttl, proto, cksum, src, dst = \
        struct.unpack('!BBHHHBBHII', data[:20])
    return {
        'version': ver_ihl >> 4,
        'ihl': ver_ihl & 0xF,
        'total_len': total_len,
        'src': src,
        'dst': dst,
    }
```

---

### [中] 内存引用环

**类别**: 内存
**现象**: 对象互相引用，gc.collect 才能回收
**检测**: 搜索双向引用、parent-child 引用

```python
# 问题：互相引用
class Node:
    def __init__(self):
        self.parent = None
        self.children = []

    def add_child(self, child):
        child.parent = self  # 双向引用
        self.children.append(child)
```

```python
# 修复：使用 weakref
import weakref

class Node:
    def __init__(self):
        self._parent = None
        self.children = []

    @property
    def parent(self):
        return self._parent() if self._parent else None

    def add_child(self, child):
        child._parent = weakref.ref(self)
        self.children.append(child)
```

---

### [中] 无界缓存

**类别**: 内存
**现象**: dict/list 无限增长，没有淘汰机制
**检测**: 搜索作为缓存使用的 dict，检查是否有大小限制

```python
# 问题：缓存无限增长
cache = {}

def get_user(user_id):
    if user_id not in cache:
        cache[user_id] = db.query(user_id)
    return cache[user_id]
```

```python
# 修复：使用 LRU 缓存
from functools import lru_cache

@lru_cache(maxsize=10000)
def get_user(user_id):
    return db.query(user_id)

# 或手动实现
from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity):
        self.cache = OrderedDict()
        self.capacity = capacity

    def get(self, key):
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def put(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
```

---

### [中] 缺少批量操作

**类别**: IO / CPU
**现象**: 逐条处理数据，没有利用批量操作
**检测**: 搜索循环中的单条数据库查询、单条消息发送

```python
# 问题：逐条查询
async def get_users(user_ids):
    results = []
    for uid in user_ids:
        user = await db.query(f"SELECT * FROM users WHERE id = {uid}")
        results.append(user)
    return results
```

```python
# 修复：批量查询
async def get_users(user_ids):
    placeholders = ','.join(['%s'] * len(user_ids))
    return await db.query(
        f"SELECT * FROM users WHERE id IN ({placeholders})",
        user_ids
    )
```

---

### [低] 异常处理在热路径

**类别**: CPU
**现象**: 用 try/except 做流程控制
**检测**: 搜索热路径中的 try/except

```python
# 问题：用异常做流程控制
def find_item(items, key):
    try:
        return items[key]
    except KeyError:
        return None  # 频繁触发异常
```

```python
# 修复：使用 get
def find_item(items, key):
    return items.get(key)
```

---

### [高] 频繁 IO/数据库操作

**类别**: CPU / IO
**现象**: 周期性或高频的 IO/数据库操作导致 CPU 飙高（上下文切换、syscall 开销、锁等待）
**检测**: 搜索循环中的文件读写、数据库查询、Redis/Memcached 操作

```go
// 问题：每次请求都查数据库
func handleRequest(req *Request) {
    user := db.Query("SELECT * FROM users WHERE id = ?", req.UserID)  // 每次都查
    orders := db.Query("SELECT * FROM orders WHERE user_id = ?", req.UserID)
    // ...
}
```

```go
// 修复：使用本地缓存
var (
    userCache  = sync.Map{}  // 或使用 lru.Cache
    cacheTTL   = 5 * time.Minute
)

func handleRequest(req *Request) {
    if cached, ok := userCache.Load(req.UserID); ok {
        entry := cached.(*CacheEntry)
        if time.Since(entry.Time) < cacheTTL {
            return entry.Data
        }
    }
    user := db.Query("SELECT * FROM users WHERE id = ?", req.UserID)
    userCache.Store(req.UserID, &CacheEntry{Data: user, Time: time.Now()})
    // ...
}
```

---

### [中] 周期性文件/日志 IO

**类别**: CPU / IO
**现象**: 定时任务频繁写日志、刷新配置、同步状态，导致 CPU 飙高
**检测**: 搜索 ticker/cron 中的文件操作、日志写入

```go
// 问题：每秒写一次统计文件
ticker := time.NewTicker(time.Second)
for range ticker.C {
    stats := collectStats()
    data, _ := json.Marshal(stats)
    os.WriteFile("/tmp/stats.json", data, 0644)  // 每秒写文件
    log.Printf("Stats: %s", data)  // 每秒打日志
}
```

```go
// 修复：批量写 + 异步日志
ticker := time.NewTicker(10 * time.Second)
for range ticker.C {
    stats := collectStats()
    data, _ := json.Marshal(stats)
    // 使用 buffer 写入，减少 syscall
    var buf bytes.Buffer
    buf.Write(data)
    os.WriteFile("/tmp/stats.json", buf.Bytes(), 0644)
    // 日志异步写
    go func() { log.Printf("Stats: %s", data) }()
}
```

---

### [中] 数据库连接池不当

**类别**: CPU / IO
**现象**: 数据库连接池过小导致请求排队，或过大导致连接管理开销
**检测**: 检查数据库连接池配置

```go
// 问题：连接池过小
db, _ := sql.Open("mysql", dsn)
db.SetMaxOpenConns(5)  // 5 个连接，高并发下排队
```

```go
// 修复：合理配置连接池
db, _ := sql.Open("mysql", dsn)
db.SetMaxOpenConns(100)           // 最大连接数
db.SetMaxIdleConns(25)            // 空闲连接数
db.SetConnMaxLifetime(5 * time.Minute)  // 连接最大生命周期
db.SetConnMaxIdleTime(1 * time.Minute)  // 空闲连接最大生命周期
```

---

### [高] Python 频繁 IO/数据库操作

**类别**: CPU / IO
**现象**: 同步 IO/数据库操作阻塞事件循环，或频繁调用导致 CPU 飙高
**检测**: 搜索 async def 中的同步 IO、循环中的数据库调用

```python
# 问题：每次请求都查数据库，阻塞事件循环
async def handle_request(request):
    user = db.query(f"SELECT * FROM users WHERE id = {request.user_id}")  # 同步阻塞！
    orders = db.query(f"SELECT * FROM orders WHERE user_id = {request.user_id}")
    return {"user": user, "orders": orders}
```

```python
# 修复：使用异步数据库驱动 + 缓存
import asyncio
import aioredis

cache = aioredis.from_url("redis://localhost")

async def handle_request(request):
    # 先查缓存
    cached = await cache.get(f"user:{request.user_id}")
    if cached:
        return json.loads(cached)

    # 异步查数据库
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE id = $1", request.user_id
        )
    result = dict(user)
    await cache.setex(f"user:{request.user_id}", 300, json.dumps(result))
    return result
```

---

### [中] Python 同步文件 IO

**类别**: CPU / IO
**现象**: 在异步上下文中使用同步文件操作
**检测**: 搜索 async def 中的 open/read/write

```python
# 问题：同步文件操作阻塞事件循环
async def load_config():
    with open("config.json") as f:  # 同步阻塞
        return json.load(f)
```

```python
# 修复：使用 aiofiles 或 run_in_executor
import aiofiles

async def load_config():
    async with aiofiles.open("config.json") as f:
        content = await f.read()
        return json.loads(content)

# 或使用线程池
async def load_config():
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _load_config_sync)

def _load_config_sync():
    with open("config.json") as f:
        return json.load(f)
```

---

### [中] Python 定时任务干扰主路径

**类别**: 调度 / CPU
**现象**: 定时任务（统计上报、规则刷新、会话清理、健康检查）抢占主线程 CPU 或阻塞 asyncio 事件循环
**检测**: 搜索 `time.sleep`、`threading.Timer`、`schedule`、`APScheduler`、`asyncio.create_task` + `while True`、`celery beat`

```python
# 问题1：定时器用 sleep 阻塞主线程
def stats_report():
    while True:
        report_stats()   # 同步操作，可能阻塞主线程
        time.sleep(10)   # 固定间隔，可能与业务线程竞争

threading.Thread(target=stats_report, daemon=True).start()
```

```python
# 问题2：asyncio 中用 time.sleep 阻塞事件循环
async def periodic_cleanup():
    while True:
        cleanup_sessions()  # 同步操作！阻塞事件循环
        time.sleep(60)      # 同步 sleep！阻塞事件循环

asyncio.create_task(periodic_cleanup())
```

```python
# 修复1：使用独立线程执行后台任务
import threading

def stats_report():
    while True:
        report_stats()
        time.sleep(10)

# 使用独立线程，不占用主线程
t = threading.Thread(target=stats_report, daemon=True, name="stats-report")
t.start()
```

```python
# 修复2：asyncio 中使用 asyncio.sleep 而非 time.sleep
async def periodic_cleanup():
    while True:
        await cleanup_sessions_async()  # 异步操作
        await asyncio.sleep(60)          # 非阻塞 sleep

asyncio.create_task(periodic_cleanup())
```

```python
# 修复3：使用 sched 模块的定时器（需在独立线程中运行）
import sched
import time
import threading

def run_periodic_task(interval, func):
    """在独立线程中运行定时任务"""
    scheduler = sched.scheduler(time.time, time.sleep)

    def _run():
        func()
        scheduler.enter(interval, 1, _run)

    scheduler.enter(interval, 1, _run)
    scheduler.run()  # 阻塞，因此必须在独立线程中调用

# 启动定时任务线程
t = threading.Thread(target=run_periodic_task, args=(10, report_stats),
                     daemon=True, name="periodic-task")
t.start()
```

**网络设备场景特别注意**：
- 定时任务如规则同步、签名更新、会话清理，不能和数据面共享 CPU 核
- Python 服务做控制面时，定时任务应避免同步 IO、避免占用事件循环
- 如果定时任务需要遍历大量会话表/规则表，应分批处理而非一次性全量扫描

---

## 网络设备专项

### [高] 控制面干扰数据面

**类别**: 调度 / 吞吐
**现象**: 控制面任务（配置更新、规则下发、日志）与数据面转发在同一 CPU 核上运行
**检测**: 检查线程亲和性设置、是否有 CPU 隔离

```c
// 问题：控制面和数据面共享 CPU
void start_threads() {
    pthread_create(&ctrl_thread, NULL, control_plane, NULL);
    pthread_create(&data_thread, NULL, data_plane, NULL);
    // 没有设置 CPU 亲和性
}
```

```c
// 修复：CPU 隔离
void start_threads() {
    cpu_set_t cpuset;

    // 控制面绑定到 CPU 0-1
    CPU_ZERO(&cpuset);
    CPU_SET(0, &cpuset);
    CPU_SET(1, &cpuset);
    pthread_setaffinity_np(ctrl_thread, sizeof(cpuset), &cpuset);

    // 数据面绑定到 CPU 2-N
    CPU_ZERO(&cpuset);
    for (int i = 2; i < num_cpus; i++)
        CPU_SET(i, &cpuset);
    pthread_setaffinity_np(data_thread, sizeof(cpuset), &cpusat);
}
```

---

### [高] 定时任务影响实时流量

**类别**: 调度 / 时延
**现象**: 定时任务（规则同步、签名更新、统计上报）抢占转发线程 CPU
**检测**: 检查定时任务的 CPU 亲和性和优先级

```c
// 问题：定时任务和转发线程同优先级
void *timer_task(void *arg) {
    while (1) {
        sleep(10);
        sync_rules();      // 可能耗时很长
        update_signatures();
    }
}
```

```c
// 修复：定时任务降优先级 + 绑定独立 CPU
void *timer_task(void *arg) {
    // 降低优先级
    nice(10);
    // 绑定到控制面 CPU
    cpu_set_t cpuset;
    CPU_ZERO(&cpusat);
    CPU_SET(0, &cpuset);
    sched_setaffinity(0, sizeof(cpuset), &cpuset);

    while (1) {
        sleep(10);
        sync_rules();
    }
}
```

---

### [中] per-packet 开销过大

**类别**: CPU / 吞吐
**现象**: 小包场景下 per-packet 处理开销成为瓶颈
**检测**: 检查是否有 per-packet 的内存分配、锁、日志

```c
// 问题：每个包都查会话表 + 打日志
int forward(struct pkt *p) {
    struct session *s = session_lookup(p);  // 锁 + hash
    if (!s) {
        LOG(INFO, "New session");  // syscall
        s = session_create(p);
    }
    LOG(DEBUG, "Forwarding packet");  // syscall
    return send_packet(p, s->out_if);
}
```

```c
// 修复：批量处理 + 采样日志
int forward_batch(struct pkt **pkts, int n) {
    struct session *sessions[n];
    session_lookup_batch(pkts, sessions, n);  // 批量查找
    for (int i = 0; i < n; i++) {
        if (!sessions[i]) {
            sessions[i] = session_create(pkts[i]);
        }
    }
    send_packet_batch(pkts, sessions, n);  // 批量发送
}
```

---

### [低] 会话表热点

**类别**: 锁 / CPU
**现象**: 会话表成为全局热点，所有核都竞争同一把锁
**检测**: 检查会话表的锁设计

```c
// 问题：全局锁
static pthread_mutex_t session_lock;
struct session *session_lookup(struct pkt *p) {
    pthread_mutex_lock(&session_lock);
    // ...
    pthread_mutex_unlock(&session_lock);
}
```

```c
// 修复：RCU 或 per-CPU 会话表
// RCU 方案
struct session *session_lookup(struct pkt *p) {
    rcu_read_lock();
    struct session *s = rcu_dereference(session_table[hash]);
    rcu_read_unlock();
    return s;
}

// 或 per-CPU 方案
DEFINE_PER_CPU(struct session_table, session_tables);
```
