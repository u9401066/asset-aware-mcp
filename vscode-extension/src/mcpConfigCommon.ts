import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';
import {
    booleanEnv,
    DEFAULT_DATA_DIR,
    DEFAULT_ENABLE_LIGHTRAG,
    DEFAULT_LLM_BACKEND,
    DEFAULT_MCP_IMAGE_RESPONSE_CHARS,
    DEFAULT_MCP_TEXT_RESPONSE_CHARS,
    DEFAULT_OLLAMA_EMBEDDING_MODEL,
    DEFAULT_OLLAMA_HOST,
    DEFAULT_OPENROUTER_BASE_URL,
    DEFAULT_OPENROUTER_MODEL,
    DEFAULT_SECTION_TREE_LOAD_MAX_BYTES,
    DEFAULT_SEGMENTATION_SOURCE_LOAD_MAX_BYTES,
    DEFAULT_TABLE_STARTUP_LOAD_MAX_BYTES,
    defaultOllamaModelForHardware,
} from './defaults';
import {
    DEFAULT_TORCH_BACKEND,
    getUvRunArgs,
    getUvxLaunch,
    PREFERRED_RUNTIME_PYTHON,
} from './uv';

export const ASSET_AWARE_SERVER_KEY = 'asset-aware-mcp';

export interface AssetAwareLaunchSpec {
    command: string;
    args: string[];
    env: Record<string, string>;
    mode: 'local' | 'package';
}

export function getPrimaryWorkspaceRoot(): string | undefined {
    return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
}

export function parseEnvFile(envPath: string): Record<string, string> {
    const env: Record<string, string> = {};
    if (!fs.existsSync(envPath)) {
        return env;
    }

    const lines = fs.readFileSync(envPath, 'utf-8').split(/\r?\n/);
    for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('#')) {
            continue;
        }
        const eqIndex = trimmed.indexOf('=');
        if (eqIndex <= 0) {
            continue;
        }

        const key = trimmed.slice(0, eqIndex).trim();
        let value = trimmed.slice(eqIndex + 1).trim();
        if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
            value = value.slice(1, -1);
        }
        env[key] = value;
    }

    return env;
}

export function normalizeEmbeddingEnv(envVars: Record<string, string>): void {
    const canonical = envVars['LIGHTRAG_EMBEDDING_MODEL'];
    const legacy = envVars['OPENAI_EMBEDDING_MODEL'];
    if (!canonical && legacy) {
        envVars['LIGHTRAG_EMBEDDING_MODEL'] = legacy;
    }
    if (canonical && !legacy) {
        envVars['OPENAI_EMBEDDING_MODEL'] = canonical;
    }
}

function clampSafetyLimitEnv(envVars: Record<string, string>, key: string, value: string): void {
    const fallback = Number(value);
    const raw = envVars[key]?.trim();
    const parsed = raw ? Number(raw) : NaN;
    if (!Number.isInteger(parsed) || parsed < 1 || parsed > fallback) {
        envVars[key] = value;
        return;
    }
    envVars[key] = String(parsed);
}

export function findLocalAssetAwareSource(workspaceRoot?: string, fallbackRoot?: string): string | undefined {
    const possiblePaths = Array.from(
        new Set(
            [
                workspaceRoot,
                workspaceRoot ? path.join(workspaceRoot, 'mcp-server') : undefined,
                workspaceRoot ? path.join(workspaceRoot, 'asset-aware-mcp') : undefined,
                workspaceRoot ? path.dirname(workspaceRoot) : undefined,
                fallbackRoot,
            ].filter((candidate): candidate is string => Boolean(candidate))
        )
    );

    for (const basePath of possiblePaths) {
        const serverPath = path.join(basePath, 'src', 'server.py');
        const pyprojectPath = path.join(basePath, 'pyproject.toml');
        if (!fs.existsSync(serverPath) || !fs.existsSync(pyprojectPath)) {
            continue;
        }

        try {
            const pyproject = fs.readFileSync(pyprojectPath, 'utf-8');
            if (pyproject.includes('name = "asset-aware-mcp"')) {
                return basePath;
            }
        } catch {
            // Try the next candidate.
        }
    }

    return undefined;
}

