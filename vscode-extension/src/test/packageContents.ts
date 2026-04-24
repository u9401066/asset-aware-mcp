import { execFile } from 'child_process';
import * as path from 'path';
import { promisify } from 'util';

const execFileAsync = promisify(execFile);
const extensionRoot = path.resolve(__dirname, '../..');

const requiredFiles = [
    'package.json',
    'README.md',
    'LICENSE',
    'resources/icon.svg',
    'resources/icon.png',
    'resources/walkthrough/setup.md',
    'resources/walkthrough/configure.md',
    'resources/walkthrough/start.md',
    'out/extension.js',
];

const forbiddenPrefixes = [
    'out/test/',
    'src/',
    'node_modules/',
    '.github/',
    '.vscode/',
    '.vscode-test/',
];

const forbiddenFiles = [
    'tsconfig.json',
    'eslint.config.mjs',
    'package-lock.json',
];

async function listPackageFiles(): Promise<string[]> {
    const npxCommand = process.platform === 'win32' ? 'npx.cmd' : 'npx';
    const { stdout } = await execFileAsync(npxCommand, ['vsce', 'ls', '--no-dependencies'], {
        cwd: extensionRoot,
        env: process.env,
        maxBuffer: 1024 * 1024 * 10,
    });

    return stdout
        .split(/\r?\n/u)
        .map((line) => line.trim())
        .filter(Boolean);
}

function assertPackageContents(files: string[]): void {
    const fileSet = new Set(files);
    const missing = requiredFiles.filter((file) => !fileSet.has(file));
    if (missing.length > 0) {
        throw new Error(`VSIX package is missing required files: ${missing.join(', ')}`);
    }

    const forbidden = files.filter((file) =>
        forbiddenPrefixes.some((prefix) => file.startsWith(prefix)) ||
        forbiddenFiles.includes(file) ||
        file.endsWith('.vsix') ||
        file.endsWith('.map') ||
        file.endsWith('.ts')
    );

    if (forbidden.length > 0) {
        throw new Error(`VSIX package contains development-only files: ${forbidden.join(', ')}`);
    }
}

async function main(): Promise<void> {
    const files = await listPackageFiles();
    assertPackageContents(files);
    console.log(`VSIX package contents verified (${files.length} files).`);
}

main().catch((error) => {
    console.error('VSIX package contents check failed:', error);
    process.exit(1);
});
