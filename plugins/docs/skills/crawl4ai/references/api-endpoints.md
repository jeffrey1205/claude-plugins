# API 端点

## 基础端点

- `GET /health` - 健康检查
- `POST /md` - Markdown 生成

## Markdown 端点参数

```json
{
  "url": "https://example.com",
  "f": "fit",
  "wait_for": 2,
  "c": "0"
}
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `url` | 目标 URL | 必填 |
| `f` | 过滤模式：raw/fit/bm25/llm | fit |
| `wait_for` | 等待 JS 渲染秒数 | 2 |
| `c` | 缓存：0=禁用，1=启用 | 0 |

## 过滤模式说明

- `raw` - 原始 Markdown，无过滤
- `fit` - 智能过滤，移除导航栏、侧边栏、广告，保留正文
- `bm25` - 基于 BM25 的相关性过滤
- `llm` - LLM 辅助过滤（需要 API key）

## 调用示例

```bash
curl -X POST http://127.0.0.1:11235/md \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "f": "fit", "wait_for": 2}'
```

## 可选参数

用户可通过以下参数调整：

- `--wait=N` - 自定义等待时间
- `--selector=CSS` - 指定抓取特定部分
- `--raw` - 禁用内容过滤
- `--save` - 保存到 md 文件（自动命名：`crawl4ai_<timestamp>.md`）
- `--save <filename>` - 保存到指定文件

## 输出方式

**默认行为：**
- 抓取完成后直接输出 Markdown 到终端
- 用户可立即查看内容

**保存提示：**
- 抓取完成后询问用户是否需要保存
- 如果用户确认保存，生成文件名或使用用户指定名称

## 错误码处理

| HTTP 状态 | 说明 |
|-----------|------|
| 200 | 成功 |
| 400 | URL 无效 |
| 403 | 被反爬虫拦截 |
| 404 | 页面不存在 |
| 500 | 服务器错误 |
| timeout | 页面加载超时 |