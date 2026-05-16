import * as assert from 'assert';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import * as vscode from 'vscode';
import {
    getCodexConfigPath,
    getCodexHome,
    installCodexMcpServer,
    isCodexAvailable,
    removeCodexMcpServer,
    __test__,
} from '../../codexMcpConfig';
import { __resetConfiguration } from './mock-vscode';

describe('codexMcpConfig', () => {
    let tempDir: string;
    let originalCodexHome: string | undefined;
    let context: any;

    beforeEach(() => {
        tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'asset-aware-codex-'));
        originalCodexHome = process.env.CODEX_HOME;
        process.env.CODEX_HOME = tempDir;
        context = {
            globalStorageUri: { fsPath: path.join(tempDir, 'globalStorage', 'u9401066.asset-aware-mcp') },
            extension: { packageJSON: { version: '0.6.19' } },
        };
        (vscode.workspace as any).workspaceFolders = [{ uri: { fsPath: tempDir } }];
        __resetConfiguration();
    });

    afterEach(() => {
        if (originalCodexHome === undefined) {
            delete process.env.CODEX_HOME;
        } else {
            process.env.CODEX_HOME = originalCodexHome;
        }
        fs.rmSync(tempDir, { recursive: true, force: true });
        (vscode.workspace as any).workspaceFolders = undefined;
        __resetConfiguration();
    });

    it('honors CODEX_HOME and detects availability', () => {
        assert.strictEqual(getCodexHome(), tempDir);
        assert.strictEqual(getCodexConfigPath(), path.join(tempDir, 'config.toml'));
        assert.strictEqual(isCodexAvailable(), true);
    });

    it('escapes TOML strings safely', () => {
        assert.strictEqual(__test__.escapeTomlString('C:\\Users\\A "B"'), 'C:\\\\Users\\\\A \\"B\\"');
    });

    it('creates config.toml while preserving unrelated user content', () => {
        fs.writeFileSync(path.join(tempDir, 'config.toml'), [
            '# user comment',
            '',
            '[mcp_servers.other]',
            'command = "node"',
            'args = ["server.js"]',
            '',
        ].join('\n'));

        const updated = installCodexMcpServer(context, '/usr/bin/uv');

        assert.strictEqual(updated, true);
        const content = fs.readFileSync(path.join(tempDir, 'config.toml'), 'utf-8');
        assert.ok(content.includes('# user comment'));
        assert.ok(content.includes('[mcp_servers.other]'));
        assert.ok(content.includes('[mcp_servers.asset-aware-mcp]'));
        assert.ok(content.includes('Managed by asset-aware-mcp VS Code extension'));
        assert.ok(content.includes('ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS = "12000"'));
        assert.ok(content.includes('ASSET_AWARE_MCP_IMAGE_RESPONSE_CHARS = "750000"'));
        assert.ok(content.includes('ASSET_AWARE_TABLE_STARTUP_LOAD_MAX_BYTES = "20971520"'));
    });

    it('updates managed blocks without duplicating them', () => {
        assert.strictEqual(installCodexMcpServer(context, '/old/uv'), true);
        assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv'), true);

        const content = fs.readFileSync(path.join(tempDir, 'config.toml'), 'utf-8');
        assert.ok(!content.includes('/old/uv'));
        assert.strictEqual((content.match(/\[mcp_servers\.asset-aware-mcp\]/g) ?? []).length, 1);
        assert.strictEqual((content.match(/\[mcp_servers\.asset-aware-mcp\.env\]/g) ?? []).length, 1);
    });

    it('includes --upgrade when activation detected a server version change', () => {
        assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv', true), true);

        const content = fs.readFileSync(path.join(tempDir, 'config.toml'), 'utf-8');
        assert.ok(content.includes('"--upgrade"'));
    });

    it('preserves custom managed env metadata while refreshing launch env', () => {
        fs.writeFileSync(path.join(tempDir, '.env'), 'DATA_DIR=next-data\nOLLAMA_MODEL=from-env\n');
        fs.writeFileSync(path.join(tempDir, 'config.toml'), [
            '# user comment',
            '',
            '# Managed by asset-aware-mcp VS Code extension. Remove this block to opt out.',
            '[mcp_servers.asset-aware-mcp]',
            'command = "/old/uv"',
            'args = ["tool", "run", "asset-aware-mcp"]',
            '',
            '[mcp_servers.asset-aware-mcp.env]',
            'HTTP_PROXY = "http://proxy.local:8080"',
            'SSL_CERT_FILE = "C:\\\\certs\\\\corp.pem"',
            'ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS = "0"',
            'ASSET_AWARE_MCP_IMAGE_RESPONSE_CHARS = "999999999"',
            '',
        ].join('\n'));

        const updated = installCodexMcpServer(context, '/usr/bin/uv');

        assert.strictEqual(updated, true);
        const content = fs.readFileSync(path.join(tempDir, 'config.toml'), 'utf-8');
        assert.ok(content.includes('# user comment'));
        assert.ok(content.includes('HTTP_PROXY = "http://proxy.local:8080"'));
        assert.ok(content.includes('SSL_CERT_FILE = "C:\\\\certs\\\\corp.pem"'));
        assert.ok(content.includes('OLLAMA_MODEL = "from-env"'));
        assert.ok(content.includes(`DATA_DIR = "${__test__.escapeTomlString(path.join(tempDir, 'next-data'))}"`));
        assert.ok(content.includes('ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS = "12000"'));
        assert.ok(content.includes('ASSET_AWARE_MCP_IMAGE_RESPONSE_CHARS = "750000"'));
        assert.ok(content.includes('ASSET_AWARE_TABLE_STARTUP_LOAD_MAX_BYTES = "20971520"'));
    });

    it('does not overwrite a custom same-key block', () => {
        fs.writeFileSync(path.join(tempDir, 'config.toml'), [
            '[mcp_servers.asset-aware-mcp]',
            'command = "custom"',
            'args = ["server"]',
            '',
        ].join('\n'));

        const updated = installCodexMcpServer(context, '/usr/bin/uv');

        assert.strictEqual(updated, false);
        const content = fs.readFileSync(path.join(tempDir, 'config.toml'), 'utf-8');
        assert.ok(content.includes('command = "custom"'));
    });

    it('skips suspicious TOML instead of appending a managed block', () => {
        const configPath = path.join(tempDir, 'config.toml');
        fs.writeFileSync(configPath, [
            '[mcp_servers.asset-aware-mcp',
            'command = "broken"',
            '',
        ].join('\n'));

        const updated = installCodexMcpServer(context, '/usr/bin/uv');

        assert.strictEqual(updated, false);
        const content = fs.readFileSync(configPath, 'utf-8');
        assert.ok(!content.includes('Managed by asset-aware-mcp VS Code extension'));
        assert.ok(__test__.hasSuspiciousTomlSyntax(content));
    });

    it('skips malformed TOML assignments instead of appending a managed block', () => {
        const configPath = path.join(tempDir, 'config.toml');
        fs.writeFileSync(configPath, [
            '[mcp_servers.other]',
            'command = "unterminated',
            'args = ["server.js"]',
            '',
        ].join('\n'));

        const updated = installCodexMcpServer(context, '/usr/bin/uv');

        assert.strictEqual(updated, false);
        const content = fs.readFileSync(configPath, 'utf-8');
        assert.ok(!content.includes('Managed by asset-aware-mcp VS Code extension'));
        assert.ok(__test__.hasSuspiciousTomlSyntax(content));
    });

    it('skips malformed TOML arrays instead of appending a managed block', () => {
        const configPath = path.join(tempDir, 'config.toml');
        fs.writeFileSync(configPath, [
            '[mcp_servers.other]',
            'command = "node"',
            'args = ["server.js"',
            '',
        ].join('\n'));

        const updated = installCodexMcpServer(context, '/usr/bin/uv');

        assert.strictEqual(updated, false);
        const content = fs.readFileSync(configPath, 'utf-8');
        assert.ok(!content.includes('Managed by asset-aware-mcp VS Code extension'));
        assert.ok(__test__.hasSuspiciousTomlSyntax(content));
    });

    it('removes managed blocks while preserving unrelated content', () => {
        assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv'), true);
        fs.appendFileSync(path.join(tempDir, 'config.toml'), '\n[other]\nkey = "value"\n');

        const removed = removeCodexMcpServer();

        assert.strictEqual(removed, true);
        const content = fs.readFileSync(path.join(tempDir, 'config.toml'), 'utf-8');
        assert.ok(!content.includes('[mcp_servers.asset-aware-mcp]'));
        assert.ok(content.includes('[other]'));
    });
});
