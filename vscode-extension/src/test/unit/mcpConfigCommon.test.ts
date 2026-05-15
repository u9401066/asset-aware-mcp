import * as assert from 'assert';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import * as vscode from 'vscode';
import { buildAssetAwareEnv, buildAssetAwareLaunchSpec } from '../../mcpConfigCommon';
import { __resetConfiguration, __setConfigurationValue } from './mock-vscode';

describe('mcpConfigCommon', () => {
    let tempDir: string;
    let originalAssetAwareHasGpu: string | undefined;
    let originalAssetAwareUseGpu: string | undefined;
    let originalAssetAwareGpu: string | undefined;
    let originalNvidiaVisibleDevices: string | undefined;
    let originalCudaVisibleDevices: string | undefined;

    beforeEach(() => {
        tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'asset-aware-mcp-common-'));
        (vscode.workspace as any).workspaceFolders = undefined;
        __resetConfiguration();
        originalAssetAwareHasGpu = process.env.ASSET_AWARE_HAS_GPU;
        originalAssetAwareUseGpu = process.env.ASSET_AWARE_USE_GPU;
        originalAssetAwareGpu = process.env.ASSET_AWARE_GPU;
        originalNvidiaVisibleDevices = process.env.NVIDIA_VISIBLE_DEVICES;
        originalCudaVisibleDevices = process.env.CUDA_VISIBLE_DEVICES;
        delete process.env.ASSET_AWARE_HAS_GPU;
        delete process.env.ASSET_AWARE_USE_GPU;
        delete process.env.ASSET_AWARE_GPU;
        delete process.env.NVIDIA_VISIBLE_DEVICES;
        delete process.env.CUDA_VISIBLE_DEVICES;
    });

    afterEach(() => {
        fs.rmSync(tempDir, { recursive: true, force: true });
        (vscode.workspace as any).workspaceFolders = undefined;
        __resetConfiguration();
        restoreEnv('ASSET_AWARE_HAS_GPU', originalAssetAwareHasGpu);
        restoreEnv('ASSET_AWARE_USE_GPU', originalAssetAwareUseGpu);
        restoreEnv('ASSET_AWARE_GPU', originalAssetAwareGpu);
        restoreEnv('NVIDIA_VISIBLE_DEVICES', originalNvidiaVisibleDevices);
        restoreEnv('CUDA_VISIBLE_DEVICES', originalCudaVisibleDevices);
    });

    function restoreEnv(key: string, value: string | undefined): void {
        if (value === undefined) {
            delete process.env[key];
        } else {
            process.env[key] = value;
        }
    }

    it('defaults to CPU Granite RAG without enabling LightRAG', () => {
        const context = { globalStorageUri: { fsPath: path.join(tempDir, 'global') } } as any;

        const env = buildAssetAwareEnv(context, tempDir);

        assert.strictEqual(env.OLLAMA_MODEL, 'granite4.1:3b');
        assert.strictEqual(env.OLLAMA_EMBEDDING_MODEL, 'nomic-embed-text');
        assert.strictEqual(env.ENABLE_LIGHTRAG, 'false');
    });

    it('uses the 8b Granite RAG default when GPU hint is enabled', () => {
        process.env.ASSET_AWARE_HAS_GPU = 'true';
        const context = { globalStorageUri: { fsPath: path.join(tempDir, 'global') } } as any;

        const env = buildAssetAwareEnv(context, tempDir);

        assert.strictEqual(env.OLLAMA_MODEL, 'granite4.1:8b');
        assert.strictEqual(env.ENABLE_LIGHTRAG, 'false');
    });

    it('keeps .env Ollama model override when GPU hint is enabled', () => {
        process.env.ASSET_AWARE_HAS_GPU = 'true';
        fs.writeFileSync(path.join(tempDir, '.env'), 'DATA_DIR=operator-data\nOLLAMA_MODEL=operator-model\n');
        const context = { globalStorageUri: { fsPath: path.join(tempDir, 'global') } } as any;

        const env = buildAssetAwareEnv(context, tempDir);

        assert.strictEqual(env.OLLAMA_MODEL, 'operator-model');
        assert.strictEqual(env.DATA_DIR, path.resolve(tempDir, 'operator-data'));
    });

    it('keeps explicit VS Code Ollama model override when GPU hint is enabled', () => {
        process.env.ASSET_AWARE_HAS_GPU = 'true';
        __setConfigurationValue('assetAwareMcp.ollamaModel', 'operator-config-model');
        const context = { globalStorageUri: { fsPath: path.join(tempDir, 'global') } } as any;

        const env = buildAssetAwareEnv(context, tempDir);

        assert.strictEqual(env.OLLAMA_MODEL, 'operator-config-model');
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