function configuredOllamaModel(config: vscode.WorkspaceConfiguration): string {
    const inspected = config.inspect<string>('ollamaModel');
    const explicitValues = inspected
        ? [
            inspected.globalValue,
            inspected.workspaceValue,
            inspected.workspaceFolderValue,
            inspected.globalLanguageValue,
            inspected.workspaceLanguageValue,
            inspected.workspaceFolderLanguageValue,
        ]
        : [];
    if (explicitValues.some(value => typeof value === 'string' && value.trim() !== '')) {
        return config.get('ollamaModel', defaultOllamaModelForHardware());
    }
    return defaultOllamaModelForHardware();
}

function configuredString(
    config: vscode.WorkspaceConfiguration,
    key: string,
    fallback: string,
): string | undefined {
    const inspected = config.inspect<string>(key);
    const explicitValues = inspected
        ? [
            inspected.globalValue,
            inspected.workspaceValue,
            inspected.workspaceFolderValue,
            inspected.globalLanguageValue,
            inspected.workspaceLanguageValue,
            inspected.workspaceFolderLanguageValue,
        ]
        : [];
    if (explicitValues.some(value => typeof value === 'string' && value.trim() !== '')) {
        return config.get(key, fallback);
    }
    return undefined;
}

export function buildAssetAwareEnv(
    context: vscode.ExtensionContext,
    workspaceRoot: string | undefined = getPrimaryWorkspaceRoot(),
): Record<string, string> {
    const config = vscode.workspace.getConfiguration('assetAwareMcp');
    const baseRoot = workspaceRoot ?? context.globalStorageUri.fsPath;
    const envVars: Record<string, string> = {
        LLM_BACKEND: config.get('llmBackend', DEFAULT_LLM_BACKEND),
        OLLAMA_HOST: config.get('ollamaHost', DEFAULT_OLLAMA_HOST),
        OLLAMA_MODEL: configuredOllamaModel(config),
        OLLAMA_EMBEDDING_MODEL: config.get('ollamaEmbeddingModel', DEFAULT_OLLAMA_EMBEDDING_MODEL),
        ENABLE_LIGHTRAG: booleanEnv(config.get('enableLightRag', DEFAULT_ENABLE_LIGHTRAG)),
    };

    const openaiKey = config.get<string>('openaiApiKey', '');
    if (openaiKey) {
        envVars['OPENAI_API_KEY'] = openaiKey;
        envVars['OPENAI_MODEL'] = config.get('openaiModel', 'gpt-4o-mini');
        envVars['LIGHTRAG_EMBEDDING_MODEL'] = config.get('openaiEmbeddingModel', 'text-embedding-3-small');
    }
    const openrouterKey = config.get<string>('openrouterApiKey', '');
    if (openrouterKey) {
        envVars['OPENROUTER_API_KEY'] = openrouterKey;
    }
    const openrouterBaseUrl = configuredString(config, 'openrouterBaseUrl', DEFAULT_OPENROUTER_BASE_URL);
    if (openrouterBaseUrl) {
        envVars['OPENROUTER_BASE_URL'] = openrouterBaseUrl;
    }
    const openrouterModel = configuredString(config, 'openrouterModel', DEFAULT_OPENROUTER_MODEL);
    if (openrouterModel) {
        envVars['OPENROUTER_MODEL'] = openrouterModel;
    }

    if (workspaceRoot) {
        Object.assign(envVars, parseEnvFile(path.join(workspaceRoot, '.env')));
        normalizeEmbeddingEnv(envVars);
    }

    const dataDir = envVars['DATA_DIR'] || config.get<string>('dataDir', DEFAULT_DATA_DIR);
    envVars['DATA_DIR'] = path.isAbsolute(dataDir) ? dataDir : path.resolve(baseRoot, dataDir);
    const uvCacheDir = envVars['UV_CACHE_DIR'] || path.join(envVars['DATA_DIR'], '.uv-cache');
    envVars['UV_CACHE_DIR'] = path.isAbsolute(uvCacheDir)
        ? uvCacheDir
        : path.resolve(baseRoot, uvCacheDir);
    envVars['ASSET_AWARE_SUPPRESS_MARKER_OUTPUT'] =
        envVars['ASSET_AWARE_SUPPRESS_MARKER_OUTPUT'] ?? 'true';
    envVars['ASSET_AWARE_MARKER_OUTPUT_LOG'] =
        envVars['ASSET_AWARE_MARKER_OUTPUT_LOG'] ?? path.join(envVars['DATA_DIR'], 'logs', 'marker.log');
    clampSafetyLimitEnv(envVars, 'ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS', DEFAULT_MCP_TEXT_RESPONSE_CHARS);
    clampSafetyLimitEnv(envVars, 'ASSET_AWARE_MCP_IMAGE_RESPONSE_CHARS', DEFAULT_MCP_IMAGE_RESPONSE_CHARS);
    clampSafetyLimitEnv(envVars, 'ASSET_AWARE_TABLE_STARTUP_LOAD_MAX_BYTES', DEFAULT_TABLE_STARTUP_LOAD_MAX_BYTES);
    clampSafetyLimitEnv(envVars, 'ASSET_AWARE_SECTION_TREE_LOAD_MAX_BYTES', DEFAULT_SECTION_TREE_LOAD_MAX_BYTES);
    clampSafetyLimitEnv(envVars, 'ASSET_AWARE_SEGMENTATION_SOURCE_LOAD_MAX_BYTES', DEFAULT_SEGMENTATION_SOURCE_LOAD_MAX_BYTES);

    return envVars;
}

