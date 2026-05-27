# 容器管理

## 容器引擎检测

优先检测 podman，其次 docker：

```bash
detect_engine() {
  if command -v podman &> /dev/null; then
    echo "podman"
  elif command -v docker &> /dev/null; then
    echo "docker"
  else
    echo "none"
  fi
}
```

## 容器启动流程

1. 检测容器引擎
2. 检查容器是否存在：`$ENGINE ps -a --format '{{.Names}}' | grep -q "crawl4ai"`
3. 检查容器是否运行：`$ENGINE ps --format '{{.Names}}' | grep -q "crawl4ai"`
4. 如果不存在，创建并启动：
   ```bash
   # 先检查镜像是否存在，不存在才拉取
   if ! $ENGINE image inspect unclecode/crawl4ai:latest &> /dev/null; then
     $ENGINE pull unclecode/crawl4ai:latest
   fi
   
   $ENGINE run -d \
     --name crawl4ai \
     -p 127.0.0.1:11235:11235 \
     --shm-size=1g \
     unclecode/crawl4ai:latest
   ```
5. 如果存在但未运行，启动：`$ENGINE start crawl4ai`

## 健康检查

等待容器就绪（最多 30 秒）：

```bash
for i in {1..30}; do
  if curl -s http://127.0.0.1:11235/health | grep -q "ok"; then
    echo "容器就绪"
    break
  fi
  sleep 1
done
```

## 错误处理

| 错误 | 处理 |
|------|------|
| 无容器引擎 | 提示安装 podman 或 docker |
| 镜像拉取失败 | 显示错误，建议检查网络 |
| 端口占用 | 提示 11235 端口被占用 |
| 权限问题 | 提示可能需要 sudo 或加入 docker/podman 组 |