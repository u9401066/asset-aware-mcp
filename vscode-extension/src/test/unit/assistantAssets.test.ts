import * as assert from 'assert';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import * as vscode from 'vscode';
import { installAssistantAssets } from '../../assistantAssets';
import { __resetConfiguration } from './mock-vscode';

describe('assistantAssets', () => {
    let tempDir: string;
    let extensionRoot: string;
    let workspaceRoot: string;

    beforeEach(() => {
        tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'asset-aware-assets-'));
        extensionRoot = path.join(tempDir, 'extension');
        workspaceRoot = path.join(tempDir, 'workspace');
        fs.mkdirSync(workspaceRoot, { recursive: true });
        (vscode.workspace as any).workspaceFolders = [{ uri: { fsPath: workspaceRoot } }];
        __resetConfiguration();
    });

    afterEach(() => {
        fs.rmSync(tempDir, { recursive: true, force: true });
        (vscode.workspace as any).workspaceFolders = undefined;
        __resetConfiguration();
    });

    function makeContext(): any {
        return {
            extensionPath: extensionRoot,
            extension: { packageJSON: { version: '0.6.18' } },
        };
    }

    function writeBundledAsset(relativePath: string, content: string): void {
        const target = path.join(extensionRoot, 'resources', 'repo-assets', 'asset-aware', relativePath);
        fs.mkdirSync(path.dirname(target), { recursive: true });
        fs.writeFileSync(target, content, 'utf-8');
    }

    it('updates previously managed assets when the workspace copy is unchanged', async () => {
        writeBundledAsset(path.join('.cline', 'skills', 'asset-aware-mcp-harness', 'SKILL.md'), 'version one\n');

        await installAssistantAssets(makeContext());
        writeBundledAsset(path.join('.cline', 'skills', 'asset-aware-mcp-harness', 'SKILL.md'), 'version two\n');
        const summary = await installAssistantAssets(makeContext());

        const installed = fs.readFileSync(
            path.join(workspaceRoot, '.cline', 'skills', 'asset-aware-mcp-harness', 'SKILL.md'),
            'utf-8',
        );
        assert.strictEqual(installed, 'version two\n');
        assert.strictEqual(summary?.updated, 1);
    });

    it('preserves edited workspace assets instead of overwriting user changes', async () => {
        const skillPath = path.join('.cline', 'skills', 'asset-aware-mcp-harness', 'SKILL.md');
        const workspaceSkillPath = path.join(workspaceRoot, skillPath);
        writeBundledAsset(skillPath, 'managed version\n');

        await installAssistantAssets(makeContext());
        fs.writeFileSync(workspaceSkillPath, 'user customization\n', 'utf-8');
        writeBundledAsset(skillPath, 'new managed version\n');
        const summary = await installAssistantAssets(makeContext());

        assert.strictEqual(fs.readFileSync(workspaceSkillPath, 'utf-8'), 'user customization\n');
        assert.strictEqual(summary?.preserved, 1);
    });

    it('migrates legacy detector-managed AGENTS.md without a manifest hash', async () => {
        writeBundledAsset(
            'AGENTS.md',
            '# Asset-Aware MCP Codex Harness\ncitation-ready document workflows\nversion two\n',
        );
        fs.writeFileSync(
            path.join(workspaceRoot, 'AGENTS.md'),
            '# Asset-Aware MCP Codex Harness\ncitation-ready document workflows\nversion one\n',
            'utf-8',
        );

        const summary = await installAssistantAssets(makeContext());

        assert.strictEqual(
            fs.readFileSync(path.join(workspaceRoot, 'AGENTS.md'), 'utf-8'),
            '# Asset-Aware MCP Codex Harness\ncitation-ready document workflows\nversion two\n',
        );
        assert.strictEqual(summary?.updated, 1);
    });
});
