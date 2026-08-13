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
        (vscode.workspace as any).isTrusted = true;
        __resetConfiguration();
    });

    afterEach(() => {
        fs.rmSync(tempDir, { recursive: true, force: true });
        (vscode.workspace as any).workspaceFolders = undefined;
        (vscode.workspace as any).isTrusted = true;
        __resetConfiguration();
    });

    function makeContext(): any {
        return {
            globalStorageUri: { fsPath: path.join(tempDir, 'globalStorage', 'u9401066.asset-aware-mcp') },
            extension: { packageJSON: { version: '0.6.19' } },
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
        assert.strictEqual(settings.servers['asset-aware-mcp'].env.ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS, '12000');
        assert.strictEqual(settings.servers['asset-aware-mcp'].env.ASSET_AWARE_MCP_IMAGE_RESPONSE_CHARS, '750000');
        assert.strictEqual(settings.servers['asset-aware-mcp'].env.ASSET_AWARE_TABLE_STARTUP_LOAD_MAX_BYTES, '20971520');
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

    it('includes --upgrade when activation detected a server version change', () => {
        const updated = installCopilotMcpConfig(makeContext(), '/usr/bin/uv', true);

        assert.strictEqual(updated, true);
        const settings = readMcpJson();
        assert.ok(settings.servers['asset-aware-mcp'].args.includes('--upgrade'));
    });

    it('preserves custom env metadata while refreshing managed launch env', () => {
        fs.mkdirSync(path.join(tempDir, '.vscode'), { recursive: true });
        fs.writeFileSync(path.join(tempDir, '.env'), 'DATA_DIR=next-data\nOLLAMA_MODEL=from-env\n');
        fs.writeFileSync(path.join(tempDir, '.vscode', 'mcp.json'), JSON.stringify({
            servers: {
                'asset-aware-mcp': {
                    type: 'stdio',
                    command: '/old/uv',
                    args: ['tool', 'run', 'asset-aware-mcp'],
                    env: {
                        HTTP_PROXY: 'http://proxy.local:8080',
                        SSL_CERT_FILE: '/etc/ssl/corp.pem',
                        ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS: '0',
                        ASSET_AWARE_MCP_IMAGE_RESPONSE_CHARS: '999999999',
                    },
                },
            },
        }, null, 2));

        const updated = installCopilotMcpConfig(makeContext(), '/usr/bin/uv');

        assert.strictEqual(updated, true);
        const entry = readMcpJson().servers['asset-aware-mcp'];
        assert.strictEqual(entry.env.HTTP_PROXY, 'http://proxy.local:8080');
        assert.strictEqual(entry.env.SSL_CERT_FILE, '/etc/ssl/corp.pem');
        assert.strictEqual(entry.env.OLLAMA_MODEL, 'from-env');
        assert.strictEqual(entry.env.DATA_DIR, path.join(tempDir, 'next-data'));
        assert.strictEqual(entry.env.ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS, '12000');
        assert.strictEqual(entry.env.ASSET_AWARE_MCP_IMAGE_RESPONSE_CHARS, '750000');
        assert.strictEqual(entry.env.ASSET_AWARE_TABLE_STARTUP_LOAD_MAX_BYTES, '20971520');
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

    it('skips malformed JSON instead of replacing it with a blank config', () => {
        const configPath = path.join(tempDir, '.vscode', 'mcp.json');
        fs.mkdirSync(path.dirname(configPath), { recursive: true });
        fs.writeFileSync(configPath, '{ "servers": {');

        const updated = installCopilotMcpConfig(makeContext(), '/usr/bin/uv');

        assert.strictEqual(updated, false);
        assert.strictEqual(fs.readFileSync(configPath, 'utf-8'), '{ "servers": {');
        assert.ok(fs.readdirSync(path.dirname(configPath)).some((name) => name.includes('.invalid.')));
    });

    for (const [label, invalidSettings] of [
        ['an array root', []],
        ['an array servers value', { servers: [] }],
        ['a null servers value', { servers: null }],
        ['a non-object nested server', { servers: { broken: [] } }],
        ['invalid nested server args', { servers: { broken: { command: 'node', args: 'server.js' } } }],
        ['invalid nested server env', { servers: { broken: { command: 'node', env: { TOKEN: 42 } } } }],
    ] as const) {
        it(`fails closed for ${label}`, () => {
            const configPath = path.join(tempDir, '.vscode', 'mcp.json');
            fs.mkdirSync(path.dirname(configPath), { recursive: true });
            const original = JSON.stringify(invalidSettings, null, 2) + '\n';
            fs.writeFileSync(configPath, original);

            const updated = installCopilotMcpConfig(makeContext(), '/usr/bin/uv');

            assert.strictEqual(updated, false);
            assert.strictEqual(fs.readFileSync(configPath, 'utf-8'), original);
            assert.ok(fs.readdirSync(path.dirname(configPath)).some((name) => name.includes('.invalid.')));
        });
    }

    it('preserves a valid custom remote server and its unknown metadata', () => {
        const configPath = path.join(tempDir, '.vscode', 'mcp.json');
        fs.mkdirSync(path.dirname(configPath), { recursive: true });
        const custom = {
            type: 'http',
            url: 'https://example.test/mcp',
            headers: { 'X-Custom': '${input:custom-header}' },
            vendorMetadata: { owner: 'user' },
        };
        fs.writeFileSync(configPath, JSON.stringify({ servers: { custom } }, null, 2));

        assert.strictEqual(installCopilotMcpConfig(makeContext(), '/usr/bin/uv'), true);

        const settings = readMcpJson();
        assert.deepStrictEqual(settings.servers.custom, custom);
        assert.ok(settings.servers['asset-aware-mcp']);
    });

    it('does not write workspace MCP config before the workspace is trusted', () => {
        (vscode.workspace as any).isTrusted = false;

        assert.strictEqual(installCopilotMcpConfig(makeContext(), '/usr/bin/uv'), false);
        assert.strictEqual(fs.existsSync(path.join(tempDir, '.vscode', 'mcp.json')), false);
    });
});
