---
name: crawl4ai
description: |
  网页内容抓取和提取工具，自动将网页转换为 LLM 友好的 Markdown 格式。
  
  **触发场景（只要涉及以下情况就使用此 skill）：**
  - 用户要抓取、爬取、获取网页内容
  - 用户要提取网页正文、去除广告导航栏
  - 用户要将网页转为 Markdown 格式
  - 用户要批量抓取多个网页
  - 用户提到知乎、雪球、博客、文档页面等需要抓取内容
  - 用户输入 URL 并想要查看其内容
  
  **关键词：** 抓取网页、爬取数据、获取页面、提取内容、网页内容、爬虫、抓博客、抓文档、抓知乎、抓雪球
  
  **不触发场景：**
  - 用户要写爬虫脚本（这是编程任务）
  - 用户要下载 PDF/图片/视频文件
  - 用户要截图网页
  - 用户要监控网站变化
  
  支持 /crawl4ai 斜杠命令手动调用。
---

# crawl4ai 网页抓取 Skill

## 使用原则

1. 自动管理容器生命周期（检测、启动、健康检查）
2. 默认启用 JS渲染和反爬虫处理
3. 使用 fit 模式过滤噪音内容
4. 处理各种异常情况并给出清晰提示
5. 默认输出到终端，可选保存到 md 文件

## 工作流程

```dot
digraph workflow {
  "接收 URL" [shape=box];
  "检测容器引擎" [shape=box];
  "引擎存在?" [shape=diamond];
  "提示安装" [shape=box];
  "检查容器状态" [shape=box];
  "容器运行?" [shape=diamond];
  "启动/重启容器" [shape=box];
  "健康检查" [shape=box];
  "就绪?" [shape=diamond];
  "等待重试" [shape=box];
  "调用 API 抓取" [shape=box];
  "处理响应" [shape=box];
  "输出 Markdown" [shape=doublecircle];

  "接收 URL" -> "检测容器引擎";
  "检测容器引擎" -> "引擎存在?";
  "引擎存在?" -> "提示安装" [label="no"];
  "引擎存在?" -> "检查容器状态" [label="yes"];
  "检查容器状态" -> "容器运行?";
  "容器运行?" -> "启动/重启容器" [label="no"];
  "容器运行?" -> "健康检查" [label="yes"];
  "启动/重启容器" -> "健康检查";
  "健康检查" -> "就绪?";
  "就绪?" -> "等待重试" [label="no"];
  "等待重试" -> "健康检查";
  "就绪?" -> "调用 API 抓取" [label="yes"];
  "调用 API 抓取" -> "处理响应";
  "处理响应" -> "输出 Markdown";
}
```

## 触发示例

**应该触发：**
- "抓取 https://example.com 的内容"
- "爬取这个网页"
- "获取 https://zhihu.com/question/xxx 的正文"
- "/crawl4ai https://example.com"

**不应该触发：**
- "帮我写一个爬虫脚本"
- "如何抓取网页数据"

## 详细步骤

### 步骤 1: URL预处理

1. 检查 URL 是否有效
2. 自动补全协议：`example.com` → `https://example.com`
3. 提取可选参数：`--wait=N`、`--selector=CSS`、`--raw`、`--save`

### 步骤 2: 容器管理

读取 `references/container.md`，执行容器检测和启动流程。

### 步骤 3: API 调用

读取 `references/api-endpoints.md`，构造请求并调用：

```bash
curl -X POST http://127.0.0.1:11235/md \
  -H "Content-Type: application/json" \
  -d '{"url": "<URL>", "f": "fit", "wait_for": 2}'
```

### 步骤 4: 结果处理

- 成功：输出 Markdown 内容到终端
- 内容过大（>100KB）：警告并可选截断
- 内容为空：提示可能需要调整参数
- 错误：根据错误类型给出具体提示

### 步骤 5: 保存提示

抓取完成后询问用户是否需要保存到 md 文件：
- 如果用户指定 `--save` 参数，直接保存
- 如果用户指定 `--save <filename>`，保存到指定文件
- 否则询问用户是否需要保存

## 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `--wait=N` | 自定义等待 JS 渲染时间 | `--wait=5` |
| `--selector=CSS` | 指定抓取特定部分 | `--selector=".article"` |
| `--raw` | 禁用内容过滤 | `--raw` |
| `--save` | 保存到 md 文件（自动命名） | `--save` |
| `--save <filename>` | 保存到指定文件 | `--save output.md` |

## 错误处理

| 错误类型 | 提示信息 |
|---------|---------|
| 无容器引擎 | "未检测到 podman 或 docker，请先安装" |
| 容器启动失败 | "容器启动失败：<错误详情>" |
| 健康检查超时 | "容器未就绪，请手动检查：$ENGINE logs crawl4ai" |
| URL 无效 | "URL 格式错误，请检查" |
| HTTP 403 | "页面拒绝访问，可能有反爬虫保护" |
| HTTP 404 | "页面不存在" |
| 内容为空 | "抓取内容为空，尝试使用 --raw 参数" |
| 内容过大 | "内容超过 100KB，建议分段处理" |

## 参考文档

- `references/container.md` - 容器管理详细逻辑
- `references/api-endpoints.md` - API 端点和参数说明