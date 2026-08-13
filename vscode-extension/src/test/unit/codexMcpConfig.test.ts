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
import { __resetConfiguration, __setConfigurationValue } from './mock-vscode';

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
        (vscode.workspace as any).isTrusted = true;
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
        (vscode.workspace as any).isTrusted = true;
        __resetConfiguration();
    });

    it('honors CODEX_HOME and detects availability', () => {
        assert.strictEqual(getCodexHome(), tempDir);
        assert.strictEqual(getCodexConfigPath(), path.join(tempDir, 'config.toml'));
        assert.strictEqual(isCodexAvailable(), true);
    });

    it('publishes a machine-scoped Codex management opt-out', () => {
        const packageJson = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../../package.json'), 'utf-8'));
        const setting = packageJson.contributes.configuration.properties['assetAwareMcp.manageCodexConfig'];

        assert.strictEqual(setting.type, 'boolean');
        assert.strictEqual(setting.default, true);
        assert.strictEqual(setting.scope, 'machine');
        assert.strictEqual(packageJson.capabilities.untrustedWorkspaces.supported, 'limited');
    });

    it('escapes TOML strings safely', () => {
        assert.strictEqual(__test__.escapeTomlString('C:\\Users\\A "B"'), 'C:\\\\Users\\\\A \\"B\\"');
    });

    it('escapes every TOML-forbidden C0 control and DEL without changing the value', () => {
        const original = Array.from({ length: 32 }, (_, index) => String.fromCharCode(index)).join('')
            + String.fromCharCode(0x7f);
        const escaped = __test__.escapeTomlString(original);
        const parsed = __test__.parseTomlConfig(`value = "${escaped}"\n`);

        assert.strictEqual(parsed?.value, original);
        assert.ok(Array.from(escaped).every((char) => {
            const code = char.charCodeAt(0);
            return code > 0x1f && code !== 0x7f;
        }));
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
        assert.ok(content.includes('enabled = true'));
        assert.ok(content.includes('startup_timeout_sec = 180'));
        assert.ok(content.includes('tool_timeout_sec = 900'));
        assert.ok(!content.includes('env_vars ='));
        assert.ok(content.includes(`cwd = "${__test__.escapeTomlString(context.globalStorageUri.fsPath)}"`));
        assert.ok(fs.statSync(context.globalStorageUri.fsPath).isDirectory());
        assert.ok(content.includes('ASSET_AWARE_DISABLE_DOTENV = "true"'));
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

    it('is byte-stable across repeated managed config syncs', () => {
        assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv'), true);
        const first = fs.readFileSync(path.join(tempDir, 'config.toml'), 'utf-8');

        assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv'), false);
        const second = fs.readFileSync(path.join(tempDir, 'config.toml'), 'utf-8');

        assert.strictEqual(second, first);
        assert.strictEqual((second.match(/enabled = true/g) ?? []).length, 1);
        assert.strictEqual((second.match(/startup_timeout_sec = 180/g) ?? []).length, 1);
        assert.strictEqual((second.match(/tool_timeout_sec = 900/g) ?? []).length, 1);
    });

    it('includes --upgrade when activation detected a server version change', () => {
        assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv', true), true);

        const content = fs.readFileSync(path.join(tempDir, 'config.toml'), 'utf-8');
        assert.ok(content.includes('"--upgrade"'));
    });

    it('uses global settings but ignores repository env when writing global Codex config', () => {
        __setConfigurationValue('assetAwareMcp.llmBackend', 'openrouter');
        __setConfigurationValue('assetAwareMcp.openrouterApiKey', 'GLOBAL_ROUTER_SECRET_DO_NOT_PERSIST');
        __setConfigurationValue('assetAwareMcp.openrouterBaseUrl', 'https://router.internal/api/v1');
        __setConfigurationValue('assetAwareMcp.dataDir', 'global-data');
        fs.writeFileSync(path.join(tempDir, '.env'), [
            'LLM_BACKEND=openrouter',
            'DATA_DIR=next-data',
            'OLLAMA_MODEL=from-env',
            'OLLAMA_HOST=http://ollama.internal:11434',
            'ETL_ENGINE=pymupdf4llm',
            'OPENROUTER_BASE_URL=https://router.internal/api/v1',
            'ASSET_AWARE_MARKER_OUTPUT_LOG=/var/tmp/asset-aware/marker.log',
            'OPENAI_API_KEY=OPENAI_SENTINEL_DO_NOT_PERSIST',
            'OPENROUTER_API_KEY=OPENROUTER_SENTINEL_DO_NOT_PERSIST',
            'MISTRAL_API_KEY=MISTRAL_SENTINEL_DO_NOT_PERSIST',
            'DATABASE_URL=postgresql://secret-user:secret-password@db.example/test',
            'DB_PASSWORD=database-secret-literal',
            'INTERNAL_SERVICE_URL=https://private.example/?token=secret-query',
            '',
        ].join('\n'));
        fs.writeFileSync(path.join(tempDir, 'config.toml'), [
            '# user comment',
            '',
            '# Managed by asset-aware-mcp VS Code extension. Remove this block to opt out.',
            '[mcp_servers.asset-aware-mcp]',
            'command = "/old/uv"',
            'args = ["tool", "run", "asset-aware-mcp"]',
            'env_vars = ["EXISTING_FORWARD"]',
            '',
            '[mcp_servers.asset-aware-mcp.env]',
            'HTTP_PROXY = "http://proxy.local:8080"',
            'SSL_CERT_FILE = "C:\\\\certs\\\\corp.pem"',
            'OPENAI_API_KEY = "LEGACY_SENTINEL_DO_NOT_PERSIST"',
            'ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS = "0"',
            'ASSET_AWARE_MCP_IMAGE_RESPONSE_CHARS = "999999999"',
            '',
        ].join('\n'));

        const updated = installCodexMcpServer(context, '/usr/bin/uv');

        assert.strictEqual(updated, true);
        const content = fs.readFileSync(path.join(tempDir, 'config.toml'), 'utf-8');
        const parsed = __test__.parseTomlConfig(content);
        const server = __test__.getSemanticServer(parsed!, 'asset-aware-mcp');
        assert.ok(content.includes('# user comment'));
        assert.ok(!content.includes('OLLAMA_MODEL ='));
        assert.ok(!content.includes('OLLAMA_HOST ='));
        assert.ok(!content.includes('ETL_ENGINE ='));
        assert.ok(content.includes('OPENROUTER_BASE_URL = "https://router.internal/api/v1"'));
        assert.ok(!content.includes('/var/tmp/asset-aware/marker.log'));
        assert.ok(content.includes(`DATA_DIR = "${__test__.escapeTomlString(path.join(context.globalStorageUri.fsPath, 'global-data'))}"`));
        assert.ok(content.includes('ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS = "12000"'));
        assert.ok(content.includes('ASSET_AWARE_MCP_IMAGE_RESPONSE_CHARS = "750000"'));
        assert.ok(content.includes('ASSET_AWARE_TABLE_STARTUP_LOAD_MAX_BYTES = "20971520"'));
        assert.ok(content.includes('"OPENROUTER_API_KEY"'));
        assert.ok(content.includes('"EXISTING_FORWARD"'));
        assert.deepStrictEqual(server?.env_vars, ['EXISTING_FORWARD', 'OPENROUTER_API_KEY']);
        assert.ok(!content.includes('"DATABASE_URL"'));
        assert.ok(!content.includes('"DB_PASSWORD"'));
        assert.ok(!content.includes('"OPENAI_API_KEY"'));
        assert.ok(!content.includes('"MISTRAL_API_KEY"'));
        assert.ok(!content.includes('"HTTP_PROXY"'));
        assert.ok(!content.includes('"SSL_CERT_FILE"'));
        assert.ok(!content.includes('HTTP_PROXY ='));
        assert.ok(!content.includes('SSL_CERT_FILE ='));
        assert.ok(!content.includes('OPENAI_API_KEY ='));
        assert.ok(!content.includes('OPENAI_SENTINEL_DO_NOT_PERSIST'));
        assert.ok(!content.includes('OPENROUTER_SENTINEL_DO_NOT_PERSIST'));
        assert.ok(!content.includes('GLOBAL_ROUTER_SECRET_DO_NOT_PERSIST'));
        assert.ok(!content.includes('MISTRAL_SENTINEL_DO_NOT_PERSIST'));
        assert.ok(!content.includes('LEGACY_SENTINEL_DO_NOT_PERSIST'));
        assert.ok(!content.includes('secret-password'));
        assert.ok(!content.includes('database-secret-literal'));
        assert.ok(!content.includes('secret-query'));
        assert.ok(!content.includes('INTERNAL_SERVICE_URL'));
    });

    it('forwards global URL settings instead of persisting embedded credentials', () => {
        __setConfigurationValue('assetAwareMcp.llmBackend', 'openrouter');
        __setConfigurationValue(
            'assetAwareMcp.openrouterBaseUrl',
            'https://router.internal/api/v1?token=router-secret-query',
        );

        assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv'), true);

        const content = fs.readFileSync(path.join(tempDir, 'config.toml'), 'utf-8');
        assert.ok(content.includes('"OPENROUTER_BASE_URL"'));
        assert.ok(!content.includes('OPENROUTER_BASE_URL ='));
        assert.ok(!content.includes('router-secret-query'));
    });

    it('forwards a credential-bearing global Ollama URL by name', () => {
        __setConfigurationValue('assetAwareMcp.llmBackend', 'ollama');
        __setConfigurationValue(
            'assetAwareMcp.ollamaHost',
            'http://ollama-user:ollama-password@ollama.internal:11434',
        );

        assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv'), true);
        const content = fs.readFileSync(path.join(tempDir, 'config.toml'), 'utf-8');
        assert.ok(content.includes('env_vars = ["OLLAMA_HOST"]'));
        assert.ok(!content.includes('OLLAMA_HOST ='));
        assert.ok(!content.includes('ollama-user'));
        assert.ok(!content.includes('ollama-password'));
    });

    it('writes a pinned package launch for a same-name workspace lookalike', () => {
        fs.mkdirSync(path.join(tempDir, 'src'), { recursive: true });
        fs.writeFileSync(path.join(tempDir, 'src', 'server.py'), 'raise SystemExit("untrusted")\n');
        fs.writeFileSync(path.join(tempDir, 'pyproject.toml'), '[project]\nname = "asset-aware-mcp"\n');
        fs.writeFileSync(path.join(tempDir, '.env'), [
            'DATA_DIR=/tmp/untrusted-data',
            'DOCLING_PYTHON_PATH=/tmp/untrusted-python',
            '',
        ].join('\n'));

        assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv'), true);

        const content = fs.readFileSync(path.join(tempDir, 'config.toml'), 'utf-8');
        const server = __test__.getSemanticServer(__test__.parseTomlConfig(content)!, 'asset-aware-mcp')!;
        assert.ok((server.args as string[]).includes('asset-aware-mcp==0.6.19'));
        assert.ok(!(server.args as string[]).includes('--directory'));
        assert.strictEqual(server.cwd, context.globalStorageUri.fsPath);
        assert.strictEqual((server.env as any).DATA_DIR, path.join(context.globalStorageUri.fsPath, 'data'));
        assert.strictEqual((server.env as any).DOCLING_PYTHON_PATH, undefined);
    });

    it('does not write Codex config from an untrusted workspace', () => {
        (vscode.workspace as any).isTrusted = false;

        assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv'), false);
        assert.strictEqual(fs.existsSync(path.join(tempDir, 'config.toml')), false);
    });

    it('forwards only credentials required by the selected backend and enabled OCR', () => {
        const source = {
            LLM_BACKEND: 'openrouter',
            OPENROUTER_API_KEY: 'router-secret',
            OPENAI_API_KEY: 'openai-secret',
            MISTRAL_API_KEY: 'mistral-secret',
            DATABASE_URL: 'postgresql://secret',
            ENABLE_MISTRAL_OCR: 'false',
        };

        assert.deepStrictEqual(__test__.buildCodexSafeEnv(source).envVars, ['OPENROUTER_API_KEY']);
        assert.deepStrictEqual(__test__.buildCodexSafeEnv({
            ...source,
            LLM_BACKEND: 'openai',
        }).envVars, ['OPENAI_API_KEY']);
        assert.deepStrictEqual(__test__.buildCodexSafeEnv({
            ...source,
            LLM_BACKEND: 'ollama',
            ENABLE_MISTRAL_OCR: 'true',
        }).envVars, ['MISTRAL_API_KEY']);
    });

    it('requires HTTPS for remote OpenRouter URLs while allowing loopback HTTP', () => {
        assert.strictEqual(__test__.isSafeOpenRouterUrl('https://router.example/api/v1'), true);
        assert.strictEqual(__test__.isSafeOpenRouterUrl('http://router.example/api/v1'), false);
        assert.strictEqual(__test__.isSafeOpenRouterUrl('http://localhost:8080/v1'), true);
        assert.strictEqual(__test__.isSafeOpenRouterUrl('http://127.0.0.2:8080/v1'), true);
        assert.strictEqual(__test__.isSafeOpenRouterUrl('http://[::1]:8080/v1'), true);
        assert.strictEqual(__test__.isSafeOllamaUrl('http://ollama.internal:11434'), true);

        const unsafe = __test__.buildCodexSafeEnv({
            LLM_BACKEND: 'openrouter',
            OPENROUTER_BASE_URL: 'http://router.example/api/v1',
        });
        assert.ok(!('OPENROUTER_BASE_URL' in unsafe.env));
        assert.ok(!unsafe.envVars.includes('OPENROUTER_BASE_URL'));

        const loopback = __test__.buildCodexSafeEnv({
            LLM_BACKEND: 'openrouter',
            OPENROUTER_BASE_URL: 'http://localhost:8080/v1',
        });
        assert.strictEqual(loopback.env.OPENROUTER_BASE_URL, 'http://localhost:8080/v1');
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

    for (const [label, custom] of [
        [
            'quoted table key',
            '[mcp_servers."asset-aware-mcp"]\ncommand = "quoted"\nargs = []\n',
        ],
        [
            'fully quoted table path',
            '["mcp_servers"."asset-aware-mcp"]\ncommand = "fully-quoted"\nargs = []\n',
        ],
        [
            'dotted assignments',
            'mcp_servers."asset-aware-mcp".command = "dotted"\nmcp_servers."asset-aware-mcp".args = []\n',
        ],
        [
            'inline same-name server',
            'mcp_servers."asset-aware-mcp" = { command = "inline", args = [] }\n',
        ],
        [
            'inline mcp_servers table',
            'mcp_servers = { "asset-aware-mcp" = { command = "root-inline", args = [] } }\n',
        ],
        [
            'non-table dotted value',
            'mcp_servers."asset-aware-mcp" = "reserved-by-user"\n',
        ],
    ] as const) {
        it(`preserves a custom same-name server expressed with ${label}`, () => {
            const configPath = path.join(tempDir, 'config.toml');
            fs.writeFileSync(configPath, custom);

            assert.strictEqual(__test__.hasSemanticServer(
                __test__.parseTomlConfig(custom)!,
                'asset-aware-mcp',
            ), true);
            assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv'), false);
            assert.strictEqual(removeCodexMcpServer(), false);
            assert.strictEqual(fs.readFileSync(configPath, 'utf-8'), custom);
        });
    }

    it('preserves a custom same-key executable even when its body names asset-aware-mcp', () => {
        const configPath = path.join(tempDir, 'config.toml');
        const custom = [
            '# user-owned local executable',
            '[mcp_servers.asset-aware-mcp]',
            'command = "/usr/local/bin/asset-aware-mcp"',
            'args = []',
            '',
        ].join('\n');
        fs.writeFileSync(configPath, custom);

        assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv'), false);
        assert.strictEqual(removeCodexMcpServer(), false);
        assert.strictEqual(fs.readFileSync(configPath, 'utf-8'), custom);
    });

    it('preserves a custom same-key source launch even when its body names src.server', () => {
        const configPath = path.join(tempDir, 'config.toml');
        const custom = [
            '# user-owned source checkout',
            '[mcp_servers.asset-aware-mcp]',
            'command = "/usr/bin/python3"',
            'args = ["-m", "src.server"]',
            '',
        ].join('\n');
        fs.writeFileSync(configPath, custom);

        assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv'), false);
        __setConfigurationValue('assetAwareMcp.manageCodexConfig', false);
        assert.strictEqual(removeCodexMcpServer(), false);
        assert.strictEqual(fs.readFileSync(configPath, 'utf-8'), custom);
    });

    it('does not treat a user comment with the managed prefix as ownership', () => {
        const configPath = path.join(tempDir, 'config.toml');
        const custom = [
            '# Managed by asset-aware-mcp VS Code extension. This is a user note, not an ownership marker.',
            '[mcp_servers.asset-aware-mcp]',
            'command = "custom-user-command"',
            'args = []',
            '',
        ].join('\n');
        fs.writeFileSync(configPath, custom);

        assert.strictEqual(__test__.isManagedMarkerLine(custom.split('\n')[0]), false);
        assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv'), false);
        assert.strictEqual(removeCodexMcpServer(), false);
        assert.strictEqual(fs.readFileSync(configPath, 'utf-8'), custom);
    });

    it('removes only the extension-managed block when Codex management is disabled', () => {
        fs.writeFileSync(path.join(tempDir, 'config.toml'), [
            '# user comment',
            '',
            '[mcp_servers.other]',
            'command = "node"',
            'args = ["server.js"]',
            '',
        ].join('\n'));
        assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv'), true);

        __setConfigurationValue('assetAwareMcp.manageCodexConfig', false);
        assert.strictEqual(isCodexAvailable(), false);
        assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv'), false);

        const content = fs.readFileSync(path.join(tempDir, 'config.toml'), 'utf-8');
        assert.ok(content.includes('# user comment'));
        assert.ok(content.includes('[mcp_servers.other]'));
        assert.ok(!content.includes('[mcp_servers.asset-aware-mcp]'));
    });

    it('does not remove a custom same-key block when Codex management is disabled', () => {
        fs.writeFileSync(path.join(tempDir, 'config.toml'), [
            '# custom Codex server owned by the user',
            '[mcp_servers.asset-aware-mcp]',
            'command = "custom"',
            'args = ["server"]',
            '',
        ].join('\n'));
        __setConfigurationValue('assetAwareMcp.manageCodexConfig', false);

        assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv'), false);

        const content = fs.readFileSync(path.join(tempDir, 'config.toml'), 'utf-8');
        assert.ok(content.includes('# custom Codex server owned by the user'));
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

    it('accepts legal multiline arrays and preserves their original formatting', () => {
        const configPath = path.join(tempDir, 'config.toml');
        const original = [
            '# intentionally formatted by the user',
            '[mcp_servers.other]',
            'command = "node"',
            'args = [',
            '    "server.js", # inline comment',
            '    "--stdio",',
            ']',
            '',
        ].join('\n');
        fs.writeFileSync(configPath, original);

        assert.strictEqual(__test__.hasSuspiciousTomlSyntax(original), false);
        assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv'), true);
        const first = fs.readFileSync(configPath, 'utf-8');
        assert.ok(first.startsWith(original));
        assert.deepStrictEqual(
            (__test__.parseTomlConfig(first)?.mcp_servers as any).other.args,
            ['server.js', '--stdio'],
        );
    });

    it('does not consume an unrelated table whose header has an inline comment', () => {
        const configPath = path.join(tempDir, 'config.toml');
        assert.strictEqual(installCodexMcpServer(context, '/old/uv'), true);
        fs.appendFileSync(configPath, [
            '',
            '[mcp_servers.other] # this comment is user-owned',
            'command = "node"',
            'args = ["server.js"]',
            '',
        ].join('\n'));

        assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv'), true);
        const updated = fs.readFileSync(configPath, 'utf-8');
        assert.ok(updated.includes('[mcp_servers.other] # this comment is user-owned'));
        assert.ok(updated.includes('command = "node"'));
        assert.strictEqual(removeCodexMcpServer(), true);
        const removed = fs.readFileSync(configPath, 'utf-8');
        assert.ok(removed.includes('[mcp_servers.other] # this comment is user-owned'));
        assert.ok(removed.includes('args = ["server.js"]'));
    });

    it('preserves user comments immediately before the next unrelated table', () => {
        const configPath = path.join(tempDir, 'config.toml');
        assert.strictEqual(installCodexMcpServer(context, '/old/uv'), true);
        fs.appendFileSync(configPath, [
            '',
            '# IMPORTANT USER COMMENT FOR OTHER',
            '[mcp_servers.other]',
            'command = "node"',
            '',
        ].join('\n'));

        assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv'), true);
        const updated = fs.readFileSync(configPath, 'utf-8');
        assert.ok(updated.includes('# IMPORTANT USER COMMENT FOR OTHER'));
        assert.ok(updated.includes('[mcp_servers.other]'));

        assert.strictEqual(removeCodexMcpServer(), true);
        const removed = fs.readFileSync(configPath, 'utf-8');
        assert.ok(removed.includes('# IMPORTANT USER COMMENT FOR OTHER'));
        assert.ok(removed.includes('command = "node"'));
    });

    it('preserves a user comment appended after a managed block at EOF', () => {
        const configPath = path.join(tempDir, 'config.toml');
        assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv'), true);
        fs.appendFileSync(configPath, '\n# USER EOF NOTE MUST SURVIVE\n');

        assert.strictEqual(removeCodexMcpServer(), true);
        const removed = fs.readFileSync(configPath, 'utf-8');
        assert.ok(removed.includes('# USER EOF NOTE MUST SURVIVE'));
        assert.ok(!removed.includes('[mcp_servers.asset-aware-mcp]'));
    });

    it('migrates a managed block twice with parser-valid stable env_vars', () => {
        const configPath = path.join(tempDir, 'config.toml');
        fs.writeFileSync(configPath, [
            '# user preface remains byte-for-byte',
            '',
            '# Managed by asset-aware-mcp VS Code extension. Remove this block to opt out.',
            '[mcp_servers.asset-aware-mcp]',
            'command = "/old/uv"',
            'args = [',
            '  "tool",',
            '  "run",',
            '  "asset-aware-mcp",',
            ']',
            'env_vars = [',
            '  "CUSTOM_TOKEN",',
            '  "HTTPS_PROXY",',
            '  "MISTRAL_API_KEY",',
            '  "OPENAI_API_KEY",',
            '  "OPENROUTER_API_KEY",',
            ']',
            '',
            '[mcp_servers.asset-aware-mcp.env]',
            'OPENAI_API_KEY = "LEGACY_SECRET_MUST_DISAPPEAR"',
            '',
        ].join('\n'));

        assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv'), true);
        const first = fs.readFileSync(configPath, 'utf-8');
        const firstParsed = __test__.parseTomlConfig(first);
        const firstServer = __test__.getSemanticServer(firstParsed!, 'asset-aware-mcp');
        assert.deepStrictEqual(firstServer?.env_vars, ['CUSTOM_TOKEN', 'HTTPS_PROXY']);
        assert.ok(!first.includes('LEGACY_SECRET_MUST_DISAPPEAR'));
        assert.ok(first.includes('# user preface remains byte-for-byte'));

        assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv'), false);
        const second = fs.readFileSync(configPath, 'utf-8');
        assert.strictEqual(second, first);
        const secondServer = __test__.getSemanticServer(
            __test__.parseTomlConfig(second)!,
            'asset-aware-mcp',
        );
        assert.deepStrictEqual(secondServer?.env_vars, ['CUSTOM_TOKEN', 'HTTPS_PROXY']);
    });

    it('preserves user primary policies and nested tool tables through install, update, and removal', () => {
        const configPath = path.join(tempDir, 'config.toml');
        const preservedPrimary = [
            '# USER PRIMARY POLICY TRIVIA MUST REMAIN',
            'required = true',
            'enabled_tools = [',
            '  "document", # keep this inline comment',
            '  "verify_citation_ref",',
            ']',
            'disabled_tools = ["delete_document"]',
            'default_tools_approval_mode = "prompt"',
            'future_policy = { mode = "strict", revision = 2 }',
            'future_multiline = """first line',
            'second line"""',
            '',
        ].join('\n');
        const preservedNested = [
            '# USER NESTED POLICY TRIVIA MUST REMAIN',
            '[mcp_servers.asset-aware-mcp.tools.document]',
            'approval_mode = "writes" # user policy',
            '',
            '[mcp_servers.asset-aware-mcp.tools.document.future]',
            'audit = { retain = true }',
            '',
            // A nested table must never be mistaken for the extension-owned
            // server env table. Its bytes remain user-owned, while the exact
            // `[...asset-aware-mcp.env]` table below is scrubbed and rebuilt.
            '[mcp_servers.asset-aware-mcp.tools.document.env]',
            'TOOL_POLICY_SENTINEL = "USER_NESTED_VALUE"',
            '',
        ].join('\n');
        const unrelated = [
            '[mcp_servers.other]',
            'command = "node"',
            'args = ["server.js"]',
            '',
        ].join('\n');
        fs.writeFileSync(configPath, [
            '# user preface',
            '',
            '# Managed by asset-aware-mcp VS Code extension. Set assetAwareMcp.manageCodexConfig=false to opt out.',
            '[mcp_servers.asset-aware-mcp]',
            'command = "/old/uv"',
            'args = [',
            '  "tool",',
            '  "run",',
            '  "asset-aware-mcp",',
            ']',
            'cwd = "/old/cwd"',
            'enabled = false',
            'startup_timeout_sec = 1',
            'tool_timeout_sec = 2',
            'env_vars = ["CUSTOM_FORWARD", "OPENAI_API_KEY"]',
            preservedPrimary,
            '[mcp_servers."asset-aware-mcp".env]',
            'OPENAI_API_KEY = "LEGACY_INLINE_SECRET_MUST_DISAPPEAR"',
            'ASSET_AWARE_DISABLE_DOTENV = "false"',
            '',
            preservedNested,
            unrelated,
        ].join('\n'));

        assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv'), true);
        const installed = fs.readFileSync(configPath, 'utf-8');
        const installedParsed = __test__.parseTomlConfig(installed)!;
        const installedServer = __test__.getSemanticServer(installedParsed, 'asset-aware-mcp')!;
        assert.strictEqual(installedServer.command, '/usr/bin/uv');
        assert.strictEqual(installedServer.required, true);
        assert.deepStrictEqual(installedServer.enabled_tools, ['document', 'verify_citation_ref']);
        assert.deepStrictEqual(installedServer.disabled_tools, ['delete_document']);
        assert.strictEqual(installedServer.default_tools_approval_mode, 'prompt');
        assert.deepStrictEqual(installedServer.future_policy, { mode: 'strict', revision: 2 });
        assert.strictEqual(installedServer.future_multiline, 'first line\nsecond line');
        assert.ok(installed.includes(preservedPrimary));
        assert.ok(installed.includes(preservedNested));
        assert.ok(installed.includes(unrelated));
        assert.ok(!installed.includes('LEGACY_INLINE_SECRET_MUST_DISAPPEAR'));
        assert.strictEqual((installedServer.env as any).ASSET_AWARE_DISABLE_DOTENV, 'true');
        assert.strictEqual((installedServer.env as any).TOOL_POLICY_SENTINEL, undefined);
        assert.strictEqual(
            (((installedServer.tools as any).document as any).env as any).TOOL_POLICY_SENTINEL,
            'USER_NESTED_VALUE',
        );

        assert.strictEqual(installCodexMcpServer(context, '/new/uv'), true);
        const updated = fs.readFileSync(configPath, 'utf-8');
        const updatedParsed = __test__.parseTomlConfig(updated)!;
        const updatedServer = __test__.getSemanticServer(updatedParsed, 'asset-aware-mcp')!;
        assert.strictEqual(updatedServer.command, '/new/uv');
        assert.ok(updated.includes(preservedPrimary));
        assert.ok(updated.includes(preservedNested));
        assert.ok(updated.includes(unrelated));
        assert.strictEqual(installCodexMcpServer(context, '/new/uv'), false);
        assert.strictEqual(fs.readFileSync(configPath, 'utf-8'), updated);

        assert.strictEqual(removeCodexMcpServer(), true);
        const removed = fs.readFileSync(configPath, 'utf-8');
        const removedParsed = __test__.parseTomlConfig(removed)!;
        const removedServer = __test__.getSemanticServer(removedParsed, 'asset-aware-mcp')!;
        assert.strictEqual(removedServer.command, 'asset-aware-mcp-management-disabled');
        assert.deepStrictEqual(removedServer.args, []);
        assert.strictEqual(removedServer.cwd, undefined);
        assert.strictEqual(removedServer.enabled, false);
        assert.strictEqual(removedServer.env_vars, undefined);
        assert.strictEqual(removedServer.env, undefined);
        assert.strictEqual(removedServer.required, true);
        assert.deepStrictEqual(removedServer.enabled_tools, ['document', 'verify_citation_ref']);
        assert.deepStrictEqual(removedServer.disabled_tools, ['delete_document']);
        assert.strictEqual(removedServer.default_tools_approval_mode, 'prompt');
        assert.ok(removed.includes(preservedPrimary));
        assert.ok(removed.includes(preservedNested));
        assert.ok(removed.includes(unrelated));
        assert.ok(!removed.includes('Managed by asset-aware-mcp VS Code extension'));
        assert.ok(removed.includes('Asset-Aware MCP launch disabled after management opt-out'));

        __setConfigurationValue('assetAwareMcp.manageCodexConfig', true);
        assert.strictEqual(installCodexMcpServer(context, '/re-enabled/uv'), true);
        const reenabled = fs.readFileSync(configPath, 'utf-8');
        const reenabledServer = __test__.getSemanticServer(
            __test__.parseTomlConfig(reenabled)!,
            'asset-aware-mcp',
        )!;
        assert.strictEqual(reenabledServer.command, '/re-enabled/uv');
        assert.strictEqual(reenabledServer.enabled, true);
        assert.strictEqual(reenabledServer.required, true);
        assert.ok(reenabled.includes(preservedPrimary));
        assert.ok(reenabled.includes(preservedNested));
        assert.ok(!reenabled.includes('management opt-out'));
    });

    it('fails closed without replacing or following a symlinked config', function () {
        if (process.platform === 'win32') {
            this.skip();
        }
        const targetPath = path.join(tempDir, 'real-config.toml');
        const configPath = path.join(tempDir, 'config.toml');
        const original = '[mcp_servers.other]\ncommand = "keep"\n';
        fs.writeFileSync(targetPath, original);
        fs.symlinkSync(targetPath, configPath);

        assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv'), false);
        assert.strictEqual(removeCodexMcpServer(), false);
        assert.strictEqual(fs.lstatSync(configPath).isSymbolicLink(), true);
        assert.strictEqual(fs.readFileSync(targetPath, 'utf-8'), original);
    });

    it('cleans its private temporary file when atomic rename fails', () => {
        const invalidTarget = path.join(tempDir, 'config-as-directory.toml');
        fs.mkdirSync(invalidTarget);

        assert.throws(() => __test__.writeConfigAtomic(invalidTarget, 'key = "value"\n'));
        const leftovers = fs.readdirSync(tempDir).filter((name) =>
            name.startsWith('config-as-directory.toml.tmp.'),
        );
        assert.deepStrictEqual(leftovers, []);
    });

    it('fails closed when a regular config changes before atomic replacement', () => {
        const configPath = path.join(tempDir, 'config.toml');
        const original = '[mcp_servers.other]\ncommand = "one"\n';
        const concurrent = '[mcp_servers.other]\ncommand = "two"\n# CONCURRENT USER EDIT\n';
        fs.writeFileSync(configPath, original);
        // Patch the underlying CommonJS module rather than TypeScript's
        // read-only namespace wrapper.
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const mutableFs: any = require('fs');
        const originalWriteFileSync = mutableFs.writeFileSync;
        let injected = false;
        mutableFs.writeFileSync = (...args: any[]) => {
            const result = originalWriteFileSync(...args);
            if (!injected && String(args[0]).includes('.tmp.')) {
                injected = true;
                originalWriteFileSync(configPath, concurrent, 'utf-8');
            }
            return result;
        };

        try {
            assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv'), false);
        } finally {
            mutableFs.writeFileSync = originalWriteFileSync;
        }

        assert.strictEqual(injected, true);
        assert.strictEqual(fs.readFileSync(configPath, 'utf-8'), concurrent);
        assert.deepStrictEqual(
            fs.readdirSync(tempDir).filter((name) => name.startsWith('config.toml.tmp.')),
            [],
        );
    });

    it('retains one private recovery snapshot for late writes through an old open file descriptor', function () {
        const configPath = path.join(tempDir, 'config.toml');
        const original = '[mcp_servers.other]\ncommand = "original"\n';
        const lateEdit = '# LATE EDIT THROUGH OLD FD\n[mcp_servers.other]\ncommand = "late"\n';
        fs.writeFileSync(configPath, original);
        const oldFd = fs.openSync(configPath, 'r+');

        try {
            assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv'), true);

            // The descriptor still refers to the inode that was atomically
            // claimed as the recovery snapshot, even though config.toml now
            // names the newly rendered managed config.
            fs.ftruncateSync(oldFd, 0);
            fs.writeSync(oldFd, lateEdit, 0, 'utf-8');
            fs.fsyncSync(oldFd);
        } finally {
            fs.closeSync(oldFd);
        }

        const config = fs.readFileSync(configPath, 'utf-8');
        assert.ok(config.includes('[mcp_servers.asset-aware-mcp]'));
        assert.ok(config.includes('command = "original"'));
        assert.ok(!config.includes('LATE EDIT THROUGH OLD FD'));

        const recoveryNames = fs.readdirSync(tempDir).filter((name) =>
            name.startsWith('config.toml.concurrent-backup.'),
        );
        assert.strictEqual(recoveryNames.length, 1);
        const recoveryPath = path.join(tempDir, recoveryNames[0]);
        assert.strictEqual(fs.readFileSync(recoveryPath, 'utf-8'), lateEdit);
        if (process.platform !== 'win32') {
            assert.strictEqual(fs.statSync(recoveryPath).mode & 0o777, 0o600);
        }

        assert.strictEqual(installCodexMcpServer(context, '/usr/bin/uv'), false);
        assert.deepStrictEqual(
            fs.readdirSync(tempDir).filter((name) =>
                name.startsWith('config.toml.concurrent-backup.'),
            ),
            recoveryNames,
        );
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
