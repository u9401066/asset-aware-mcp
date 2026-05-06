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
    'resources/repo-assets/asset-aware/.cline/skills/llm-wiki-builder/SKILL.md',
    'resources/repo-assets/asset-aware/.codex/skills/asset-aware-mcp-harness/SKILL.md',
    'resources/repo-assets/asset-aware/.codex/skills/llm-wiki-builder/SKILL.md',
    'resources/repo-assets/asset-aware/.clinerules/35-foam-llm-wiki.md',
    'resources/repo-assets/asset-aware/.clinerules/workflows/full-check.md',
    'resources/repo-assets/asset-aware/.clinerules/workflows/llm-wiki-build.md',
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

const forbiddenAssetFragments = [
    'resources/repo-assets/asset-aware/.github/hooks/',
    'resources/repo-assets/asset-aware/.github/zotero-research-workflow.md',
    'resources/repo-assets/asset-aware/.github/agents/research.agent.md',
    'resources/repo-assets/asset-aware/scripts/hooks/copilot/',
    'resources/repo-assets/asset-aware/.claude/skills/pubmed-',
    'resources/repo-assets/asset-aware/.claude/skills/zotero-keeper-harness/',
    'resources/repo-assets/asset-aware/.claude/skills/pipeline-persistence/',
    'resources/repo-assets/asset-aware/.cline/skills/pubmed-search-mcp-harness/',
    'resources/repo-assets/asset-aware/.cline/skills/zotero-keeper-harness/',
    'resources/repo-assets/asset-aware/.codex/skills/pubmed-search-mcp-harness/',
    'resources/repo-assets/asset-aware/.codex/skills/zotero-keeper-harness/',
    'resources/repo-assets/asset-aware/.clinerules/00-zotero-project.md',
    'resources/repo-assets/asset-aware/.clinerules/10-zotero-python.md',
    'resources/repo-assets/asset-aware/.clinerules/20-zotero-vscode-extension.md',
    'resources/repo-assets/asset-aware/.clinerules/30-zotero-research-workflow.md',
    'resources/repo-assets/asset-aware/.clinerules/40-zotero-release.md',
    'resources/repo-assets/asset-aware/.clinerules/50-pubmed-project.md',
    'resources/repo-assets/asset-aware/.clinerules/60-pubmed-python.md',
    'resources/repo-assets/asset-aware/.clinerules/70-pubmed-mcp-tools.md',
    'resources/repo-assets/asset-aware/.clinerules/80-pubmed-release.md',
    'resources/repo-assets/asset-aware/.clinerules/workflows/pubmed-',
    'resources/repo-assets/asset-aware/.clinerules/workflows/zotero-',
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

    const forbiddenAssets = files.filter((file) =>
        forbiddenAssetFragments.some((fragment) => file.includes(fragment))
    );
    if (forbiddenAssets.length > 0) {
        throw new Error(`VSIX package contains non Asset-Aware harness assets: ${forbiddenAssets.join(', ')}`);
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
