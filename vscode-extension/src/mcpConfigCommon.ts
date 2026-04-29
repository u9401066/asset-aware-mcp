import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';
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

export function buildAssetAwareEnv(
    context: vscode.ExtensionContext,
    workspaceRoot: string | undefined = getPrimaryWorkspaceRoot(),
): Record<string, string> {
    const config = vscode.workspace.getConfiguration('assetAwareMcp');
    const baseRoot = workspaceRoot ?? context.globalStorageUri.fsPath;
    const envVars: Record<string, string> = {
        LLM_BACKEND: config.get('llmBackend', 'ollama'),
        OLLAMA_HOST: config.get('ollamaHost', 'http://localhost:11434'),
        OLLAMA_MODEL: config.get('ollamaModel', 'qwen2.5:7b'),
        OLLAMA_EMBEDDING_MODEL: config.get('ollamaEmbeddingModel', 'nomic-embed-text'),
        ENABLE_LIGHTRAG: 'true',
    };

    const openaiKey = config.get<string>('openaiApiKey', '');
    if (openaiKey) {
        envVars['OPENAI_API_KEY'] = openaiKey;
        envVars['OPENAI_MODEL'] = config.get('openaiModel', 'gpt-4o-mini');
        envVars['LIGHTRAG_EMBEDDING_MODEL'] = config.get('openaiEmbeddingModel', 'text-embedding-3-small');
    }

    if (workspaceRoot) {
        Object.assign(envVars, parseEnvFile(path.join(workspaceRoot, '.env')));
        normalizeEmbeddingEnv(envVars);
    }

    const dataDir = envVars['DATA_DIR'] || config.get<string>('dataDir', './data');
    envVars['DATA_DIR'] = path.isAbsolute(dataDir) ? dataDir : path.resolve(baseRoot, dataDir);

    return envVars;
}

export function buildAssetAwareLaunchSpec(
    context: vscode.ExtensionContext,
    uvPath: string,
    options: { workspaceRoot?: string; needsUpgrade?: boolean } = {},
): AssetAwareLaunchSpec {
    const workspaceRoot = options.workspaceRoot ?? getPrimaryWorkspaceRoot();
    const localSource = findLocalAssetAwareSource(workspaceRoot, workspaceRoot);
    const env = buildAssetAwareEnv(context, workspaceRoot);

    if (localSource) {
        return {
            command: uvPath,
            args: [
                ...getUvRunArgs(PREFERRED_RUNTIME_PYTHON),
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

    const config = vscode.workspace.getConfiguration('assetAwareMcp');
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
