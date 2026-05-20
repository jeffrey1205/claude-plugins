const fs = require('fs');
const os = require('os');
const path = require('path');
const { execSync } = require('child_process');

// 动态获取 clangd 路径，如果不存在则退出
function getClangdPath() {
    try {
        return execSync('command -v clangd', { encoding: 'utf8' }).trim();
    } catch(e) {
        console.log('系统未安装 clangd，跳过配置。');
        return null;
    }
}

// 核心补丁逻辑
function executePatch(configFile, clangdPath) {
    let content = fs.readFileSync(configFile, 'utf8');

    // 1. 必须有 ls_specific_settings 关键字
    if (!content.includes('ls_specific_settings:')) {
        console.log('未找到 ls_specific_settings，跳过。');
        return true;
    }

    // 2. 场景 A：空对象 {}
    if (/ls_specific_settings:\s*\{\s*\}/.test(content)) {
        const replacement =
            'ls_specific_settings:\n' +
            '  cpp:\n' +
            '    ls_path: "' + clangdPath + '"';
        content = content.replace(/ls_specific_settings:\s*\{\s*\}/, replacement);
        fs.writeFileSync(configFile, content, 'utf8');
        console.log('原始空配置 → clangd: ' + clangdPath);
        return true;
    }

    // 3. 场景 B/C：按行处理
    const lines = content.split(/\r?\n/);
    const lsIdx = lines.findIndex(l => /^\s*ls_specific_settings:\s*$/.test(l));
    if (lsIdx === -1) {
        console.log('未找到 ls_specific_settings 行，跳过。');
        return true;
    }

    // 在 ls_specific_settings 块内查找 cpp:（2 空格缩进）
    let cppIdx = -1;
    for (let i = lsIdx + 1; i < lines.length; i++) {
        if (lines[i].trim() && !/^[ \t]/.test(lines[i])) break; // 离开块
        if (/^  cpp:\s*$/.test(lines[i])) { cppIdx = i; break; }
    }

    const lsPath = '    ls_path: "' + clangdPath + '"';

    if (cppIdx === -1) {
        // 场景 B：没有 cpp，在 ls_specific_settings: 下一行插入
        lines.splice(lsIdx + 1, 0, '  cpp:', lsPath);
        fs.writeFileSync(configFile, lines.join('\n'), 'utf8');
        console.log('追加 cpp.ls_path: ' + clangdPath);
        return true;
    }

    // 场景 C：已有 cpp:
    const nextLine = lines[cppIdx + 1];
    if (nextLine && /ls_path:/.test(nextLine)) {
        if (nextLine.includes(clangdPath)) {
            console.log('cpp.ls_path 已正确: ' + clangdPath);
        } else {
            lines[cppIdx + 1] = lsPath;
            fs.writeFileSync(configFile, lines.join('\n'), 'utf8');
            console.log('覆写 cpp.ls_path → ' + clangdPath);
        }
    } else {
        lines.splice(cppIdx + 1, 0, lsPath);
        fs.writeFileSync(configFile, lines.join('\n'), 'utf8');
        console.log('在 cpp: 下方插入 ls_path');
    }
    return true;
}

// 启动
try {
    const configFile = path.join(os.homedir(), '.serena', 'serena_config.yml');
    const clangdPath = getClangdPath();
    if (!clangdPath) {
        process.exit(0);
    }
    console.log('启动: clangd=' + clangdPath);
    executePatch(configFile, clangdPath);
} catch (e) {
    console.log('启动失败: ' + e.message);
}
