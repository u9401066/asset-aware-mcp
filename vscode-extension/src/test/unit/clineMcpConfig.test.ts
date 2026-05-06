import * as assert from 'assert';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import * as vscode from 'vscode';
import { installClineMcpServer, isClineInstalled, removeClineMcpServer } from '../../clineMcpConfig';
import { __resetConfiguration, __setExtensionInstalled } from './mock-vscode';

describe('clineMcpConfig', () => {
    let tempDir: string;
    let context: any;
    let settingsPath: string;

    beforeEach(() => {
        tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'asset-aware-cline-'));
        context = {
            globalStorageUri: {
                fsPath: path.join(tempDir, 'globalStorage', 'u9401066.asset-aware-mcp'),
            },
            extension: { packageJSON: { version: '0.6.18' } },
        };
        settingsPath = path.join(tempDir, 'globalStorage', 'saoudrizwan.claude-dev', 'settings', 'cline_mcp_settings.json');
        (vscode.workspace as any).workspaceFolders = [{ uri: { fsPath: tempDir } }];
        __resetConfiguration();
    });

    afterEach(() => {
        fs.rmSync(tempDir, { recursive: true, force: true });
        (vscode.workspace as any).workspaceFolders = undefined;
        __resetConfiguration();
    });

    function readSettings(): any {
        return JSON.parse(fs.readFileSync(settingsPath, 'utf-8'));
    }

    it('detects Cline by extension install or global storage', () => {
        assert.strictEqual(isClineInstalled(context), false);
        __setExtensionInstalled('saoudrizwan.claude-dev', true);
        assert.strictEqual(isClineInstalled(context), true);
        __setExtensionInstalled('saoudrizwan.claude-dev', false);
        fs.mkdirSync(path.dirname(settingsPath), { recursive: true });
        assert.strictEqual(isClineInstalled(context), true);
    });

    it('creates Cline MCP settings without touching unrelated servers', () => {
        fs.mkdirSync(path.dirname(settingsPath), { recursive: true });
        fs.writeFileSync(settingsPath, JSON.stringify({
            mcpServers: {
                other: { command: 'node', args: ['server.js'] },
            },
        }, null, 2));

        const updated = installClineMcpServer(context, '/usr/bin/uv');

        assert.strictEqual(updated, true);
        const settings = readSettings();
        assert.ok(settings.mcpServers.other);
        assert.ok(settings.mcpServers['asset-aware-mcp']);
        assert.ok(settings.mcpRules.assetAwareDocs.servers.includes('asset-aware-mcp'));
    });

    it('preserves Cline-local disabled and alwaysAllow metadata on managed entries', () => {
        fs.mkdirSync(path.dirname(settingsPath), { recursive: true });
        fs.writeFileSync(settingsPath, JSON.stringify({
            mcpServers: {
                'asset-aware-mcp': {
                    command: '/old/uv',
                    args: ['tool', 'run', 'asset-aware-mcp'],
                    disabled: true,
                    alwaysAllow: ['ingest_pdf'],
                },
            },
        }, null, 2));

        const updated = installClineMcpServer(context, '/usr/bin/uv');

        assert.strictEqual(updated, true);
        const entry = readSettings().mcpServers['asset-aware-mcp'];
        assert.strictEqual(entry.command, '/usr/bin/uv');
        assert.strictEqual(entry.disabled, true);
        assert.deepStrictEqual(entry.alwaysAllow, ['ingest_pdf']);
    });

    it('does not auto-overwrite a managed Cline DATA_DIR from another workspace', () => {
        const otherWorkspace = fs.mkdtempSync(path.join(os.tmpdir(), 'asset-aware-other-workspace-'));
        fs.mkdirSync(path.dirname(settingsPath), { recursive: true });
        fs.writeFileSync(settingsPath, JSON.stringify({
            mcpServers: {
                'asset-aware-mcp': {
                    command: '/old/uv',
                    args: ['tool', 'run', 'asset-aware-mcp'],
                    env: {
                        DATA_DIR: path.join(otherWorkspace, 'data'),
                    },
                    alwaysAllow: ['ingest_pdf'],
                },
            },
        }, null, 2));

        try {
            const updated = installClineMcpServer(context, '/usr/bin/uv');

            assert.strictEqual(updated, false);
            const entry = readSettings().mcpServers['asset-aware-mcp'];
            assert.strictEqual(entry.command, '/old/uv');
            assert.strictEqual(entry.env.DATA_DIR, path.join(otherWorkspace, 'data'));
            assert.deepStrictEqual(entry.alwaysAllow, ['ingest_pdf']);
        } finally {
            fs.rmSync(otherWorkspace, { recursive: true, force: true });
        }
    });

    it('allows manual Cline workspace takeover for a managed cross-workspace DATA_DIR', () => {
        const otherWorkspace = fs.mkdtempSync(path.join(os.tmpdir(), 'asset-aware-other-workspace-'));
        fs.mkdirSync(path.dirname(settingsPath), { recursive: true });
        fs.writeFileSync(settingsPath, JSON.stringify({
            mcpServers: {
                'asset-aware-mcp': {
                    command: '/old/uv',
                    args: ['tool', 'run', 'asset-aware-mcp'],
                    env: {
                        DATA_DIR: path.join(otherWorkspace, 'data'),
                    },
                    alwaysAllow: ['ingest_pdf'],
                },
            },
        }, null, 2));

        try {
            const updated = installClineMcpServer(context, '/usr/bin/uv', false, { forceWorkspace: true });

            assert.strictEqual(updated, true);
            const entry = readSettings().mcpServers['asset-aware-mcp'];
            assert.strictEqual(entry.command, '/usr/bin/uv');
            assert.strictEqual(entry.env.DATA_DIR, path.join(tempDir, 'data'));
            assert.deepStrictEqual(entry.alwaysAllow, ['ingest_pdf']);
        } finally {
            fs.rmSync(otherWorkspace, { recursive: true, force: true });
        }
    });

    it('includes --upgrade when activation detected a server version change', () => {
        fs.mkdirSync(path.dirname(settingsPath), { recursive: true });

        const updated = installClineMcpServer(context, '/usr/bin/uv', true);

        assert.strictEqual(updated, true);
        const entry = readSettings().mcpServers['asset-aware-mcp'];
        assert.ok(entry.args.includes('--upgrade'));
    });

    it('does not overwrite a custom same-key server', () => {
        fs.mkdirSync(path.dirname(settingsPath), { recursive: true });
        fs.writeFileSync(settingsPath, JSON.stringify({
            mcpServers: {
                'asset-aware-mcp': { command: 'custom', args: ['server'] },
            },
        }, null, 2));

        const updated = installClineMcpServer(context, '/usr/bin/uv');

        assert.strictEqual(updated, false);
        assert.strictEqual(readSettings().mcpServers['asset-aware-mcp'].command, 'custom');
    });

    it('skips malformed JSON instead of replacing it with a blank config', () => {
        fs.mkdirSync(path.dirname(settingsPath), { recursive: true });
        fs.writeFileSync(settingsPath, '{ "mcpServers": {');

        const updated = installClineMcpServer(context, '/usr/bin/uv');

        assert.strictEqual(updated, false);
        assert.strictEqual(fs.readFileSync(settingsPath, 'utf-8'), '{ "mcpServers": {');
        assert.ok(fs.readdirSync(path.dirname(settingsPath)).some((name) => name.includes('.invalid.')));
    });

    it('removes only the managed server', () => {
        fs.mkdirSync(path.dirname(settingsPath), { recursive: true });
        installClineMcpServer(context, '/usr/bin/uv');
        const settings = readSettings();
        settings.mcpServers.other = { command: 'node', args: ['server.js'] };
        fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2));

        const removed = removeClineMcpServer(context);

        assert.strictEqual(removed, true);
        const after = readSettings();
        assert.strictEqual(after.mcpServers['asset-aware-mcp'], undefined);
        assert.ok(after.mcpServers.other);
    });
});
