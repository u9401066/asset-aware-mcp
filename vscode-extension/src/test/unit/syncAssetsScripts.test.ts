import * as assert from 'assert';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { spawnSync } from 'child_process';

const extensionRoot = path.resolve(__dirname, '../../..');
const repoRoot = path.resolve(extensionRoot, '..');
const syncScript = path.join(extensionRoot, 'scripts', 'sync-assistant-assets.mjs');
const checkScript = path.join(extensionRoot, 'scripts', 'check-sync-assets.mjs');

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

function writeText(filePath: string, content: string = 'ok\n'): void {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, content, { encoding: 'utf8' });
}

function createRequiredSources(root: string): void {
    writeText(path.join(root, 'AGENTS.md'));
    writeText(path.join(root, '.github', 'copilot-instructions.md'));
    writeText(path.join(root, '.github', 'agents', 'asset-aware-document.agent.md'));
    writeText(path.join(root, 'scripts', 'count_tools.ps1'));
    fs.mkdirSync(path.join(root, '.github', 'bylaws'), { recursive: true });
    writeText(path.join(root, '.github', 'bylaws', 'ddd-architecture.md'));

    for (const skillDir of claudeSkillDirs) {
        writeText(path.join(root, '.claude', 'skills', skillDir, 'SKILL.md'));
    }

    for (const skillDir of [
        path.join('.cline', 'skills', 'asset-aware-mcp-harness'),
        path.join('.cline', 'skills', 'llm-wiki-builder'),
        path.join('.codex', 'skills', 'asset-aware-mcp-harness'),
        path.join('.codex', 'skills', 'llm-wiki-builder'),
    ]) {
        writeText(path.join(root, skillDir, 'SKILL.md'));
    }

    for (const ruleFile of clineRuleFiles) {
        writeText(path.join(root, '.clinerules', ruleFile));
    }
}

describe('sync asset scripts', () => {
    let tempDir: string;

    beforeEach(() => {
        tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'asset-aware-sync-assets-'));
    });

    afterEach(() => {
        fs.rmSync(tempDir, { recursive: true, force: true });
    });

    it('uses explicit utf8 writes for normalized text assets', () => {
        const syncSource = fs.readFileSync(syncScript, 'utf8');
        const checkSource = fs.readFileSync(checkScript, 'utf8');

        assert.ok(syncSource.includes("encoding: 'utf8'"));
        assert.ok(syncSource.includes('U+FFFD'));
        assert.ok(checkSource.includes('U+FFFD'));
    });

    it('rejects text assets that already contain replacement characters', () => {
        const fakeRepoRoot = path.join(tempDir, 'repo');
        const fakeExtensionRoot = path.join(tempDir, 'extension');
        const fakeAssetRoot = path.join(tempDir, 'asset-root');
        createRequiredSources(fakeRepoRoot);
        writeText(path.join(fakeRepoRoot, 'AGENTS.md'), 'bad \uFFFD text\n');

        const result = spawnSync(process.execPath, [syncScript], {
            cwd: repoRoot,
            encoding: 'utf8',
            env: {
                ...process.env,
                ASSET_AWARE_REPO_ROOT: fakeRepoRoot,
                ASSET_AWARE_EXTENSION_ROOT: fakeExtensionRoot,
                ASSET_AWARE_ASSET_ROOT: fakeAssetRoot,
            },
        });

        assert.notStrictEqual(result.status, 0);
        assert.match(`${result.stdout}\n${result.stderr}`, /replacement character|U\+FFFD/i);
    });
});
