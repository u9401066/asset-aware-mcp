import * as assert from 'assert';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import * as vscode from 'vscode';
import { AssetAwareMcpProvider } from '../../mcpProvider';
import { __resetConfiguration, __setConfigurationValue } from './mock-vscode';

describe('AssetAwareMcpProvider', () => {
    let tempDir: string;

    beforeEach(() => {
        tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'asset-aware-mcp-provider-'));
        (vscode.workspace as any).workspaceFolders = undefined;
        __resetConfiguration();
    });

    afterEach(() => {
        fs.rmSync(tempDir, { recursive: true, force: true });
        (vscode.workspace as any).workspaceFolders = undefined;
        __resetConfiguration();
    });

    function makeContext(overrides: Record<string, any> = {}) {
        return {
            globalState: { get: () => undefined },
            extension: { packageJSON: { version: '0.6.2' } },
            ...overrides,
        } as any;
    }

    it('uses preferred python in production mode', () => {
        const provider = new AssetAwareMcpProvider(tempDir, undefined, makeContext());

        const servers = provider.provideMcpServerDefinitions({} as any) as any[];

        assert.ok(Array.isArray(servers));
        assert.strictEqual(servers.length, 1);
        assert.ok(servers[0].args.includes('--python'));
        assert.ok(servers[0].args.includes('3.11'));
        assert.ok(servers[0].args.includes('--from'));
        assert.ok(servers[0].args.includes('asset-aware-mcp==0.6.2'));
        assert.strictEqual(servers[0].args[servers[0].args.length - 1], 'asset-aware-mcp');
    });

    it('uses preferred python in development mode', () => {
        fs.mkdirSync(path.join(tempDir, 'src'), { recursive: true });
        fs.writeFileSync(path.join(tempDir, 'src', 'server.py'), 'def main():\n    pass\n');
        fs.writeFileSync(path.join(tempDir, 'pyproject.toml'), '[project]\nname = "asset-aware-mcp"\n');
        (vscode.workspace as any).workspaceFolders = [{ uri: { fsPath: tempDir } }];

        const provider = new AssetAwareMcpProvider(tempDir, undefined, makeContext());

        const servers = provider.provideMcpServerDefinitions({} as any) as any[];

        assert.strictEqual(servers.length, 1);
        assert.deepStrictEqual(servers[0].args.slice(0, 5), ['run', '--python', '3.11', '--directory', tempDir]);
        assert.deepStrictEqual(servers[0].args.slice(5), ['python', '-m', 'src.server']);
    });

    it('adds marker runtime args when marker backend is enabled', () => {
        __setConfigurationValue('assetAwareMcp.enableMarkerBackend', true);
        __setConfigurationValue('assetAwareMcp.torchBackend', 'cpu');

        const provider = new AssetAwareMcpProvider(tempDir, undefined, makeContext());

        const servers = provider.provideMcpServerDefinitions({} as any) as any[];

        assert.ok(servers[0].args.includes('--with'));
        assert.ok(servers[0].args.includes('marker-pdf'));
        assert.ok(servers[0].args.includes('--torch-backend'));
        assert.ok(servers[0].args.includes('cpu'));
    });

    it('adds --upgrade flag when needsUpgrade is true', () => {
        const provider = new AssetAwareMcpProvider(tempDir, undefined, makeContext(), true);

        const servers = provider.provideMcpServerDefinitions({} as any) as any[];

        assert.ok(servers[0].args.includes('--upgrade'));
        assert.ok(servers[0].args.includes('--from'));
        assert.ok(servers[0].args.includes('asset-aware-mcp==0.6.2'));
    });

    it('does not add --upgrade flag when needsUpgrade is false', () => {
        const provider = new AssetAwareMcpProvider(tempDir, undefined, makeContext(), false);

        const servers = provider.provideMcpServerDefinitions({} as any) as any[];

        assert.ok(!servers[0].args.includes('--upgrade'));
        assert.ok(servers[0].args.includes('--from'));
    });
});