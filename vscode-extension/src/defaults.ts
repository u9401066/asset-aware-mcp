export const DEFAULT_LLM_BACKEND = 'ollama';
export const DEFAULT_OLLAMA_HOST = 'http://localhost:11434';
export const DEFAULT_OLLAMA_CPU_MODEL = 'granite4.1:3b';
export const DEFAULT_OLLAMA_GPU_MODEL = 'granite4.1:8b';
export const DEFAULT_OLLAMA_MODEL = DEFAULT_OLLAMA_CPU_MODEL;
export const DEFAULT_OLLAMA_EMBEDDING_MODEL = 'nomic-embed-text';
export const DEFAULT_OPENAI_MODEL = 'gpt-4o-mini';
export const DEFAULT_LIGHTRAG_EMBEDDING_MODEL = 'text-embedding-3-small';
export const DEFAULT_DATA_DIR = './data';
export const DEFAULT_LIGHTRAG_WORKING_DIR = './data/lightrag_db';
export const DEFAULT_ETL_PROFILE = 'default';
export const DEFAULT_ENABLE_LIGHTRAG = false;

export function envBoolean(value: string | undefined, fallback: boolean): boolean {
    if (value === undefined || value.trim() === '') {
        return fallback;
    }
    const normalized = value.trim().toLowerCase();
    return normalized === '1' || normalized === 'true' || normalized === 'yes' || normalized === 'on';
}

export function booleanEnv(value: boolean): 'true' | 'false' {
    return value ? 'true' : 'false';
}

const GPU_MODEL_HINT_ENV_VARS = [
    'ASSET_AWARE_HAS_GPU',
    'ASSET_AWARE_USE_GPU',
    'ASSET_AWARE_GPU',
];
const GPU_VISIBLE_DEVICE_ENV_VARS = [
    'NVIDIA_VISIBLE_DEVICES',
    'CUDA_VISIBLE_DEVICES',
];
const TRUE_ENV_VALUES = new Set(['1', 'true', 'yes', 'on']);
const FALSE_ENV_VALUES = new Set(['0', 'false', 'no', 'off', 'none', 'void', '-1']);

function normalizedEnvValue(value: string | undefined): string {
    return (value ?? '').trim().toLowerCase();
}

export function envPrefersGpuModel(env: NodeJS.ProcessEnv = process.env): boolean {
    for (const key of GPU_MODEL_HINT_ENV_VARS) {
        const value = normalizedEnvValue(env[key]);
        if (TRUE_ENV_VALUES.has(value)) {
            return true;
        }
        if (FALSE_ENV_VALUES.has(value)) {
            return false;
        }
    }

    for (const key of GPU_VISIBLE_DEVICE_ENV_VARS) {
        const value = normalizedEnvValue(env[key]);
        if (value && !FALSE_ENV_VALUES.has(value)) {
            return true;
        }
    }
    return false;
}

export function defaultOllamaModelForHardware(env: NodeJS.ProcessEnv = process.env): string {
    return envPrefersGpuModel(env) ? DEFAULT_OLLAMA_GPU_MODEL : DEFAULT_OLLAMA_CPU_MODEL;
}
