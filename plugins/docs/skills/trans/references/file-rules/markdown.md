# Markdown 翻译规则

## YAML Front Matter 处理

文件以 `---` 开头的元数据区域：

| 字段 | 处理 |
|------|------|
| `name` | 绝对不翻译 |
| `description` | 翻译冒号后的内容 |
| 其他所有字段 | 保持原样 |

## 代码块免疫

以下代码块不翻译：

````markdown
```language
# 这段代码不翻译，只翻译注释
code here stays as-is
```
````

- 围栏代码块（````language ... ````）
- 缩进代码块（4 空格缩进）
- 行内代码（`` `code` ``）
- 无语言标记的伪代码块

代码块内仅翻译注释：
- Shell 注释：`# 注释`
- 单行注释：`// 注释`
- 多行注释：`/* 注释 */`
- Python docstring：`"""注释"""`

## 标识符保护

不翻译以下元素：
- 函数/方法签名：`discover_hosts(interface, timeout)`
- 参数名、返回值类型
- JSON 字段名和枚举值
- 库/类/层名称
- CLI 参数和命令
- 日志/协议字段名
- DNS 记录值

## 表格与结构

- 保留表格结构（`|---|---|`）
- 链接路径不变，翻译链接文本
- 保留标题层级

## 输出格式值

保持英文：YES, NO, ENABLED, DISABLED, BLOCKED, CONFIGURED, CRITICAL, HIGH, MEDIUM, LOW, PASS, FAIL
