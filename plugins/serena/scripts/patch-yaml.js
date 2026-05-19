const fs = require('fs');
const path = require('path');

function patchYaml() {
    // 1. 获取当前项目目录下的配置文件路径
    const configFile = path.join(process.cwd(), '.serena', 'project.yml');

    // 条件 1：如果没有 project.yml 文件，直接安全退出
    if (!fs.existsSync(configFile)) {
        console.log('[-] 未检测到项目下的 .serena/project.yml，跳过。');
        return;
    }

    // 2. 读取文件内容
    let content = fs.readFileSync(configFile, 'utf8');
    const targetPath = '/usr/bin/clangd';

    // 条件 2：只有包含 "- cpp" 且没有被注释掉时，才继续处理
    const hasCppEnabled = content.split('\n').some(line => {
        const trimmed = line.trim();
        return trimmed.startsWith('- cpp') || trimmed === '-cpp';
    });

    if (!hasCppEnabled) {
        console.log('[-] 该项目未在 languages 中启用 cpp，跳过。');
        return;
    }

    // 🛑 条件 3（核心修改）：如果没有 ls_specific_settings 关键字，输出 log 并返回
    if (!content.includes('ls_specific_settings:')) {
        console.log('[-] 项目文件中不存在 ls_specific_settings 节点，不进行新添，直接跳过。');
        return;
    }

    // ---------------------------------------------------------
    // 走到这里，说明启用了 cpp 且有 ls_specific_settings，开始进行精准修改
    // ---------------------------------------------------------

    // 场景 A：ls_specific_settings 是原始的空对象 {}
    if (content.includes('ls_specific_settings: {}')) {
        const replacement = `ls_specific_settings:\n  cpp:\n    ls_path: "${targetPath}"`;
        content = content.replace('ls_specific_settings: {}', replacement);
        fs.writeFileSync(configFile, content, 'utf8');
        console.log('[+] 检测到原始空配置 {}，已成功将其修改为正确的 cpp.ls_path');
        return;
    }

    // 场景 B：已经有完整的 ls_specific_settings 段落，但里面完全没有配置过 cpp: 项
    if (!content.includes('cpp:')) {
        const replacement = `ls_specific_settings:\n  cpp:\n    ls_path: "${targetPath}"`;
        content = content.replace('ls_specific_settings:', replacement);
        fs.writeFileSync(configFile, content, 'utf8');
        console.log('[+] 已成功在现有的 ls_specific_settings 中追加 cpp.ls_path');
        return;
    }

    // 场景 C：已经有 cpp: 节点，但路径不对或缺少了 ls_path
    if (content.includes('cpp:') && !content.includes(targetPath)) {
        const lines = content.split('\n');
        let cppIndex = lines.findIndex(l => l.trim() === 'cpp:');

        if (cppIndex !== -1) {
            const nextLine = lines[cppIndex + 1];
            if (nextLine && nextLine.includes('ls_path:')) {
                // 精准覆写不正确的 ls_path 行
                lines[cppIndex + 1] = `    ls_path: "${targetPath}"`;
            } else {
                // 如果有 cpp: 却缺少 ls_path 这一行，在 cpp 下方插入
                lines.splice(cppIndex + 1, 0, `    ls_path: "${targetPath}"`);
            }
            fs.writeFileSync(configFile, lines.join('\n'), 'utf8');
            console.log('[+] 已成功将不正确的 cpp.ls_path 修正为正确路径');
        }
        return;
    }

    console.log('[-] 项目下的 cpp.ls_path 已经是最新正确配置，无需修改。');
}

try {
    patchYaml();
} catch (e) {
    console.error('[-] 自动处理项目 project.yml 失败:', e.message);
}
