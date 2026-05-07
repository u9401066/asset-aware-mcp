import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const extensionRoot = process.env.ASSET_AWARE_EXTENSION_ROOT
    ? path.resolve(process.env.ASSET_AWARE_EXTENSION_ROOT)
    : path.resolve(scriptDir, '..');
const repoRoot = process.env.ASSET_AWARE_REPO_ROOT
    ? path.resolve(process.env.ASSET_AWARE_REPO_ROOT)
    : path.resolve(extensionRoot, '..');
const assetRoot = process.env.ASSET_AWARE_ASSET_ROOT
    ? path.resolve(process.env.ASSET_AWARE_ASSET_ROOT)
    : path.join(extensionRoot, 'resources', 'repo-assets', 'asset-aware');

const clineRuleFiles = [
    '00-project.md',
    '10-python.md',
    '20-vscode-extension.md',
    '30-citation-ready.md',
    '35-foam-llm-wiki.md',
    '40-release.md',
    'workflows/full-check.md',
    'workflows/llm-wiki-build.md',
    'workflows/mcp-setup.md',
    'workflows/release-publish.md',
    'workflows/skills-audit.md',
];

const claudeSkillDirs = [
    'changelog-updater',
    'code-refactor',
    'code-reviewer',
    'ddd-architect',
    'git-doc-updater',
    'git-precommit',
    'memory-checkpoint',
    'memory-updater',
    'pdf-asset-extractor',
    'project-init',
    'readme-i18n',
    'readme-updater',
    'roadmap-updater',
    'test-generator',
];

const mappings = [
    {
        source: path.join(repoRoot, 'AGENTS.md'),
        target: path.join(assetRoot, 'AGENTS.md'),
    },
    {
        source: path.join(repoRoot, '.github', 'copilot-instructions.md'),
        target: path.join(assetRoot, '.github', 'copilot-instructions.md'),
    },
    {
        source: path.join(repoRoot, '.github', 'agents', 'asset-aware-document.agent.md'),
        target: path.join(assetRoot, '.github', 'agents', 'asset-aware-document.agent.md'),
    },
    {
        source: path.join(repoRoot, 'scripts', 'count_tools.ps1'),
        target: path.join(assetRoot, 'scripts', 'count_tools.ps1'),
    },
    {
        source: path.join(repoRoot, '.github', 'bylaws'),
        target: path.join(assetRoot, '.github', 'bylaws'),
    },
    ...claudeSkillDirs.map((skillDir) => ({
        source: path.join(repoRoot, '.claude', 'skills', skillDir),
        target: path.join(assetRoot, '.claude', 'skills', skillDir),
    })),
    {
        source: path.join(repoRoot, '.cline', 'skills', 'asset-aware-mcp-harness'),
        target: path.join(assetRoot, '.cline', 'skills', 'asset-aware-mcp-harness'),
    },
    {
        source: path.join(repoRoot, '.cline', 'skills', 'llm-wiki-builder'),
        target: path.join(assetRoot, '.cline', 'skills', 'llm-wiki-builder'),
    },
    {
        source: path.join(repoRoot, '.codex', 'skills', 'asset-aware-mcp-harness'),
        target: path.join(assetRoot, '.codex', 'skills', 'asset-aware-mcp-harness'),
    },
    {
        source: path.join(repoRoot, '.codex', 'skills', 'llm-wiki-builder'),
        target: path.join(assetRoot, '.codex', 'skills', 'llm-wiki-builder'),
    },
    ...clineRuleFiles.map((ruleFile) => ({
        source: path.join(repoRoot, '.clinerules', ruleFile),
        target: path.join(assetRoot, '.clinerules', ruleFile),
    })),
];

function ensureParentDirectory(targetPath) {
    fs.mkdirSync(path.dirname(targetPath), { recursive: true });
}

function normalizeTextAsset(targetPath) {
    const ext = path.extname(targetPath).toLowerCase();
    const raw = fs.readFileSync(targetPath);
    let content = raw[0] === 0xef && raw[1] === 0xbb && raw[2] === 0xbf
        ? raw.subarray(3)
        : raw;

    if (['.md', '.json', '.toml', '.sh', '.ps1'].includes(ext)) {
        content = Buffer.from(content.toString('utf8').replace(/\r\n/g, '\n'), 'utf8');
    }

    fs.writeFileSync(targetPath, content);
}

function copyRecursive(sourcePath, targetPath) {
    const stat = fs.statSync(sourcePath);
    if (stat.isDirectory()) {
        fs.mkdirSync(targetPath, { recursive: true });
        for (const entry of fs.readdirSync(sourcePath, { withFileTypes: true })) {
            copyRecursive(path.join(sourcePath, entry.name), path.join(targetPath, entry.name));
        }
        return;
    }

    ensureParentDirectory(targetPath);
    fs.copyFileSync(sourcePath, targetPath);
    normalizeTextAsset(targetPath);
}

function main() {
    fs.rmSync(assetRoot, { recursive: true, force: true });

    for (const mapping of mappings) {
        if (!fs.existsSync(mapping.source)) {
            throw new Error(`Missing assistant asset source: ${mapping.source}`);
        }
        copyRecursive(mapping.source, mapping.target);
        console.log(`Synced ${path.relative(repoRoot, mapping.source)} -> ${path.relative(extensionRoot, mapping.target)}`);
    }
}

main();
