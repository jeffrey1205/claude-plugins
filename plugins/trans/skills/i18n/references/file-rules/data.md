# 数据文件翻译规则

## 通用规则

以下规则适用于 JSON、YAML、CSV、XML：

**可翻译的键**：仅翻译 `description`、`title`、`label`、`name`（仅当值为人类可读文本而非标识符时）、`message`、`summary`、`help`、`comment`、`note` 对应的字符串值。

**不翻译的键**：`tags`、`keywords`、`category`、`type`、`id`、`slug`、`endpoint`、`path` 等标识符类键的值保持原样。

**始终不翻译**：布尔值、数字、null、键名、术语保护列表中的术语。

## JSON（.json）

- 数组结构保持不变
- 术语保护在字符串值中生效

### 示例

```json
原始:
{
  "name": "user_login",
  "description": "User login event",
  "enabled": true,
  "severity": 5,
  "tags": ["security", "authentication"]
}

翻译后:
{
  "name": "user_login",
  "description": "用户登录事件",
  "enabled": true,
  "severity": 5,
  "tags": ["security", "authentication"]
}
```

## YAML（.yaml / .yml）

- 锚点和引用（`&`, `*`）不翻译
- 多行字符串（`|`, `>`）按内容类型翻译
- 术语保护在字符串值中生效

### 示例

```yaml
原始:
service:
  name: auth-service
  description: Authentication service configuration
  replicas: 3
  health_check:
    enabled: true
    path: /healthz

翻译后:
service:
  name: auth-service
  description: 认证服务配置
  replicas: 3
  health_check:
    enabled: true
    path: /healthz
```

## CSV（.csv）

### 规则

- 翻译表头和数据单元格的文本
- 保留数字、ID、URL、邮箱地址不翻译
- 保留 CSV 分隔符和引号结构
- 空单元格保持不变

### 示例

```csv
原始:
ID,Name,Description,Status
1,Login,User login endpoint,Active

翻译后:
ID,Name,Description,Status
1,Login,用户登录端点,Active
```

## XML（.xml）

### 规则

- 翻译标签间的文本内容
- 翻译注释（`<!-- 注释 -->`）
- 标签名不翻译
- 属性名不翻译
- 命名空间（xmlns）不翻译
- CDATA 区不翻译
- 技术属性的值（如 type、id、class）不翻译

### 示例

```xml
原始:
<config>
  <!-- Database configuration -->
  <database name="prod_db">
    <host>localhost</host>
    <description>Production database</description>
  </database>
</config>

翻译后:
<config>
  <!-- 数据库配置 -->
  <database name="prod_db">
    <host>localhost</host>
    <description>生产数据库</description>
  </database>
</config>
```
