import * as assert from 'assert';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import * as vscode from 'vscode';
import {
    __buildInstallTerminalOptionsForTests,
    __buildRuntimePrepareEnvForTests,
    __buildRuntimePrepareSpecForTests,
    __buildRuntimePrepareSpecsForTests,
    __runtimePrepareMaxBufferForTests,
    __registerMcpServerProviderForTests,
    __resetMcpServerProviderRegistrationForTests,
} from '../../extension';
import { __resetConfiguration } from './mock-vscode';

describe('extension MCP provider registration', () => {
    afterEach(() => {
        __resetMcpServerProviderRegistrationForTests();
        __resetConfiguration();
        (vscode.workspace as any).workspaceFolders = undefined;
        delete (vscode.lm as any).registerMcpServerDefinitionProvider;
    });

    it('disposes the previous MCP provider registration before replacing it', () => {
        const disposed: string[] = [];
        const registrations: string[] = [];
        (vscode.lm as any).registerMcpServerDefinitionProvider = (
            id: string,
            provider: { token: string },
        ) => {
            registrations.push(`${id}:${provider.token}`);
            return {
                dispose: () => disposed.push(provider.token),
            };
        };
        const context = { subscriptions: [] } as any;

        const firstRegistered = __registerMcpServerProviderForTests(
            context,
            { token: 'first' } as any,
        );
        const secondRegistered = __registerMcpServerProviderForTests(
            context,
            { token: 'second' } as any,
        );

        assert.strictEqual(firstRegistered, true);
        assert.strictEqual(secondRegistered, true);
        assert.deepStrictEqual(registrations, [
            'asset-aware-mcp.servers:first',
            'asset-aware-mcp.servers:second',
        ]);
        assert.deepStrictEqual(disposed, ['first']);
        assert.strictEqual(context.subscriptions.length, 2);
    });

    it('builds runtime prepare env from the same workspace launch env as MCP clients', () => {
        const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'asset aware runtime-'));
        try {
            fs.writeFileSync(
                path.join(tempDir, '.env'),
                [
                    'DATA_DIR=workspace-data',
                    'OLLAMA_MODEL=from-env',
                    'ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS=0',
                    '',
                ].join('\n'),
            );
            (vscode.workspace as any).workspaceFolders = [{ uri: { fsPath: tempDir } }];
            const context = {
                globalStorageUri: { fsPath: path.join(tempDir, 'global storage') },
                extension: { packageJSON: { version: '0.6.19' } },
            } as any;

            const env = __buildRuntimePrepareEnvForTests(context);

            assert.strictEqual(env.DATA_DIR, path.join(tempDir, 'workspace-data'));
            assert.strictEqual(env.UV_CACHE_DIR, path.join(tempDir, 'workspace-data', '.uv-cache'));
            assert.strictEqual(env.OLLAMA_MODEL, 'from-env');
            assert.strictEqual(env.ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS, '12000');
            assert.strictEqual(env.ASSET_AWARE_TABLE_STARTUP_LOAD_MAX_BYTES, '20971520');
        } finally {
            fs.rmSync(tempDir, { recursive: true, force: true });
        }
    });

    it('prepares the local source runtime with the same source-root env as MCP clients', () => {
        const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'asset aware local runtime-'));
        try {
            const sourceRoot = path.join(tempDir, 'asset-aware-mcp');
            fs.mkdirSync(path.join(sourceRoot, 'src'), { recursive: true });
            fs.writeFileSync(path.join(sourceRoot, 'src', 'server.py'), 'def main():\n    pass\n');
            fs.writeFileSync(path.join(sourceRoot, 'pyproject.toml'), '[project]\nname = "asset-aware-mcp"\n');
            fs.writeFileSync(path.join(tempDir, '.env'), 'DATA_DIR=parent-data\nOLLAMA_MODEL=parent-model\n');
            fs.writeFileSync(path.join(sourceRoot, '.env'), 'DATA_DIR=child-data\nOLLAMA_MODEL=child-model\n');
            (vscode.workspace as any).workspaceFolders = [{ uri: { fsPath: tempDir } }];
            const context = {
                globalStorageUri: { fsPath: path.join(tempDir, 'global storage') },
                extension: { packageJSON: { version: '0.6.19' } },
            } as any;

            const spec = __buildRuntimePrepareSpecForTests(context, 'uv', false);

            assert.strictEqual(spec.command, 'uv');
            assert.strictEqual(spec.mode, 'local');
            assert.deepStrictEqual(spec.args.slice(0, 5), ['run', '--python', '3.11', '--directory', sourceRoot]);
            assert.deepStrictEqual(spec.args.slice(5, 7), ['python', '-c']);
            assert.ok(spec.args[7].includes('src.presentation.server'));
            assert.strictEqual(spec.env.OLLAMA_MODEL, 'child-model');
            assert.strictEqual(spec.env.DATA_DIR, path.resolve(sourceRoot, 'child-data'));
        } finally {
            fs.rmSync(tempDir, { recursive: true, force: true });
        }
    });

    it('builds runtime prepare specs with a Python 3.10 fallback for older macOS', () => {
        const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'asset aware runtime fallback-'));
        try {
            (vscode.workspace as any).workspaceFolders = [{ uri: { fsPath: tempDir } }];
            const context = {
                globalStorageUri: { fsPath: path.join(tempDir, 'global storage') },
                extension: { packageJSON: { version: '0.6.19' } },
            } as any;

            const specs = __buildRuntimePrepareSpecsForTests(context, 'uv', false);

            assert.strictEqual(specs.length, 2);
            assert.deepStrictEqual(specs[0].args.slice(0, 4), ['tool', 'run', '--python', '3.11']);
            assert.deepStrictEqual(specs[1].args.slice(0, 4), ['tool', 'run', '--python', '3.10']);
            assert.strictEqual(specs[0].pythonVersion, '3.11');
            assert.strictEqual(specs[1].pythonVersion, '3.10');
        } finally {
            fs.rmSync(tempDir, { recursive: true, force: true });
        }
    });

    it('uses a large runtime prepare buffer for first-install uv output', () => {
        assert.ok(__runtimePrepareMaxBufferForTests() >= 50 * 1024 * 1024);
    });

    it('uses PowerShell for optional install terminals on Windows', () => {
        const cwd = 'C:\\Users\\Alice Smith\\asset-aware-mcp';
        const options = __buildInstallTerminalOptionsForTests(
            'Asset-Aware MCP: Install lightrag',
            cwd,
            'win32',
        );

        assert.strictEqual(options.name, 'Asset-Aware MCP: Install lightrag');
        assert.strictEqual(options.cwd, cwd);
        assert.strictEqual(options.shellPath, 'powershell.exe');
        assert.deepStrictEqual(options.shellArgs, [
            '-NoLogo',
            '-NoProfile',
            '-ExecutionPolicy',
            'Bypass',
        ]);
    });

    it('keeps the user default terminal shell on non-Windows optional installs', () => {
        const options = __buildInstallTerminalOptionsForTests(
            'Asset-Aware MCP: Install lightrag',
            '/Users/alice/asset-aware-mcp',
            'darwin',
        );

        assert.strictEqual(options.name, 'Asset-Aware MCP: Install lightrag');
        assert.strictEqual(options.cwd, '/Users/alice/asset-aware-mcp');
        assert.strictEqual(options.shellPath, undefined);
        assert.strictEqual(options.shellArgs, undefined);
    });
});
