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
            extension: { packageJSON: { version: '0.6.19' } },
            globalStorageUri: { fsPath: path.join(tempDir, 'global-storage') },
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
        assert.ok(servers[0].args.includes('asset-aware-mcp==0.6.19'));
        assert.strictEqual(servers[0].args[servers[0].args.length - 1], 'asset-aware-mcp');
    });

    it('production launch definition includes runtime env needed for server availability checks', () => {
        const provider = new AssetAwareMcpProvider(
            tempDir,
            undefined,
            makeContext({ globalState: { get: () => 'uv' } }),
        );

        const servers = provider.provideMcpServerDefinitions({} as any) as any[];

        assert.strictEqual(servers.length, 1);
        assert.strictEqual(servers[0].command, 'uvx');
        assert.ok(servers[0].env.DATA_DIR);
        assert.ok(servers[0].env.UV_CACHE_DIR);
        assert.match(servers[0].env.ASSET_AWARE_MARKER_OUTPUT_LOG, /marker\.log$/);
        assert.strictEqual(servers[0].env.ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS, '12000');
        assert.strictEqual(servers[0].env.ASSET_AWARE_MCP_IMAGE_RESPONSE_CHARS, '750000');
        assert.strictEqual(servers[0].env.ASSET_AWARE_TABLE_STARTUP_LOAD_MAX_BYTES, '20971520');
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

    it('does not add marker extra in development mode while marker backend is on security hold', () => {
        fs.mkdirSync(path.join(tempDir, 'src'), { recursive: true });
        fs.writeFileSync(path.join(tempDir, 'src', 'server.py'), 'def main():\n    pass\n');
        fs.writeFileSync(path.join(tempDir, 'pyproject.toml'), '[project]\nname = "asset-aware-mcp"\n');
        (vscode.workspace as any).workspaceFolders = [{ uri: { fsPath: tempDir } }];
        __setConfigurationValue('assetAwareMcp.enableMarkerBackend', true);

        const provider = new AssetAwareMcpProvider(tempDir, undefined, makeContext());

        const servers = provider.provideMcpServerDefinitions({} as any) as any[];

        assert.ok(!servers[0].args.includes('--extra'));
        assert.ok(!servers[0].args.includes('marker'));
        assert.ok(!servers[0].args.includes('marker-pdf'));
    });

    it('resolves local source .env DATA_DIR relative to the local source root', () => {
        const workspaceRoot = path.join(tempDir, 'workspace');
        const sourceRoot = path.join(workspaceRoot, 'asset-aware-mcp');
        fs.mkdirSync(path.join(sourceRoot, 'src'), { recursive: true });
        fs.writeFileSync(path.join(sourceRoot, 'src', 'server.py'), 'def main():\n    pass\n');
        fs.writeFileSync(path.join(sourceRoot, 'pyproject.toml'), '[project]\nname = "asset-aware-mcp"\n');
        fs.writeFileSync(path.join(workspaceRoot, '.env'), 'DATA_DIR=parent-data\nOLLAMA_MODEL=parent-model\n');
        fs.writeFileSync(path.join(sourceRoot, '.env'), 'DATA_DIR=child-data\nOLLAMA_MODEL=child-model\n');
        (vscode.workspace as any).workspaceFolders = [{ uri: { fsPath: workspaceRoot } }];

        const provider = new AssetAwareMcpProvider(workspaceRoot, undefined, makeContext());

        const servers = provider.provideMcpServerDefinitions({} as any) as any[];

        assert.strictEqual(servers.length, 1);
        assert.strictEqual(servers[0].label, 'Asset-Aware MCP (Dev)');
        assert.strictEqual(servers[0].env.OLLAMA_MODEL, 'child-model');
        assert.strictEqual(
            servers[0].env.DATA_DIR,
            path.resolve(sourceRoot, 'child-data'),
        );
    });

    it('omits marker runtime args while marker backend is on security hold', () => {
        __setConfigurationValue('assetAwareMcp.enableMarkerBackend', true);
        __setConfigurationValue('assetAwareMcp.torchBackend', 'cpu');

        const provider = new AssetAwareMcpProvider(tempDir, undefined, makeContext());

        const servers = provider.provideMcpServerDefinitions({} as any) as any[];

        assert.ok(!servers[0].args.includes('--with'));
        assert.ok(!servers[0].args.includes('marker-pdf'));
        assert.ok(!servers[0].args.includes('--torch-backend'));
    });

    it('logs package launch diagnostics for marker security hold without touching stdio', () => {
        __setConfigurationValue('assetAwareMcp.enableMarkerBackend', true);
        __setConfigurationValue('assetAwareMcp.torchBackend', 'cpu');
        const lines: string[] = [];
        const outputChannel = {
            appendLine(message: string) {
                lines.push(message);
            },
        } as any;

        const provider = new AssetAwareMcpProvider(
            tempDir,
            outputChannel,
            makeContext({ globalState: { get: () => 'uv' } }),
        );

        const servers = provider.provideMcpServerDefinitions({} as any) as any[];
        const logOutput = lines.join('\n');

        assert.deepStrictEqual(servers[0].args, [
            '--python',
            '3.11',
            '--from',
            'asset-aware-mcp==0.6.19',
            'asset-aware-mcp',
        ]);
        assert.match(logOutput, /Launch mode: package/);
        assert.match(logOutput, /Command: uvx --python 3\.11 --from asset-aware-mcp==0\.6\.19 asset-aware-mcp/);
        assert.match(logOutput, /DATA_DIR: /);
        assert.match(logOutput, /Server version pin: 0\.6\.19/);
        assert.match(logOutput, /Marker backend enabled: true/);
        assert.match(logOutput, /Marker backend requested but temporarily disabled/);
        assert.match(logOutput, /marker-pdf pins Pillow<11/);
        assert.doesNotMatch(logOutput, /Marker cold start may download/);
    });

    it('adds --upgrade flag when needsUpgrade is true', () => {
        const provider = new AssetAwareMcpProvider(tempDir, undefined, makeContext(), true);

        const servers = provider.provideMcpServerDefinitions({} as any) as any[];

        assert.ok(servers[0].args.includes('--upgrade'));
        assert.ok(servers[0].args.includes('--from'));
        assert.ok(servers[0].args.includes('asset-aware-mcp==0.6.19'));
    });

    it('does not add --upgrade flag when needsUpgrade is false', () => {
        const provider = new AssetAwareMcpProvider(tempDir, undefined, makeContext(), false);

        const servers = provider.provideMcpServerDefinitions({} as any) as any[];

        assert.ok(!servers[0].args.includes('--upgrade'));
        assert.ok(servers[0].args.includes('--from'));
    });

    it('merges workspace .env in production mode', () => {
        fs.writeFileSync(
            path.join(tempDir, '.env'),
            'OLLAMA_MODEL=from-env\nDATA_DIR=custom-data\nLIGHTRAG_EMBEDDING_MODEL=text-embedding-3-large\n',
        );
        const provider = new AssetAwareMcpProvider(tempDir, undefined, makeContext());

        const servers = provider.provideMcpServerDefinitions({} as any) as any[];

        assert.strictEqual(servers[0].env.OLLAMA_MODEL, 'from-env');
        assert.strictEqual(
            servers[0].env.DATA_DIR,
            path.resolve(tempDir, 'custom-data'),
        );
        assert.strictEqual(
            servers[0].env.LIGHTRAG_EMBEDDING_MODEL,
            'text-embedding-3-large',
        );
    });

    it('passes OpenAI embedding setting to Python runtime env', () => {
        __setConfigurationValue('assetAwareMcp.openaiApiKey', 'sk-test');
        __setConfigurationValue('assetAwareMcp.openaiEmbeddingModel', 'text-embedding-3-large');
        const provider = new AssetAwareMcpProvider(tempDir, undefined, makeContext());

        const servers = provider.provideMcpServerDefinitions({} as any) as any[];

        assert.strictEqual(
            servers[0].env.LIGHTRAG_EMBEDDING_MODEL,
            'text-embedding-3-large',
        );
    });

    it('maps legacy OPENAI_EMBEDDING_MODEL .env values to LIGHTRAG_EMBEDDING_MODEL', () => {
        fs.writeFileSync(
            path.join(tempDir, '.env'),
            'OPENAI_EMBEDDING_MODEL=text-embedding-legacy\n',
        );
        const provider = new AssetAwareMcpProvider(tempDir, undefined, makeContext());

        const servers = provider.provideMcpServerDefinitions({} as any) as any[];

        assert.strictEqual(
            servers[0].env.LIGHTRAG_EMBEDDING_MODEL,
            'text-embedding-legacy',
        );
        assert.strictEqual(
            servers[0].env.OPENAI_EMBEDDING_MODEL,
            'text-embedding-legacy',
        );
    });
});
