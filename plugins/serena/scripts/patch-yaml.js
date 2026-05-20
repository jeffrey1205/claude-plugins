const fs = require('fs');
const os = require('os');
const path = require('path');
const { execSync } = require('child_process');

// 支持的语言服务器列表
const LANGUAGE_SERVERS = [
    { name: 'cpp', command: 'clangd' },
    { name: 'bash', command: 'bash-language-server' },
    { name: 'typescript', command: 'typescript-language-server' }
];

// 动态获取语言服务器路径，如果不存在则返回 null
function getLsPath(cmd) {
    try {
        return execSync(`command -v ${cmd}`, { encoding: 'utf8' }).trim();
    } catch(e) {
        return null;
    }
}

// 在 ls_specific_settings 块内查找指定语言的索引（2 空格缩进）
function findLanguageIndex(lines, lsIdx, langName) {
    for (let i = lsIdx + 1; i < lines.length; i++) {
        if (lines[i].trim() && !/^[ \t]/.test(lines[i])) break; // 离开块
        if (new RegExp(`^  ${langName}:\\s*$`).test(lines[i])) return i;
    }
    return -1;
}

// 在指定位置插入或更新语言配置
function insertOrUpdateLanguage(lines, lsIdx, langName, lsPath) {
    const langIdx = findLanguageIndex(lines, lsIdx, langName);
    const lsPathLine = '    ls_path: "' + lsPath + '"';

    if (langIdx === -1) {
        // 场景 B：没有该语言配置，在 ls_specific_settings: 下一行插入
        lines.splice(lsIdx + 1, 0, '  ' + langName + ':', lsPathLine);
        console.log(`追加 ${langName}.ls_path: ${lsPath}`);
        return true;
    }

    // 场景 C：已有该语言配置
    const nextLine = lines[langIdx + 1];
    if (nextLine && /ls_path:/.test(nextLine)) {
        if (nextLine.includes(lsPath)) {
            console.log(`${langName}.ls_path 已正确: ${lsPath}`);
            return false;
        } else {
            lines[langIdx + 1] = lsPathLine;
            console.log(`覆写 ${langName}.ls_path → ${lsPath}`);
            return true;
        }
    } else {
        lines.splice(langIdx + 1, 0, lsPathLine);
        console.log(`在 ${langName}: 下方插入 ls_path`);
        return true;
    }
}

// 核心补丁逻辑
function executePatch(configFile, languages) {
    let content = fs.readFileSync(configFile, 'utf8');

    // 1. 必须有 ls_specific_settings 关键字
    if (!content.includes('ls_specific_settings:')) {
        console.log('未找到 ls_specific_settings，跳过。');
        return true;
    }

    // 2. 场景 A：空对象 {}
    if (/ls_specific_settings:\s*\{\s*\}/.test(content)) {
        // 动态生成配置内容
        const langConfigs = languages.map(lang =>
            `  ${lang.name}:\n    ls_path: "${lang.path}"`
        ).join('\n');
        const replacement = 'ls_specific_settings:\n' + langConfigs;
        content = content.replace(/ls_specific_settings:\s*\{\s*\}/, replacement);
        fs.writeFileSync(configFile, content, 'utf8');
        console.log('原始空配置 → 已配置: ' + languages.map(l => l.name).join(', '));
        return true;
    }

    // 3. 场景 B/C：按行处理
    const lines = content.split(/\r?\n/);
    const lsIdx = lines.findIndex(l => /^\s*ls_specific_settings:\s*$/.test(l));
    if (lsIdx === -1) {
        console.log('未找到 ls_specific_settings 行，跳过。');
        return true;
    }

    let modified = false;
    for (const lang of languages) {
        if (insertOrUpdateLanguage(lines, lsIdx, lang.name, lang.path)) {
            modified = true;
        }
    }

    if (modified) {
        fs.writeFileSync(configFile, lines.join('\n'), 'utf8');
    }
    return true;
}

// 启动
try {
    const configFile = path.join(os.homedir(), '.serena', 'serena_config.yml');

    // 检测所有已安装的语言服务器
    const languages = LANGUAGE_SERVERS
        .map(ls => ({ name: ls.name, path: getLsPath(ls.command) }))
        .filter(ls => ls.path !== null);

    if (languages.length === 0) {
        console.log('未检测到任何语言服务器，跳过配置。');
        process.exit(0);
    }

    console.log('检测到语言服务器: ' + languages.map(l => `${l.name}=${l.path}`).join(', '));
    executePatch(configFile, languages);
} catch (e) {
    console.log('启动失败: ' + e.message);
}
