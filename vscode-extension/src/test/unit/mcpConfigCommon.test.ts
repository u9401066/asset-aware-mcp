import * as assert from 'assert';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import * as vscode from 'vscode';
import { buildAssetAwareEnv, buildAssetAwareLaunchSpec } from '../../mcpConfigCommon';
import { __resetConfiguration } from './mock-vscode';

describe('mcpConfigCommon', () => {
    let tempDir: string;

    beforeEach(() => {
        tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'asset-aware-mcp-common-'));
        (vscode.workspace as any).workspaceFolders = undefined;
        __resetConfiguration();
    });

    afterEach(() => {
        fs.rmSync(tempDir, { recursive: true, force: true });
        (vscode.workspace as any).workspaceFolders = undefined;
        __resetConfiguration();
    });

    it('defaults to Granite RAG without enabling LightRAG', () => {
        const context = { globalStorageUri: { fsPath: path.join(tempDir, 'global') } } as any;

        const env = buildAssetAwareEnv(context, tempDir);

        assert.strictEqual(env.OLLAMA_MODEL, 'granite4.1');
        assert.strictEqual(env.OLLAMA_EMBEDDING_MODEL, 'nomic-embed-text');
        assert.strictEqual(env.ENABLE_LIGHTRAG, 'false');
    });

    it('builds local-source env from detected source root', () => {
        const sourceRoot = path.join(tempDir, 'asset-aware-mcp');
        fs.mkdirSync(path.join(sourceRoot, 'src'), { recursive: true });
        fs.writeFileSync(path.join(sourceRoot, 'src', 'server.py'), 'def main():\n    pass\n');
        fs.writeFileSync(path.join(sourceRoot, 'pyproject.toml'), '[project]\nname = "asset-aware-mcp"\n');
        fs.writeFileSync(path.join(sourceRoot, '.env'), 'DATA_DIR=child-data\nOLLAMA_MODEL=from-child\n');
        fs.writeFileSync(path.join(tempDir, '.env'), 'DATA_DIR=parent-data\nOLLAMA_MODEL=from-parent\n');
        (vscode.workspace as any).workspaceFolders = [{ uri: { fsPath: tempDir } }];
        const context = { globalStorageUri: { fsPath: path.join(tempDir, 'global') } } as any;

        const launch = buildAssetAwareLaunchSpec(context, 'uv', { workspaceRoot: tempDir });

        assert.strictEqual(launch.mode, 'local');
        assert.deepStrictEqual(
            launch.args.slice(launch.args.indexOf('--directory'), launch.args.indexOf('--directory') + 2),
            ['--directory', sourceRoot],
        );
        assert.strictEqual(launch.env.OLLAMA_MODEL, 'from-child');
        assert.strictEqual(launch.env.DATA_DIR, path.resolve(sourceRoot, 'child-data'));
        assert.strictEqual(
            launch.env.UV_CACHE_DIR,
            path.join(sourceRoot, 'child-data', '.uv-cache'),
        );
        assert.strictEqual(launch.env.ASSET_AWARE_SUPPRESS_MARKER_OUTPUT, 'true');
        assert.strictEqual(
            launch.env.ASSET_AWARE_MARKER_OUTPUT_LOG,
            path.join(sourceRoot, 'child-data', 'logs', 'marker.log'),
        );
    });
});
