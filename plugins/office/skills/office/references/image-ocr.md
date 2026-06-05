# 图片与 OCR 处理指南

## 目录
- [读取图片基本信息](#读取图片基本信息)
- [OCR 图像预处理](#ocr-图像预处理)
- [OCR 识别](#ocr-识别)

> **相关文档**：环境依赖缺失时参见 `references/setup.md`；PDF OCR 流程参见 `references/pdf-read.md`

---

## 读取图片基本信息

```bash
~/.local/pyoffice/bin/python -c "
from PIL import Image
img = Image.open('photo.jpg')
print(f'格式: {img.format}, 尺寸: {img.size}, 模式: {img.mode}')
img.close()
"
```

---

## OCR 图像预处理

提升 OCR 识别率的预处理步骤：

```bash
~/.local/pyoffice/bin/python << 'PYEOF'
import cv2

img = cv2.imread('scan.png')
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Otsu 自适应二值化
_, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

# 降噪
denoised = cv2.fastNlMeansDenoising(binary)

# 可选：膨胀/腐蚀（去除噪点）
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
cleaned = cv2.morphologyEx(denoised, cv2.MORPH_CLOSE, kernel)

cv2.imwrite('preprocessed.png', cleaned)
print('预处理完成: preprocessed.png')
PYEOF
```

---

## OCR 识别

### 使用 pytesseract（需 uv 环境）

```bash
~/.local/pyoffice/bin/python -c "
import pytesseract
from PIL import Image
img = Image.open('preprocessed.png')
# 英文: lang='eng', 中文: lang='chi_sim'
print(pytesseract.image_to_string(img, lang='chi_sim+eng'))
"
```

### 使用 tesseract 命令行

```bash
tesseract preprocessed.png output -l chi_sim+eng
cat output.txt
```
