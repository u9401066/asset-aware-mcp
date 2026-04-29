import * as assert from 'assert';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import * as vscode from 'vscode';
import { installCopilotMcpConfig } from '../../copilotMcpConfig';
import { __resetConfiguration } from './mock-vscode';

describe('copilotMcpConfig', () => {
    let tempDir: string;

    beforeEach(() => {
        tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'asset-aware-copilot-'));
        (vscode.workspace as any).workspaceFolders = [{ uri: { fsPath: tempDir } }];
        __resetConfiguration();
    });

    afterEach(() => {
        fs.rmSync(tempDir, { recursive: true, force: true });
        (vscode.workspace as any).workspaceFolders = undefined;
        __resetConfiguration();
    });

    function makeContext(): any {
        return {
            globalStorageUri: { fsPath: path.join(tempDir, 'globalStorage', 'u9401066.asset-aware-mcp') },
            extension: { packageJSON: { version: '0.6.14' } },
        };
    }

    function readMcpJson(): any {
        return JSON.parse(fs.readFileSync(path.join(tempDir, '.vscode', 'mcp.json'), 'utf-8'));
    }

    it('creates workspace .vscode/mcp.json with Asset-Aware server', () => {
        const updated = installCopilotMcpConfig(makeContext(), '/usr/bin/uv');

        assert.strictEqual(updated, true);
        const settings = readMcpJson();
        assert.ok(settings.servers['asset-aware-mcp']);
        assert.strictEqual(settings.servers['asset-aware-mcp'].type, 'stdio');
        assert.strictEqual(settings.servers['asset-aware-mcp'].command, '/usr/bin/uv');
        assert.ok(settings.servers['asset-aware-mcp'].args.includes('asset-aware-mcp'));
        assert.ok(settings.servers['asset-aware-mcp'].env.DATA_DIR.startsWith(tempDir));
    });

    it('preserves unrelated servers and is idempotent', () => {
        fs.mkdirSync(path.join(tempDir, '.vscode'), { recursive: true });
        fs.writeFileSync(path.join(tempDir, '.vscode', 'mcp.json'), JSON.stringify({
            servers: {
                other: { type: 'stdio', command: 'node', args: ['server.js'] },
            },
        }, null, 2));

        assert.strictEqual(installCopilotMcpConfig(makeContext(), '/usr/bin/uv'), true);
        assert.strictEqual(installCopilotMcpConfig(makeContext(), '/usr/bin/uv'), false);

        const settings = readMcpJson();
        assert.ok(settings.servers.other);
        assert.ok(settings.servers['asset-aware-mcp']);
    });

    it('does not overwrite a custom server using the same key', () => {
        fs.mkdirSync(path.join(tempDir, '.vscode'), { recursive: true });
        fs.writeFileSync(path.join(tempDir, '.vscode', 'mcp.json'), JSON.stringify({
            servers: {
                'asset-aware-mcp': { type: 'stdio', command: 'custom', args: ['server'] },
            },
        }, null, 2));

        const updated = installCopilotMcpConfig(makeContext(), '/usr/bin/uv');

        assert.strictEqual(updated, false);
        const settings = readMcpJson();
        assert.strictEqual(settings.servers['asset-aware-mcp'].command, 'custom');
    });
});
