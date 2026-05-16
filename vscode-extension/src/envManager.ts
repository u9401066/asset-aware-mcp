/**
 * Environment File Manager
 *
 * Handles reading and writing .env configuration files.
 * Provides type-safe access to environment variables.
 */

import * as fs from 'fs';
import * as path from 'path';
import {
    booleanEnv,
    DEFAULT_DATA_DIR,
    DEFAULT_ENABLE_LIGHTRAG,
    DEFAULT_ETL_PROFILE,
    DEFAULT_LIGHTRAG_EMBEDDING_MODEL,
    DEFAULT_LIGHTRAG_WORKING_DIR,
    DEFAULT_LLM_BACKEND,
    DEFAULT_MCP_IMAGE_RESPONSE_CHARS,
    DEFAULT_MCP_TEXT_RESPONSE_CHARS,
    DEFAULT_OLLAMA_EMBEDDING_MODEL,
    DEFAULT_OLLAMA_HOST,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_OPENROUTER_BASE_URL,
    DEFAULT_OPENROUTER_MODEL,
    DEFAULT_SECTION_TREE_LOAD_MAX_BYTES,
    DEFAULT_SEGMENTATION_SOURCE_LOAD_MAX_BYTES,
    DEFAULT_TABLE_STARTUP_LOAD_MAX_BYTES,
    defaultOllamaModelForHardware,
} from './defaults';

export interface EnvConfig {
    LLM_BACKEND?: string;
    OLLAMA_HOST?: string;
    OLLAMA_MODEL?: string;
    OLLAMA_EMBEDDING_MODEL?: string;
    OPENAI_API_KEY?: string;
    OPENAI_MODEL?: string;
    OPENROUTER_API_KEY?: string;
    OPENROUTER_BASE_URL?: string;
    OPENROUTER_MODEL?: string;
    LIGHTRAG_EMBEDDING_MODEL?: string;
    /** Legacy alias retained when reading older .env files. */
    OPENAI_EMBEDDING_MODEL?: string;
    DATA_DIR?: string;
    LIGHTRAG_WORKING_DIR?: string;
    LIGHTRAG_DIR?: string;
    ETL_PROFILE?: string;
    ENABLE_LIGHTRAG?: string;
    ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS?: string;
    ASSET_AWARE_MCP_IMAGE_RESPONSE_CHARS?: string;
    ASSET_AWARE_TABLE_STARTUP_LOAD_MAX_BYTES?: string;
    ASSET_AWARE_SECTION_TREE_LOAD_MAX_BYTES?: string;
    ASSET_AWARE_SEGMENTATION_SOURCE_LOAD_MAX_BYTES?: string;
    [key: string]: string | undefined;
}

export interface DocumentArtifact {
    id: string;
    label: string;
    kind: string;
    path: string;
    icon: string;
}

export interface CitationSpanSummary {
    spanId: string;
    label: string;
    description: string;
    quote: string;
    path: string;
    line: number;
}

function defaultEnv(): EnvConfig {
    return {
        LLM_BACKEND: DEFAULT_LLM_BACKEND,
        OLLAMA_HOST: DEFAULT_OLLAMA_HOST,
        OLLAMA_MODEL: defaultOllamaModelForHardware(),
        OLLAMA_EMBEDDING_MODEL: DEFAULT_OLLAMA_EMBEDDING_MODEL,
        OPENAI_API_KEY: '',
        OPENAI_MODEL: DEFAULT_OPENAI_MODEL,
        OPENROUTER_API_KEY: '',
        OPENROUTER_BASE_URL: DEFAULT_OPENROUTER_BASE_URL,
        OPENROUTER_MODEL: DEFAULT_OPENROUTER_MODEL,
        LIGHTRAG_EMBEDDING_MODEL: DEFAULT_LIGHTRAG_EMBEDDING_MODEL,
        DATA_DIR: DEFAULT_DATA_DIR,
        LIGHTRAG_WORKING_DIR: DEFAULT_LIGHTRAG_WORKING_DIR,
        ETL_PROFILE: DEFAULT_ETL_PROFILE,
        ENABLE_LIGHTRAG: booleanEnv(DEFAULT_ENABLE_LIGHTRAG),
        ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS: DEFAULT_MCP_TEXT_RESPONSE_CHARS,
        ASSET_AWARE_MCP_IMAGE_RESPONSE_CHARS: DEFAULT_MCP_IMAGE_RESPONSE_CHARS,
        ASSET_AWARE_TABLE_STARTUP_LOAD_MAX_BYTES: DEFAULT_TABLE_STARTUP_LOAD_MAX_BYTES,
        ASSET_AWARE_SECTION_TREE_LOAD_MAX_BYTES: DEFAULT_SECTION_TREE_LOAD_MAX_BYTES,
        ASSET_AWARE_SEGMENTATION_SOURCE_LOAD_MAX_BYTES: DEFAULT_SEGMENTATION_SOURCE_LOAD_MAX_BYTES,
    };
}

