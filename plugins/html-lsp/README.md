# html-lsp

HTML、CSS 和 ESLint 语言服务器集成，基于 `@zed-industries/vscode-langservers-extracted` 项目。

## 功能

- **HTML 语言服务器**：语法检查、标签补全、嵌入样式/脚本校验
- **CSS 语言服务器**：语法检查、属性补全、SCSS/SASS/Less 支持
- **ESLint 语言服务器**：JS/TS/JSX/TSX/Vue/Svelte/Astro 实时 lint 诊断

## 安装

```bash
npm install -g @zed-industries/vscode-langservers-extracted
npm install --save-dev eslint
```

## 支持的文件类型

| 服务器 | 扩展名 |
|--------|--------|
| HTML | `.html`, `.htm` |
| CSS | `.css`, `.scss`, `.sass`, `.less` |
| ESLint | `.js`, `.jsx`, `.mjs`, `.cjs`, `.ts`, `.tsx`, `.vue`, `.svelte`, `.astro` |
