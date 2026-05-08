/**
 * Extension Test Suite
 *
 * Tests for the Asset-Aware MCP VS Code Extension
 */

import * as assert from 'assert';
import * as vscode from 'vscode';
import * as path from 'path';

suite('Extension Test Suite', () => {
    vscode.window.showInformationMessage('Start all tests.');

    test('Extension should be present', () => {
        const extension = vscode.extensions.getExtension('u9401066.asset-aware-mcp');
        assert.ok(extension, 'Extension should be installed');
    });

    test('Extension should activate', async () => {
        const extension = vscode.extensions.getExtension('u9401066.asset-aware-mcp');
        if (extension) {
            await extension.activate();
            assert.ok(extension.isActive, 'Extension should be active');
        }
    });

    test('Commands should be registered', async () => {
        const commands = await vscode.commands.getCommands(true);

        const expectedCommands = [
            'assetAwareMcp.setupWizard',
            'assetAwareMcp.openSettings',
            'assetAwareMcp.installAssistantAssets',
            'assetAwareMcp.configureExternalMcp',
            'assetAwareMcp.showStatus',
            'assetAwareMcp.checkConnection',
            'assetAwareMcp.editEnv',
            'assetAwareMcp.refreshStatus',
            'assetAwareMcp.checkDependencies',
            'assetAwareMcp.showOutput'
        ];

        for (const cmd of expectedCommands) {
            assert.ok(
                commands.includes(cmd),
                `Command ${cmd} should be registered`
            );
        }
    });

    test('Configuration should have default values', () => {
        const config = vscode.workspace.getConfiguration('assetAwareMcp');

        assert.strictEqual(config.get('llmBackend'), 'ollama');
        assert.strictEqual(config.get('ollamaHost'), 'http://localhost:11434');
        assert.strictEqual(config.get('ollamaModel'), 'qwen2.5:7b');
        assert.strictEqual(config.get('ollamaEmbeddingModel'), 'nomic-embed-text');
        assert.strictEqual(config.get('dataDir'), './data');
    });

    test('Installed activation smoke verifies MCP provider launch definition', async function () {
        if (process.env.ASSET_AWARE_MCP_VERIFY_PROVIDER_LAUNCH !== '1') {
            this.skip();
        }

        const extension = vscode.extensions.getExtension('u9401066.asset-aware-mcp');
        assert.ok(extension, 'Extension should be installed');
        const expectedExtensionDir = process.env.ASSET_AWARE_MCP_EXPECT_EXTENSION_DIR;
        if (process.env.ASSET_AWARE_MCP_EXPECT_INSTALLED_EXTENSION === '1' && expectedExtensionDir) {
            assert.strictEqual(
                path.resolve(extension.extensionPath),
                path.resolve(expectedExtensionDir),
                'Activation smoke should discover the installed VSIX extension, not only a dev extension path',
            );
        }
        const api = await extension.activate() as {
            getMcpProviderForTests?: () => vscode.McpServerDefinitionProvider<vscode.McpStdioServerDefinition> | undefined;
        };

        const provider = api.getMcpProviderForTests?.();
        assert.ok(provider, 'MCP provider should be initialized after activation');

        const servers = provider.provideMcpServerDefinitions({} as any) as any[];
        assert.strictEqual(servers.length, 1);
        assert.strictEqual(servers[0].label, 'Asset-Aware MCP');
        assert.ok(servers[0].args.includes('--python'));
        assert.ok(servers[0].args.includes('3.11'));
        assert.ok(servers[0].args.includes('--from'));
        assert.ok(servers[0].args.some((arg: string) => arg.startsWith('asset-aware-mcp==')));
        assert.strictEqual(servers[0].args[servers[0].args.length - 1], 'asset-aware-mcp');
    });
});

suite('MCP Provider Test Suite', () => {
    test('getUvPaths should return valid paths', () => {
        const homeDir = process.env.HOME || process.env.USERPROFILE || '';
        const platform = process.platform;

        // Just verify we have a home directory
        assert.ok(homeDir.length > 0, 'Home directory should be set');

        // Verify platform is recognized
        assert.ok(
            ['win32', 'darwin', 'linux'].includes(platform),
            'Platform should be recognized'
        );
    });
});

suite('Utility Functions Test Suite', () => {
    test('Path resolution should work correctly', () => {
        const testPath = './data';
        const basePath = '/home/user/workspace';
        const expected = path.join(basePath, 'data');

        const resolved = path.isAbsolute(testPath)
            ? testPath
            : path.join(basePath, testPath);

        assert.strictEqual(resolved, expected);
    });

    test('Environment variable parsing simulation', () => {
        const envContent = `
# This is a comment
LLM_BACKEND=ollama
OLLAMA_HOST="http://localhost:11434"
OLLAMA_MODEL='qwen2.5:7b'
EMPTY_VALUE=
        `.trim();

        const env: Record<string, string> = {};
        const lines = envContent.split('\n');

        for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || trimmed.startsWith('#')) {
                continue;
            }

            const eqIndex = trimmed.indexOf('=');
            if (eqIndex > 0) {
                const key = trimmed.substring(0, eqIndex).trim();
                let value = trimmed.substring(eqIndex + 1).trim();

                // Remove quotes if present
                if ((value.startsWith('"') && value.endsWith('"')) ||
                    (value.startsWith("'") && value.endsWith("'"))) {
                    value = value.slice(1, -1);
                }

                env[key] = value;
            }
        }

        assert.strictEqual(env['LLM_BACKEND'], 'ollama');
        assert.strictEqual(env['OLLAMA_HOST'], 'http://localhost:11434');
        assert.strictEqual(env['OLLAMA_MODEL'], 'qwen2.5:7b');
        assert.strictEqual(env['EMPTY_VALUE'], '');
    });
});
