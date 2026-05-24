#!/usr/bin/env node
/**
 * Serena Setup Script
 * 用法: node setup.js [--install|--update|--config]
 * 无参数时输出 JSON 状态供 LLM 解析
 */

const { spawn, execSync } = require('child_process');
const path = require('path');

const INSTALL_CMD = 'uv tool install --from git+https://github.com/oraios/serena serena-agent';
const UPDATE_CMD = 'uv tool upgrade serena-agent';

// 一次调用获取安装状态和版本
function getSerenaStatus() {
    try {
        const version = execSync('serena --version 2>/dev/null', { encoding: 'utf8' }).trim();
        return { installed: true, version };
    } catch {
        return { installed: false, version: null };
    }
}

function runCommand(cmd) {
    return new Promise((resolve, reject) => {
        console.log(`执行: ${cmd}`);
        const child = spawn('sh', ['-c', cmd], { stdio: 'inherit' });
        child.on('close', (code) => {
            code === 0 ? resolve() : reject(new Error(`退出码: ${code}`));
        });
        child.on('error', reject);
    });
}

function runPatchYaml() {
    const patchYamlPath = path.join(path.dirname(__filename), 'patch-yaml.js');
    console.log('\n配置语言服务器...');
    try {
        execSync(`node "${patchYamlPath}"`, { stdio: 'inherit' });
        console.log('语言服务器配置完成。');
    } catch {
        console.log('语言服务器配置跳过。');
    }
}

function outputStatus() {
    console.log(JSON.stringify(getSerenaStatus(), null, 2));
}

async function doAction(action, cmd) {
    console.log(`正在${action} Serena...`);
    try {
        await runCommand(cmd);
        console.log(`\nSerena ${action}成功！`);
    } catch (e) {
        console.error(`\n${action}失败: ${e.message}`);
        process.exit(1);
    }
}

function doConfig() {
    runPatchYaml();
}

async function main() {
    const args = process.argv.slice(2);

    if (args.length === 0) {
        outputStatus();
    } else if (args.includes('--install')) {
        await doAction('安装', INSTALL_CMD);
    } else if (args.includes('--update')) {
        await doAction('更新', UPDATE_CMD);
    } else if (args.includes('--config')) {
        doConfig();
    } else {
        console.error('用法: node setup.js [--install|--update|--config]');
        process.exit(1);
    }
}

main().catch((e) => {
    console.error(`Setup 失败: ${e.message}`);
    process.exit(1);
});