export class EnvManager {
    private workspaceRoot: string;
    private projectRoot: string;
    private envPath: string;

    constructor(workspaceRoot: string) {
        this.workspaceRoot = workspaceRoot;
        this.projectRoot = this.findProjectRoot(workspaceRoot);
        this.envPath = path.join(this.projectRoot, '.env');
    }

    /**
     * Find the project root by looking for pyproject.toml or src/server.py
     */
    private findProjectRoot(startPath: string): string {
        let current = startPath;
        const root = path.parse(current).root;

        while (current !== root) {
            if (fs.existsSync(path.join(current, 'pyproject.toml')) ||
                fs.existsSync(path.join(current, 'src', 'server.py'))) {
                return current;
            }
            current = path.dirname(current);
        }

        return startPath;
    }

    /**
     * Get the path to the .env file
     */
    getEnvPath(): string {
        return this.envPath;
    }

    /**
     * Get the manifest path for a document, supporting both legacy and current layouts.
     */
    getManifestPath(docId: string): string | null {
        return this.findManifestPath(path.join(this.getDataDir(), docId), docId);
    }

    /**
     * Check if .env file exists
     */
    exists(): boolean {
        return fs.existsSync(this.envPath);
    }

    /**
     * Read and parse .env file
     */
    async readEnv(): Promise<EnvConfig> {
        if (!this.exists()) {
            return defaultEnv();
        }

        try {
            const content = fs.readFileSync(this.envPath, 'utf-8');
            return this.parseEnvContent(content);
        } catch (error) {
            console.error('Error reading .env file:', error);
            return defaultEnv();
        }
    }

    /**
     * Parse .env content to object
     */
    private parseEnvContent(content: string): EnvConfig {
        const env: EnvConfig = defaultEnv();
        const explicitKeys = new Set<string>();
        const lines = content.split('\n');

        for (const line of lines) {
            const trimmed = line.trim();

            // Skip empty lines and comments
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
                explicitKeys.add(key);
            }
        }

        if (!explicitKeys.has('LIGHTRAG_EMBEDDING_MODEL') && env.OPENAI_EMBEDDING_MODEL) {
            env.LIGHTRAG_EMBEDDING_MODEL = env.OPENAI_EMBEDDING_MODEL;
        }
        if (!env.OPENAI_EMBEDDING_MODEL && env.LIGHTRAG_EMBEDDING_MODEL) {
            env.OPENAI_EMBEDDING_MODEL = env.LIGHTRAG_EMBEDDING_MODEL;
        }

