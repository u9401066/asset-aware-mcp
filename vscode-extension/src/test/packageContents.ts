import * as path from 'path';
import { listFiles, PackageManager } from '@vscode/vsce';

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
    'resources/repo-assets/asset-aware/AGENTS.md',
    'resources/repo-assets/asset-aware/.github/copilot-instructions.md',
    'resources/repo-assets/asset-aware/.github/agents/asset-aware-document.agent.md',
    'resources/repo-assets/asset-aware/.github/bylaws/ddd-architecture.md',
    'resources/repo-assets/asset-aware/.claude/skills/pdf-asset-extractor/SKILL.md',
    'resources/repo-assets/asset-aware/.cline/skills/asset-aware-mcp-harness/SKILL.md',
    'resources/repo-assets/asset-aware/.codex/skills/asset-aware-mcp-harness/SKILL.md',
    'resources/repo-assets/asset-aware/.clinerules/workflows/full-check.md',
    'out/extension.js',
];

const forbiddenPrefixes = [
    'out/test/',
    'src/',
    'node_modules/',
    'scripts/',
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
    return await listFiles({
        cwd: extensionRoot,
        packageManager: PackageManager.None,
    });
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
