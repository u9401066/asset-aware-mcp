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
        assert.strictEqual(env.ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS, '12000');
        assert.strictEqual(env.ASSET_AWARE_MCP_IMAGE_RESPONSE_CHARS, '750000');
        assert.strictEqual(env.ASSET_AWARE_TABLE_STARTUP_LOAD_MAX_BYTES, '20971520');
        assert.strictEqual(env.ASSET_AWARE_SECTION_TREE_LOAD_MAX_BYTES, '20971520');
        assert.strictEqual(env.ASSET_AWARE_SEGMENTATION_SOURCE_LOAD_MAX_BYTES, '20971520');
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

    it('loads OpenRouter preset settings from workspace .env', () => {
        fs.writeFileSync(path.join(tempDir, '.env'), [
            'LLM_BACKEND=openrouter',
            'OPENROUTER_API_KEY=sk-or-test',
            'OPENROUTER_BASE_URL=https://openrouter.ai/api/v1',
            'OPENROUTER_MODEL=liquid/lfm-2.5-1.2b-instruct:free',
            '',
        ].join('\n'));
        const context = { globalStorageUri: { fsPath: path.join(tempDir, 'global') } } as any;

        const env = buildAssetAwareEnv(context, tempDir);

        assert.strictEqual(env.LLM_BACKEND, 'openrouter');
        assert.strictEqual(env.OPENROUTER_API_KEY, 'sk-or-test');
        assert.strictEqual(env.OPENROUTER_BASE_URL, 'https://openrouter.ai/api/v1');
        assert.strictEqual(env.OPENROUTER_MODEL, 'liquid/lfm-2.5-1.2b-instruct:free');
    });

    it('uses explicit VS Code OpenRouter settings without requiring a .env file', () => {
        __setConfigurationValue('assetAwareMcp.llmBackend', 'openrouter');
        __setConfigurationValue('assetAwareMcp.openrouterApiKey', 'sk-or-config');
        __setConfigurationValue('assetAwareMcp.openrouterModel', 'liquid/custom:free');
        const context = { globalStorageUri: { fsPath: path.join(tempDir, 'global') } } as any;

        const env = buildAssetAwareEnv(context, tempDir);

        assert.strictEqual(env.LLM_BACKEND, 'openrouter');
        assert.strictEqual(env.OPENROUTER_API_KEY, 'sk-or-config');
        assert.strictEqual(env.OPENROUTER_MODEL, 'liquid/custom:free');
        assert.strictEqual(env.OPENROUTER_BASE_URL, undefined);
    });

    it('clamps unsafe .env OOM guard values back to VSIX safety defaults', () => {
        fs.writeFileSync(path.join(tempDir, '.env'), [
            'ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS=0',
            'ASSET_AWARE_MCP_IMAGE_RESPONSE_CHARS=999999999',
            'ASSET_AWARE_TABLE_STARTUP_LOAD_MAX_BYTES=0',
            'ASSET_AWARE_SECTION_TREE_LOAD_MAX_BYTES=0',
            'ASSET_AWARE_SEGMENTATION_SOURCE_LOAD_MAX_BYTES=999999999',
            '',
        ].join('\n'));
        const context = { globalStorageUri: { fsPath: path.join(tempDir, 'global') } } as any;

        const env = buildAssetAwareEnv(context, tempDir);

        assert.strictEqual(env.ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS, '12000');
        assert.strictEqual(env.ASSET_AWARE_MCP_IMAGE_RESPONSE_CHARS, '750000');
        assert.strictEqual(env.ASSET_AWARE_TABLE_STARTUP_LOAD_MAX_BYTES, '20971520');
        assert.strictEqual(env.ASSET_AWARE_SECTION_TREE_LOAD_MAX_BYTES, '20971520');
        assert.strictEqual(env.ASSET_AWARE_SEGMENTATION_SOURCE_LOAD_MAX_BYTES, '20971520');
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
        assert.strictEqual(launch.env.ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS, '12000');
        assert.strictEqual(launch.env.ASSET_AWARE_MCP_IMAGE_RESPONSE_CHARS, '750000');
        assert.strictEqual(launch.env.ASSET_AWARE_TABLE_STARTUP_LOAD_MAX_BYTES, '20971520');
    });
});