        return env;
    }

    /**
     * Create default .env file
     */
    async createDefaultEnv(): Promise<void> {
        const content = this.generateEnvContent(defaultEnv());
        fs.mkdirSync(path.dirname(this.envPath), { recursive: true });
        fs.writeFileSync(this.envPath, content, 'utf-8');
    }

    /**
     * Update a single environment variable
     */
    async updateEnv(key: string, value: string): Promise<void> {
        const env = await this.readEnv();
        env[key] = value;
        await this.writeEnv(env);
    }

    /**
     * Write entire env config to file
     */
    async writeEnv(env: EnvConfig): Promise<void> {
        const content = this.generateEnvContent(env);
        fs.mkdirSync(path.dirname(this.envPath), { recursive: true });
        fs.writeFileSync(this.envPath, content, 'utf-8');
    }

    private findManifestPath(docPath: string, docId: string): string | null {
        const candidates = [
            path.join(docPath, `${docId}_manifest.json`),
            path.join(docPath, 'manifest.json'),
        ];

        for (const candidate of candidates) {
            if (fs.existsSync(candidate)) {
                return candidate;
            }
        }

        return null;
    }

    /**
     * Generate .env file content from config
     */
    private generateEnvContent(env: EnvConfig): string {
        const lines: string[] = [
            '# Asset-Aware MCP Configuration',
            '# Generated by VS Code Extension',
            '',
            '# ============================================',
            '# LLM Backend Selection',
            '# ============================================',
            '# Options: "ollama" (local) or "openai" (cloud)',
            `LLM_BACKEND=${env.LLM_BACKEND || DEFAULT_LLM_BACKEND}`,
            '',
            '# ============================================',
            '# ETL Profile (Document Extraction Settings)',
            '# ============================================',
            '# Options: "default", "arxiv", "nature", "ieee", "elsevier"',
            `ETL_PROFILE=${env.ETL_PROFILE || DEFAULT_ETL_PROFILE}`,
            '',
            '# ============================================',
            '# Ollama Settings (for local LLM)',
            '# ============================================',
            `OLLAMA_HOST=${env.OLLAMA_HOST || DEFAULT_OLLAMA_HOST}`,
            `OLLAMA_MODEL=${env.OLLAMA_MODEL || defaultOllamaModelForHardware()}`,
            `OLLAMA_EMBEDDING_MODEL=${env.OLLAMA_EMBEDDING_MODEL || DEFAULT_OLLAMA_EMBEDDING_MODEL}`,
            '',
            '# ============================================',
            '# OpenAI Settings (for cloud LLM)',
            '# ============================================',
            `OPENAI_API_KEY=${env.OPENAI_API_KEY || ''}`,
            `OPENAI_MODEL=${env.OPENAI_MODEL || DEFAULT_OPENAI_MODEL}`,
            `LIGHTRAG_EMBEDDING_MODEL=${env.LIGHTRAG_EMBEDDING_MODEL || env.OPENAI_EMBEDDING_MODEL || DEFAULT_LIGHTRAG_EMBEDDING_MODEL}`,
            '',
            '# ============================================',
            '# OpenRouter Settings (optional fast/free preset)',
            '# ============================================',
            '# Use LLM_BACKEND=openrouter for low-cost summaries and draft RAG answers.',
            '# OpenRouter generation still uses OLLAMA_EMBEDDING_MODEL for LightRAG retrieval.',
            `OPENROUTER_API_KEY=${env.OPENROUTER_API_KEY || ''}`,
            `OPENROUTER_BASE_URL=${env.OPENROUTER_BASE_URL || DEFAULT_OPENROUTER_BASE_URL}`,
            `OPENROUTER_MODEL=${env.OPENROUTER_MODEL || DEFAULT_OPENROUTER_MODEL}`,
            '',
            '# ============================================',
            '# Storage Settings',
            '# ============================================',
            `DATA_DIR=${env.DATA_DIR || DEFAULT_DATA_DIR}`,
            `LIGHTRAG_WORKING_DIR=${env.LIGHTRAG_WORKING_DIR || env.LIGHTRAG_DIR || DEFAULT_LIGHTRAG_WORKING_DIR}`,
            '',
            '# ============================================',
            '# Optional Knowledge Graph',
            '# ============================================',
            '# Leave false for CPU-only or document-only workflows.',
            `ENABLE_LIGHTRAG=${env.ENABLE_LIGHTRAG || booleanEnv(DEFAULT_ENABLE_LIGHTRAG)}`,
            '',
            '# ============================================',
            '# MCP Client Safety Limits',
            '# ============================================',
            '# Keep responses bounded for stdio clients such as Cline/Copilot/Codex.',
            `ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS=${env.ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS || DEFAULT_MCP_TEXT_RESPONSE_CHARS}`,
            `ASSET_AWARE_MCP_IMAGE_RESPONSE_CHARS=${env.ASSET_AWARE_MCP_IMAGE_RESPONSE_CHARS || DEFAULT_MCP_IMAGE_RESPONSE_CHARS}`,
            `ASSET_AWARE_TABLE_STARTUP_LOAD_MAX_BYTES=${env.ASSET_AWARE_TABLE_STARTUP_LOAD_MAX_BYTES || DEFAULT_TABLE_STARTUP_LOAD_MAX_BYTES}`,
            `ASSET_AWARE_SECTION_TREE_LOAD_MAX_BYTES=${env.ASSET_AWARE_SECTION_TREE_LOAD_MAX_BYTES || DEFAULT_SECTION_TREE_LOAD_MAX_BYTES}`,
            `ASSET_AWARE_SEGMENTATION_SOURCE_LOAD_MAX_BYTES=${env.ASSET_AWARE_SEGMENTATION_SOURCE_LOAD_MAX_BYTES || DEFAULT_SEGMENTATION_SOURCE_LOAD_MAX_BYTES}`,
            ''
        ];

        return lines.join('\n');
    }

    /**
     * Get data directory path
     */
    getDataDir(): string {
        const env = this.readEnvSync();
        const dataDir = env.DATA_DIR || DEFAULT_DATA_DIR;
        if (path.isAbsolute(dataDir)) {
            return dataDir;
        }
        return path.resolve(this.projectRoot, dataDir);
    }

    /**
     * Synchronous read for quick access
     */
    private readEnvSync(): EnvConfig {
        if (!this.exists()) {
            return defaultEnv();
        }

        try {
            const content = fs.readFileSync(this.envPath, 'utf-8');
            return this.parseEnvContent(content);
        } catch {
            return defaultEnv();
        }
    }

    /**
     * List ingested documents from data directory
     */
    listDocuments(): { id: string; path: string; manifestExists: boolean }[] {
        const dataDir = this.getDataDir();
        const documents: { id: string; path: string; manifestExists: boolean }[] = [];

        if (!fs.existsSync(dataDir)) {
            return documents;
        }

        try {
            const entries = fs.readdirSync(dataDir, { withFileTypes: true });

            for (const entry of entries) {
                if (entry.isDirectory() && entry.name.startsWith('doc_')) {
                    const docPath = path.join(dataDir, entry.name);
                    const manifestPath = this.findManifestPath(docPath, entry.name);

                    documents.push({
                        id: entry.name,
                        path: docPath,
                        manifestExists: manifestPath !== null
                    });
                }
            }
        } catch (error) {
            console.error('Error listing documents:', error);
        }

        return documents;
    }

    /**
     * List persisted ETL jobs from data/jobs directory.
     */
    listJobs(): { id: string; status: string; progress: number; path: string }[] {
        const jobsDir = path.join(this.getDataDir(), 'jobs');
        const jobs: { id: string; status: string; progress: number; path: string }[] = [];

        if (!fs.existsSync(jobsDir)) {
            return jobs;
        }

        try {
            const entries = fs.readdirSync(jobsDir, { withFileTypes: true });
            for (const entry of entries) {
                if (!entry.isFile() || !entry.name.endsWith('.json') || !entry.name.startsWith('job_')) {
                    continue;
                }

                const jobPath = path.join(jobsDir, entry.name);
                try {
                    const content = fs.readFileSync(jobPath, 'utf-8');
                    const data = JSON.parse(content) as {
                        job_id?: string;
                        status?: string;
                        progress?: { percentage?: number };
                    };
                    jobs.push({
                        id: data.job_id || entry.name.replace('.json', ''),
                        status: data.status || 'unknown',
                        progress: data.progress?.percentage || 0,
                        path: jobPath
                    });
                } catch {
                    // Skip unreadable job files
                }
            }
        } catch (error) {
            console.error('Error listing jobs:', error);
        }

        return jobs;
    }

    /**
     * List A2T tables from tables directory
     */
    listTables(): { id: string; title: string; path: string; mdPath: string }[] {
        const dataDir = this.getDataDir();
        const tablesDir = path.join(dataDir, 'tables');
        const tables: { id: string; title: string; path: string; mdPath: string }[] = [];

        if (!fs.existsSync(tablesDir)) {
            return tables;
        }

        try {
            const entries = fs.readdirSync(tablesDir, { withFileTypes: true });
            for (const entry of entries) {
                if (entry.isFile() && entry.name.endsWith('.json') && entry.name.startsWith('tbl_')) {
                    const tableId = entry.name.replace('.json', '');
                    const jsonPath = path.join(tablesDir, entry.name);
                    const mdPath = path.join(tablesDir, `${tableId}.md`);

                    try {
                        const content = fs.readFileSync(jsonPath, 'utf-8');
                        const data = JSON.parse(content);
                        tables.push({
                            id: tableId,
                            title: data.title || tableId,
                            path: jsonPath,
                            mdPath: fs.existsSync(mdPath) ? mdPath : ''
                        });
                    } catch {
                        // Skip invalid JSON
                    }
                }
            }
        } catch (error) {
            console.error('Error listing tables:', error);
        }

        return tables;
    }

    /**
     * List A2T drafts from drafts directory
     */
    listDrafts(): { id: string; title: string; path: string }[] {
        const dataDir = this.getDataDir();
        const draftsDir = path.join(dataDir, 'tables', 'drafts');
        const drafts: { id: string; title: string; path: string }[] = [];

        if (!fs.existsSync(draftsDir)) {
            return drafts;
        }

        try {
            const entries = fs.readdirSync(draftsDir, { withFileTypes: true });
            for (const entry of entries) {
                if (entry.isFile() && entry.name.endsWith('.json') && entry.name.startsWith('draft_')) {
                    const draftId = entry.name.replace('.json', '');
                    const jsonPath = path.join(draftsDir, entry.name);

                    try {
                        const content = fs.readFileSync(jsonPath, 'utf-8');
                        const data = JSON.parse(content);
                        drafts.push({
                            id: draftId,
                            title: data.title || draftId,
                            path: jsonPath
                        });
                    } catch {
                        // Skip invalid JSON
                    }
                }
            }
        } catch (error) {
            console.error('Error listing drafts:', error);
        }

        return drafts;
    }

    /**
     * Read document manifest
     */
    readManifest(docId: string): object | null {
        const manifestPath = this.getManifestPath(docId);

        if (!manifestPath) {
            return null;
        }

        try {
            const content = fs.readFileSync(manifestPath, 'utf-8');
            return JSON.parse(content);
        } catch {
            return null;
        }
    }

    /**
     * List known document artifacts for quick review from the VS Code tree.
     */
    listDocumentArtifacts(docId: string): DocumentArtifact[] {
        const docDir = path.join(this.getDataDir(), docId);
        const candidates: DocumentArtifact[] = [
            {
                id: 'manifest',
                label: 'Manifest',
                kind: 'json',
                path: path.join(docDir, `${docId}_manifest.json`),
                icon: 'json',
            },
            {
                id: 'manifest-legacy',
                label: 'Manifest (legacy)',
                kind: 'json',
                path: path.join(docDir, 'manifest.json'),
                icon: 'json',
            },
            {
                id: 'markdown',
                label: 'Full Markdown',
                kind: 'markdown',
                path: path.join(docDir, `${docId}_full.md`),
                icon: 'markdown',
            },
            {
                id: 'blocks',
                label: 'Blocks',
                kind: 'json',
                path: path.join(docDir, 'blocks.json'),
                icon: 'symbol-structure',
            },
            {
                id: 'segmentation',
                label: 'Segmentation',
                kind: 'json',
                path: path.join(docDir, 'segmentation.json'),
                icon: 'symbol-structure',
            },
            {
                id: 'citation-index',
                label: 'Citation Index',
                kind: 'jsonl',
                path: path.join(docDir, 'citation_index.jsonl'),
                icon: 'references',
            },
            {
                id: 'citation-status',
                label: 'Citation Status',
                kind: 'json',
                path: path.join(docDir, 'citation_index.status.json'),
                icon: 'verified',
            },
        ];

        return candidates.filter((artifact, index, all) => {
            if (!fs.existsSync(artifact.path)) {
                return false;
            }
            return all.findIndex(candidate => candidate.path === artifact.path) === index;
        });
    }

    /**
     * List citation spans from citation_index.jsonl with source line numbers.
     */
    listCitationSpans(docId: string, limit = 25): CitationSpanSummary[] {
        const indexPath = path.join(this.getDataDir(), docId, 'citation_index.jsonl');
        if (!fs.existsSync(indexPath)) {
            return [];
        }

        try {
            const lines = fs.readFileSync(indexPath, 'utf-8').split(/\r?\n/);
            const spans: CitationSpanSummary[] = [];
            for (let i = 0; i < lines.length && spans.length < limit; i += 1) {
                const line = lines[i].trim();
                if (!line) {
                    continue;
                }
                try {
                    const data = JSON.parse(line) as {
                        span_id?: string;
                        page?: number;
                        line_start?: number;
                        line_end?: number;
                        text?: string;
                    };
                    const quote = data.text || '';
                    const lineDisplay = typeof data.line_start === 'number'
                        ? `L${data.line_start + 1}-${data.line_end ?? data.line_start + 1}`
                        : 'L?';
                    spans.push({
                        spanId: data.span_id || `span-${i + 1}`,
                        label: data.span_id || `Span ${i + 1}`,
                        description: `p.${data.page ?? '?'} ${lineDisplay}`,
                        quote,
                        path: indexPath,
                        line: i,
                    });
                } catch {
                    // Skip invalid JSONL records.
                }
            }
            return spans;
        } catch {
            return [];
        }
    }
}
