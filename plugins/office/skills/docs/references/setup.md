# 环境安装指南

## 目录
- [第一步：创建 uv 虚拟环境并安装所有 Python 库](#第一步创建-uv-虚拟环境并安装所有-python-库)
- [第二步：安装系统命令行工具](#第二步安装系统命令行工具需要-sudo)
- [第三步：验证](#第三步验证)
- [注意事项](#注意事项)

---

## 第一步：创建 uv 虚拟环境并安装所有 Python 库

```bash
# 创建虚拟环境（如已存在可跳过）
uv venv ~/.local/pyoffice --python python3

# 安装所有文档处理相关的 Python 库
uv pip install --upgrade --python ~/.local/pyoffice/bin/python --no-cache --link-mode=copy \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    python-docx python-pptx pillow opencv-python-headless pytesseract \
    pymupdf openpyxl xlrd pandas
```

---

## 第二步：安装系统命令行工具（需要 sudo）

```bash
sudo apt install -y poppler-utils antiword \
    tesseract-ocr tesseract-ocr-eng tesseract-ocr-chi-sim
```

---

## 第三步：验证

重新运行检测脚本（在 SKILL.md 中），确认所有工具就绪。

---

## 注意事项

- 如果当前机器没有 `uv`，先安装：`curl -LsSf https://astral.sh/uv/install.sh | sh`
- 所有 Python 库统一在 `~/.local/pyoffice` 虚拟环境中管理，使用 `~/.local/pyoffice/bin/python` 调用
- 如果是 Debian 系以外的 Linux，apt 包名可能不同，需酌情调整
