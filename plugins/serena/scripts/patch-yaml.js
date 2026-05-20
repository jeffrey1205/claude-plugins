const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

function writeDebugLog(msg) {
    try {
        const logPath = path.join(process.cwd(), '.serena', 'plugin-patch.log');
        const timestamp = new Date().toISOString();
        fs.appendFileSync(logPath, `[${timestamp}] ${msg}\n`, 'utf8');
    } catch(e) {}
}

// 动态获取 clangd 路径
function getClangdPath() {
    try {
        return execSync('command -v clangd', { encoding: 'utf8' }).trim();
    } catch(e) {
        return '/usr/bin/clangd';
    }
}

// 核心补丁逻辑
function executePatch(configFile, clangdPath) {
    let content = fs.readFileSync(configFile, 'utf8');

    // 1. 检查是否启用了 cpp
    const hasCppEnabled = content.split('\n').some(line => {
        return /^-\s*cpp(\s*|$)/.test(line.trim());
    });
    if (!hasCppEnabled) {
        writeDebugLog('未启用 cpp，跳过。');
        return true;
    }

    // 2. 必须有 ls_specific_settings 关键字
    if (!content.includes('ls_specific_settings:')) {
        writeDebugLog('有 cpp 但无 ls_specific_settings，跳过。');
        return true;
    }

    // 3. 场景 A：空对象 {}
    if (/ls_specific_settings:\s*\{\s*\}/.test(content)) {
        const replacement =
            'ls_specific_settings:\n' +
            '  cpp:\n' +
            '    ls_path: "' + clangdPath + '"';
        content = content.replace(/ls_specific_settings:\s*\{\s*\}/, replacement);
        fs.writeFileSync(configFile, content, 'utf8');
        writeDebugLog('原始空配置 → clangd: ' + clangdPath);
        return true;
    }

    // 4. 场景 B/C：按行处理
    const lines = content.split(/\r?\n/);
    const lsIdx = lines.findIndex(l => /^\s*ls_specific_settings:\s*$/.test(l));
    if (lsIdx === -1) {
        writeDebugLog('有 cpp 但未找到 ls_specific_settings 行，跳过。');
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
        writeDebugLog('追加 cpp.ls_path: ' + clangdPath);
        return true;
    }

    // 场景 C：已有 cpp:
    const nextLine = lines[cppIdx + 1];
    if (nextLine && /ls_path:/.test(nextLine)) {
        if (nextLine.includes(clangdPath)) {
            writeDebugLog('cpp.ls_path 已正确: ' + clangdPath);
        } else {
            lines[cppIdx + 1] = lsPath;
            fs.writeFileSync(configFile, lines.join('\n'), 'utf8');
            writeDebugLog('覆写 cpp.ls_path → ' + clangdPath);
        }
    } else {
        lines.splice(cppIdx + 1, 0, lsPath);
        fs.writeFileSync(configFile, lines.join('\n'), 'utf8');
        writeDebugLog('在 cpp: 下方插入 ls_path');
    }
    return true;
}

// 递归重试（指数退避）
function retryLoop(configFile, clangdPath, attempt, maxAttempts, delayMs) {
    if (attempt > maxAttempts) {
        writeDebugLog('已满 ' + maxAttempts + ' 次尝试，退出。');
        return;
    }

    if (fs.existsSync(configFile)) {
        try {
            const stat = fs.statSync(configFile);
            if (stat.size > 0) {
                const done = executePatch(configFile, clangdPath);
                if (done) return;
            }
        } catch (e) {
            writeDebugLog('第 ' + attempt + ' 次异常: ' + e.message);
        }
    }

    setTimeout(() => retryLoop(configFile, clangdPath, attempt + 1, maxAttempts, delayMs * 2), delayMs);
}

// 启动
try {
    const configFile = path.join(process.cwd(), '.serena', 'project.yml');
    const clangdPath = getClangdPath();
    writeDebugLog('启动: clangd=' + clangdPath);
    retryLoop(configFile, clangdPath, 1, 5, 200);
} catch (e) {
    writeDebugLog('启动失败: ' + e.message);
}
