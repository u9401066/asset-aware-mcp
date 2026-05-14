export const DEFAULT_LLM_BACKEND = 'ollama';
export const DEFAULT_OLLAMA_HOST = 'http://localhost:11434';
export const DEFAULT_OLLAMA_MODEL = 'granite4.1';
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