export function buildAssetAwareLaunchSpec(
    context: vscode.ExtensionContext,
    uvPath: string,
    options: { workspaceRoot?: string; needsUpgrade?: boolean } = {},
): AssetAwareLaunchSpec {
    const workspaceRoot = options.workspaceRoot ?? getPrimaryWorkspaceRoot();
    const localSource = findLocalAssetAwareSource(workspaceRoot, workspaceRoot);
    const envRoot = localSource ?? workspaceRoot;
    const env = buildAssetAwareEnv(context, envRoot);
    const config = vscode.workspace.getConfiguration('assetAwareMcp');

    if (localSource) {
        return {
            command: uvPath,
            args: [
                ...getUvRunArgs(
                    PREFERRED_RUNTIME_PYTHON,
                    config.get('enableMarkerBackend', false),
                ),
                '--directory',
                localSource,
                'python',
                '-m',
                'src.server',
            ],
            env,
            mode: 'local',
        };
    }

    const serverVersion = context.extension?.packageJSON?.version as string | undefined;
    const launch = getUvxLaunch(
        uvPath,
        PREFERRED_RUNTIME_PYTHON,
        config.get('enableMarkerBackend', false),
        config.get('torchBackend', DEFAULT_TORCH_BACKEND),
        serverVersion,
        options.needsUpgrade ?? false,
    );

    return {
        command: launch.command,
        args: [...launch.args, ASSET_AWARE_SERVER_KEY],
        env,
        mode: 'package',
    };
}

export function isAssetAwareLaunch(command: string | undefined, args: unknown): boolean {
    const argList = Array.isArray(args) ? args.map(String) : [];
    const commandText = command ?? '';
    return commandText.includes(ASSET_AWARE_SERVER_KEY)
        || argList.includes(ASSET_AWARE_SERVER_KEY)
        || argList.includes('src.server')
        || argList.some((arg) => arg.includes(`${ASSET_AWARE_SERVER_KEY}==`));
}

export function entriesEqual(a: unknown, b: unknown): boolean {
    return JSON.stringify(a) === JSON.stringify(b);
}

export function mergeManagedEnv(
    existing: Record<string, string> | undefined,
    next: Record<string, string> | undefined,
): Record<string, string> | undefined {
    const merged = {
        ...(existing ?? {}),
        ...(next ?? {}),
    };
    return Object.keys(merged).length > 0 ? merged : undefined;
}
