import * as fs from 'fs';
import * as net from 'net';
import * as os from 'os';
import * as path from 'path';
import * as vscode from 'vscode';
import { parse as parseToml } from 'smol-toml';
import {
    ASSET_AWARE_SERVER_KEY,
    buildAssetAwareLaunchSpec,
    isAssetAwareLaunch,
    isWorkspaceTrusted,
} from './mcpConfigCommon';

interface CodexServerSpec {
    command: string;
    args: string[];
    cwd: string;
    env: Record<string, string>;
    envVars: string[];
}

interface StripResult {
    content: string;
    removed: boolean;
    blockedByCustom: boolean;
    insertionOffset?: number;
    preservedPrimaryBody?: string;
    dormantPolicyBlock?: boolean;
}

interface SourceLine {
    text: string;
    start: number;
    end: number;
}

interface ConfigSnapshot {
    content: string;
    exists: boolean;
    dev?: number;
    ino?: number;
    mtimeMs?: number;
    size?: number;
}

interface TomlLexState {
    quote: 'basic' | 'literal' | 'multi-basic' | 'multi-literal' | undefined;
    squareDepth: number;
    braceDepth: number;
}

interface ManagedBlockRange {
    blockStart: number;
    blockEnd: number;
    markerStart: number;
    primaryBodyStart: number;
    primaryBodyEnd: number;
    dormantPolicyBlock: boolean;
}

type UnknownRecord = Record<string, unknown>;

const CODEX_STARTUP_TIMEOUT_SECONDS = 180;
const CODEX_TOOL_TIMEOUT_SECONDS = 900;
const CODEX_MANAGED_MARKER_CURRENT = '# Managed by asset-aware-mcp VS Code extension. Set assetAwareMcp.manageCodexConfig=false to opt out.';
const CODEX_MANAGED_MARKER_LEGACY = '# Managed by asset-aware-mcp VS Code extension. Remove this block to opt out.';
const CODEX_DORMANT_POLICY_MARKER = '# Asset-Aware MCP launch disabled after management opt-out; user policy below is preserved for safe re-enable.';
const CODEX_MANAGED_MARKERS = new Set([
    CODEX_MANAGED_MARKER_CURRENT,
    CODEX_MANAGED_MARKER_LEGACY,
    CODEX_DORMANT_POLICY_MARKER,
]);
const DISABLE_DOTENV_ENV_NAME = 'ASSET_AWARE_DISABLE_DOTENV';
const CODEX_OWNED_PRIMARY_KEYS = new Set([
    'args',
    'command',
    'cwd',
    'enabled',
    'env',
    'env_vars',
    'startup_timeout_sec',
    'tool_timeout_sec',
]);

// Only operational metadata may be serialized into ~/.codex/config.toml.
// Values from repository .env files are otherwise untrusted and may contain
// arbitrary credentials.
const CODEX_INLINE_ENV_ALLOWLIST = new Set([
    DISABLE_DOTENV_ENV_NAME,
    'ASSET_AWARE_MCP_ENABLE_LEGACY_TOOLS',
    'ASSET_AWARE_MCP_IMAGE_RESPONSE_CHARS',
    'ASSET_AWARE_MARKER_OUTPUT_LOG',
    'ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS',
    'ASSET_AWARE_MCP_TOOL_SURFACE',
    'ASSET_AWARE_SECTION_TREE_LOAD_MAX_BYTES',
    'ASSET_AWARE_SEGMENTATION_SOURCE_LOAD_MAX_BYTES',
    'ASSET_AWARE_SUPPRESS_MARKER_OUTPUT',
    'ASSET_AWARE_TABLE_STARTUP_LOAD_MAX_BYTES',
    'DATA_DIR',
    'DOCLING_PYTHON_PATH',
    'ENABLE_LIGHTRAG',
    'ENABLE_MISTRAL_OCR',
    'ETL_ENGINE',
    'ETL_PROFILE',
    'ETL_PROFILE_JSON',
    'IMAGE_OUTPUT_FORMAT',
    'LIGHTRAG_EMBEDDING_MODEL',
    'LIGHTRAG_WORKING_DIR',
    'LLM_BACKEND',
    'MAX_IMAGE_SIZE_MB',
    'OLLAMA_EMBEDDING_MODEL',
    'OLLAMA_EMBEDDING_TIMEOUT',
    'OLLAMA_HOST',
    'OLLAMA_LLM_TIMEOUT',
    'OLLAMA_MODEL',
    'OPENAI_EMBEDDING_MODEL',
    'OPENAI_MODEL',
    'OPENROUTER_BASE_URL',
    'OPENROUTER_MODEL',
    'TABLE_OUTPUT_DIR',
    'UV_CACHE_DIR',
]);

const BACKEND_SPECIFIC_INLINE_ENV = new Map<string, Set<string>>([
    ['OLLAMA_HOST', new Set(['ollama'])],
    ['OLLAMA_MODEL', new Set(['ollama'])],
    ['OLLAMA_EMBEDDING_MODEL', new Set(['ollama'])],
    ['OPENAI_MODEL', new Set(['openai'])],
    ['OPENROUTER_BASE_URL', new Set(['openrouter'])],
    ['OPENROUTER_MODEL', new Set(['openrouter'])],
]);

const POLICY_MANAGED_FORWARD_ENV_NAMES = new Set([
    'MISTRAL_API_KEY',
    'OLLAMA_HOST',
    'OPENAI_API_KEY',
    'OPENROUTER_API_KEY',
    'OPENROUTER_BASE_URL',
]);

function isRecord(value: unknown): value is UnknownRecord {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function parseTomlConfig(content: string): UnknownRecord | undefined {
    try {
        const parsed = parseToml(content);
        return isRecord(parsed) ? parsed as UnknownRecord : undefined;
    } catch {
        return undefined;
    }
}

function getSemanticServer(config: UnknownRecord, serverKey: string): UnknownRecord | undefined {
    const servers = config['mcp_servers'];
    if (!isRecord(servers) || !Object.prototype.hasOwnProperty.call(servers, serverKey)) {
        return undefined;
    }
    const server = servers[serverKey];
    return isRecord(server) ? server : undefined;
}

function hasSemanticServer(config: UnknownRecord, serverKey: string): boolean {
    const servers = config['mcp_servers'];
    return isRecord(servers) && Object.prototype.hasOwnProperty.call(servers, serverKey);
}

function getStringRecord(value: unknown): Record<string, string> {
    if (!isRecord(value)) {
        return {};
    }
    const result: Record<string, string> = {};
    for (const [key, item] of Object.entries(value)) {
        if (typeof item === 'string') {
            result[key] = item;
        }
    }
    return result;
}

function getStringArray(value: unknown): string[] {
    if (!Array.isArray(value)) {
        return [];
    }
    return value.filter((item): item is string => typeof item === 'string');
}

function normalizeBoolean(value: string | undefined): boolean {
    return ['1', 'true', 'yes', 'on'].includes(value?.trim().toLowerCase() ?? '');
}

function isCredentialOrTransportEnvName(key: string): boolean {
    return /(?:API_KEY|ACCESS_KEY|AUTH|BEARER|COOKIE|CREDENTIAL|DATABASE_URL|DB_URL|PASS(?:WORD|WD)?|PRIVATE_KEY|SECRET|TOKEN|_PROXY|_CERT_FILE|_CA_BUNDLE)$/i.test(key);
}

function isTransportEnvName(key: string): boolean {
    return /(?:_PROXY|_CERT_FILE|_CA_BUNDLE)$/i.test(key);
}

function parseSafeHttpUrl(value: string): URL | undefined {
    try {
        const parsed = new URL(value);
        if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
            return undefined;
        }
        return parsed;
    } catch {
        return undefined;
    }
}

function hasUrlSecretMaterial(parsed: URL): boolean {
    return parsed.username !== '' || parsed.password !== '' || parsed.search !== '' || parsed.hash !== '';
}

function isLoopbackHostname(hostname: string): boolean {
    const normalized = hostname.toLowerCase().replace(/^\[|\]$/g, '');
    if (normalized === 'localhost' || normalized === '::1') {
        return true;
    }
    return net.isIP(normalized) === 4 && normalized.startsWith('127.');
}

function isSafeOllamaUrl(value: string): boolean {
    const parsed = parseSafeHttpUrl(value);
    return Boolean(parsed && !hasUrlSecretMaterial(parsed));
}

function isSafeOpenRouterUrl(value: string): boolean {
    const parsed = parseSafeHttpUrl(value);
    if (!parsed || hasUrlSecretMaterial(parsed)) {
        return false;
    }
    return parsed.protocol === 'https:' || isLoopbackHostname(parsed.hostname);
}

function isSafeHttpUrl(value: string): boolean {
    return isSafeOllamaUrl(value);
}

function backendAllowsInlineEnv(key: string, backend: string): boolean {
    const allowedBackends = BACKEND_SPECIFIC_INLINE_ENV.get(key);
    return !allowedBackends || allowedBackends.has(backend);
}

function shouldForwardOpenRouterBaseUrl(value: string): boolean {
    const parsed = parseSafeHttpUrl(value);
    if (!parsed) {
        return false;
    }
    // Secret-bearing URL components must never be serialized. Remote HTTP is
    // rejected completely rather than smuggled through env_vars.
    return (parsed.protocol === 'https:' || isLoopbackHostname(parsed.hostname))
        && hasUrlSecretMaterial(parsed);
}

function buildCodexSafeEnv(
    source: Record<string, string>,
    existingEnvVars: Iterable<string> = [],
): {
    env: Record<string, string>;
    envVars: string[];
} {
    const env: Record<string, string> = {
        [DISABLE_DOTENV_ENV_NAME]: 'true',
    };
    const envVars = new Set<string>();
    const existingEnvVarSet = new Set(existingEnvVars);
    const backend = source['LLM_BACKEND']?.trim().toLowerCase() || 'ollama';

    // Existing extension-managed forwarding is an explicit user-visible
    // choice. Keep it stable across syncs, but never infer unrelated secrets.
    for (const key of existingEnvVars) {
        if (/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)
            && !POLICY_MANAGED_FORWARD_ENV_NAMES.has(key)) {
            envVars.add(key);
        }
    }

    if (backend === 'openai' && (source['OPENAI_API_KEY'] || existingEnvVarSet.has('OPENAI_API_KEY'))) {
        envVars.add('OPENAI_API_KEY');
    } else if (backend === 'openrouter') {
        if (source['OPENROUTER_API_KEY'] || existingEnvVarSet.has('OPENROUTER_API_KEY')) {
            envVars.add('OPENROUTER_API_KEY');
        } else if (source['OPENAI_API_KEY'] || existingEnvVarSet.has('OPENAI_API_KEY')) {
            // The Python backend intentionally supports this compatibility
            // fallback, but only when no OpenRouter-specific credential exists.
            envVars.add('OPENAI_API_KEY');
        }
    }
    if (normalizeBoolean(source['ENABLE_MISTRAL_OCR'])
        && (source['MISTRAL_API_KEY'] || existingEnvVarSet.has('MISTRAL_API_KEY'))) {
        envVars.add('MISTRAL_API_KEY');
    }

    for (const [key, value] of Object.entries(source)) {
        if (isTransportEnvName(key)) {
            envVars.add(key);
            continue;
        }
        if (!CODEX_INLINE_ENV_ALLOWLIST.has(key) || !backendAllowsInlineEnv(key, backend)) {
            continue;
        }
        if (key === 'OLLAMA_HOST') {
            if (isSafeOllamaUrl(value)) {
                env[key] = value;
            } else if (parseSafeHttpUrl(value) && hasUrlSecretMaterial(parseSafeHttpUrl(value)!)) {
                envVars.add(key);
            }
            continue;
        }
        if (key === 'OPENROUTER_BASE_URL') {
            if (isSafeOpenRouterUrl(value)) {
                env[key] = value;
            } else if (shouldForwardOpenRouterBaseUrl(value)) {
                envVars.add(key);
            }
            continue;
        }
        env[key] = value;
    }

    return {
        env,
        envVars: Array.from(envVars).sort(),
    };
}

export function getCodexHome(): string {
    const override = process.env.CODEX_HOME;
    if (override && override.trim()) {
        return override.trim();
    }
    return path.join(os.homedir(), '.codex');
}

export function getCodexConfigPath(): string {
    return path.join(getCodexHome(), 'config.toml');
}

export function isCodexAvailable(): boolean {
    const config = vscode.workspace.getConfiguration('assetAwareMcp');
    if (!config.get<boolean>('manageCodexConfig', true)) {
        return false;
    }
    if (config.get<boolean>('installCodexConfig', false)) {
        return true;
    }
    return fs.existsSync(getCodexHome());
}

function escapeTomlString(value: string): string {
    return Array.from(value, (char) => {
        switch (char) {
            case '\b':
                return '\\b';
            case '\t':
                return '\\t';
            case '\n':
                return '\\n';
            case '\f':
                return '\\f';
            case '\r':
                return '\\r';
            case '"':
                return '\\"';
            case '\\':
                return '\\\\';
            default:
                if (char.charCodeAt(0) <= 0x1f || char.charCodeAt(0) === 0x7f) {
                    return `\\u${char.charCodeAt(0).toString(16).toUpperCase().padStart(4, '0')}`;
                }
                return char;
        }
    }).join('');
}

function renderArgs(args: string[]): string {
    return '[' + args.map((arg) => `"${escapeTomlString(arg)}"`).join(', ') + ']';
}

function renderManagedBlock(
    serverKey: string,
    spec: CodexServerSpec,
    preservedPrimaryBody: string = '',
): string {
    const lines: string[] = [
        CODEX_MANAGED_MARKER_CURRENT,
        `[mcp_servers.${serverKey}]`,
        `command = "${escapeTomlString(spec.command)}"`,
        `args = ${renderArgs(spec.args)}`,
        `cwd = "${escapeTomlString(spec.cwd)}"`,
        'enabled = true',
        `startup_timeout_sec = ${CODEX_STARTUP_TIMEOUT_SECONDS}`,
        `tool_timeout_sec = ${CODEX_TOOL_TIMEOUT_SECONDS}`,
    ];

    if (spec.envVars.length > 0) {
        lines.push(`env_vars = ${renderArgs(spec.envVars)}`);
    }

    let rendered = lines.join('\n') + '\n';
    if (preservedPrimaryBody !== '') {
        rendered += preservedPrimaryBody;
        if (!rendered.endsWith('\n') && !rendered.endsWith('\r')) {
            rendered += '\n';
        }
    }

    const envKeys = Object.keys(spec.env).sort();
    if (envKeys.length > 0) {
        if (!rendered.endsWith('\n\n') && !rendered.endsWith('\r\n\r\n')) {
            rendered += '\n';
        }
        const envLines = [`[mcp_servers.${serverKey}.env]`];
        for (const key of envKeys) {
            envLines.push(`${key} = "${escapeTomlString(spec.env[key])}"`);
        }
        rendered += envLines.join('\n') + '\n';
    }

    return rendered;
}

function splitSourceLines(content: string): SourceLine[] {
    const lines: SourceLine[] = [];
    let start = 0;
    for (let index = 0; index < content.length; index += 1) {
        if (content[index] !== '\n' && content[index] !== '\r') {
            continue;
        }
        const textEnd = index;
        if (content[index] === '\r' && content[index + 1] === '\n') {
            index += 1;
        }
        lines.push({ text: content.slice(start, textEnd), start, end: index + 1 });
        start = index + 1;
    }
    if (start < content.length || content.length === 0) {
        lines.push({ text: content.slice(start), start, end: content.length });
    }
    return lines;
}

function stripTomlComment(line: string): string {
    let inString: '"' | "'" | '' = '';
    let escaping = false;
    let output = '';
    for (const char of line) {
        if (inString) {
            output += char;
            if (inString === '"' && !escaping && char === '\\') {
                escaping = true;
                continue;
            }
            if (!escaping && char === inString) {
                inString = '';
            }
            escaping = false;
            continue;
        }
        if (char === '"' || char === "'") {
            inString = char;
            output += char;
            continue;
        }
        if (char === '#') {
            break;
        }
        output += char;
    }
    return output;
}

function isTomlTableHeaderLine(line: string): boolean {
    const value = stripTomlComment(line).trim();
    return (value.startsWith('[[') && value.endsWith(']]'))
        || (value.startsWith('[') && !value.startsWith('[[') && value.endsWith(']'));
}

function semanticTableHeaderMatches(
    line: string,
    serverKey: string,
    childKey?: string,
): boolean {
    const header = stripTomlComment(line).trim();
    if (!header.startsWith('[') || header.startsWith('[[') || !header.endsWith(']')) {
        return false;
    }
    const probeKey = '__asset_aware_header_probe__';
    const parsed = parseTomlConfig(`${header}\n${probeKey} = true\n`);
    const server = parsed ? getSemanticServer(parsed, serverKey) : undefined;
    if (!server) {
        return false;
    }
    if (childKey === undefined) {
        return server[probeKey] === true;
    }
    const child = server[childKey];
    return isRecord(child) && child[probeKey] === true;
}

function isCanonicalPrimaryHeader(line: string, serverKey: string): boolean {
    return semanticTableHeaderMatches(line, serverKey);
}

function isCanonicalEnvHeader(line: string, serverKey: string): boolean {
    return semanticTableHeaderMatches(line, serverKey, 'env');
}

function isManagedMarkerLine(line: string): boolean {
    return CODEX_MANAGED_MARKERS.has(line.trim());
}

function isTopLevelTriviaLine(line: string): boolean {
    const trimmed = line.trim();
    return trimmed === '' || trimmed.startsWith('#');
}

function scanTomlLine(line: string, state: TomlLexState): void {
    for (let index = 0; index < line.length; index += 1) {
        if (state.quote === 'multi-basic') {
            if (line.startsWith('"""', index)) {
                state.quote = undefined;
                index += 2;
            } else if (line[index] === '\\') {
                index += 1;
            }
            continue;
        }
        if (state.quote === 'multi-literal') {
            if (line.startsWith("'''", index)) {
                state.quote = undefined;
                index += 2;
            }
            continue;
        }
        if (state.quote === 'basic') {
            if (line[index] === '\\') {
                index += 1;
            } else if (line[index] === '"') {
                state.quote = undefined;
            }
            continue;
        }
        if (state.quote === 'literal') {
            if (line[index] === "'") {
                state.quote = undefined;
            }
            continue;
        }

        if (line[index] === '#') {
            break;
        }
        if (line.startsWith('"""', index)) {
            state.quote = 'multi-basic';
            index += 2;
        } else if (line.startsWith("'''", index)) {
            state.quote = 'multi-literal';
            index += 2;
        } else if (line[index] === '"') {
            state.quote = 'basic';
        } else if (line[index] === "'") {
            state.quote = 'literal';
        } else if (line[index] === '[') {
            state.squareDepth += 1;
        } else if (line[index] === ']') {
            state.squareDepth = Math.max(0, state.squareDepth - 1);
        } else if (line[index] === '{') {
            state.braceDepth += 1;
        } else if (line[index] === '}') {
            state.braceDepth = Math.max(0, state.braceDepth - 1);
        }
    }

    // Basic and literal strings cannot legally cross a line boundary. The
    // semantic parser rejects malformed input before this scanner is used.
    if (state.quote === 'basic' || state.quote === 'literal') {
        state.quote = undefined;
    }
}

function tomlStateIsTopLevel(state: TomlLexState): boolean {
    return !state.quote && state.squareDepth === 0 && state.braceDepth === 0;
}

function simpleAssignmentKey(line: string): string | undefined {
    const match = line.match(/^\s*(?:([A-Za-z0-9_-]+)|"([^"\\]*)"|'([^']*)')\s*=/u);
    return match?.[1] ?? match?.[2] ?? match?.[3];
}

function stripOwnedPrimaryAssignments(body: string): string {
    const lines = splitSourceLines(body);
    const state: TomlLexState = { quote: undefined, squareDepth: 0, braceDepth: 0 };
    let skippingOwnedValue = false;
    let preserved = '';

    for (const line of lines) {
        if (!skippingOwnedValue && tomlStateIsTopLevel(state)) {
            const key = simpleAssignmentKey(line.text);
            skippingOwnedValue = key !== undefined && CODEX_OWNED_PRIMARY_KEYS.has(key);
        }

        if (!skippingOwnedValue) {
            preserved += body.slice(line.start, line.end);
        }
        scanTomlLine(line.text, state);
        if (skippingOwnedValue && tomlStateIsTopLevel(state)) {
            skippingOwnedValue = false;
        }
    }

    return preserved;
}

function findManagedBlockRange(content: string, serverKey: string): ManagedBlockRange | undefined {
    const lines = splitSourceLines(content);
    const state: TomlLexState = { quote: undefined, squareDepth: 0, braceDepth: 0 };
    let primaryIndex = -1;
    let markerIndex = -1;

    for (let index = 0; index < lines.length; index += 1) {
        const atTopLevel = !state.quote && state.squareDepth === 0 && state.braceDepth === 0;
        if (atTopLevel && isTomlTableHeaderLine(lines[index].text)
            && isCanonicalPrimaryHeader(lines[index].text, serverKey)) {
            let candidate = index - 1;
            while (candidate >= 0 && lines[candidate].text.trim() === '') {
                candidate -= 1;
            }
            if (candidate >= 0 && isManagedMarkerLine(lines[candidate].text)) {
                primaryIndex = index;
                markerIndex = candidate;
                break;
            }
        }
        scanTomlLine(lines[index].text, state);
    }

    if (primaryIndex < 0 || markerIndex < 0) {
        return undefined;
    }

    const managedState: TomlLexState = { quote: undefined, squareDepth: 0, braceDepth: 0 };
    let trailingTriviaStart: number | undefined;
    let primaryBodyEnd: number | undefined;
    let foundEnvTable = false;
    for (let index = primaryIndex; index < lines.length; index += 1) {
        const atTopLevel = tomlStateIsTopLevel(managedState);
        if (index > primaryIndex && atTopLevel && isTomlTableHeaderLine(lines[index].text)) {
            if (!foundEnvTable && isCanonicalEnvHeader(lines[index].text, serverKey)) {
                primaryBodyEnd = lines[index].start;
                foundEnvTable = true;
                trailingTriviaStart = undefined;
                scanTomlLine(lines[index].text, managedState);
                continue;
            }
            const blockEnd = trailingTriviaStart ?? lines[index].start;
            return {
                blockStart: lines[primaryIndex].start,
                blockEnd,
                markerStart: lines[markerIndex].start,
                primaryBodyStart: lines[primaryIndex].end,
                primaryBodyEnd: primaryBodyEnd ?? blockEnd,
                dormantPolicyBlock: lines[markerIndex].text.trim() === CODEX_DORMANT_POLICY_MARKER,
            };
        }
        if (atTopLevel && isTopLevelTriviaLine(lines[index].text)) {
            trailingTriviaStart ??= lines[index].start;
        } else {
            trailingTriviaStart = undefined;
        }
        scanTomlLine(lines[index].text, managedState);
    }

    const blockEnd = trailingTriviaStart ?? content.length;
    return {
        blockStart: lines[primaryIndex].start,
        blockEnd,
        markerStart: lines[markerIndex].start,
        primaryBodyStart: lines[primaryIndex].end,
        primaryBodyEnd: primaryBodyEnd ?? blockEnd,
        dormantPolicyBlock: lines[markerIndex].text.trim() === CODEX_DORMANT_POLICY_MARKER,
    };
}

function extractManagedBlock(content: string, serverKey: string): string | undefined {
    const range = findManagedBlockRange(content, serverKey);
    return range ? content.slice(range.blockStart, range.blockEnd) : undefined;
}

function hasManagedMarkerBeforeBlock(content: string, serverKey: string): boolean {
    return findManagedBlockRange(content, serverKey) !== undefined;
}

function stripManagedBlock(content: string, serverKey: string): StripResult {
    const parsed = parseTomlConfig(content);
    if (!parsed) {
        return { content, removed: false, blockedByCustom: true };
    }
    const semanticServerExists = hasSemanticServer(parsed, serverKey);
    const range = findManagedBlockRange(content, serverKey);
    if (semanticServerExists && !range) {
        return { content, removed: false, blockedByCustom: true };
    }
    if (!range) {
        return { content, removed: false, blockedByCustom: false };
    }

    const preservedPrimaryBody = stripOwnedPrimaryAssignments(
        content.slice(range.primaryBodyStart, range.primaryBodyEnd),
    );
    const prefix = content.slice(0, range.markerStart);

    return {
        content: prefix + content.slice(range.blockEnd),
        removed: true,
        blockedByCustom: false,
        insertionOffset: prefix.length,
        preservedPrimaryBody,
        dormantPolicyBlock: range.dormantPolicyBlock,
    };
}

function ensureTrailingBlankLine(content: string): string {
    if (content === '') {
        return '';
    }
    if (content.endsWith('\n\n')) {
        return content;
    }
    if (content.endsWith('\n')) {
        return content + '\n';
    }
    return content + '\n\n';
}

function insertAt(content: string, offset: number, inserted: string): string {
    return content.slice(0, offset) + inserted + content.slice(offset);
}

function renderDormantUserPolicy(serverKey: string, body: string): string {
    if (body.trim() === '' || body.split(/\r?\n/u).every(isTopLevelTriviaLine)) {
        return '';
    }
    // Codex requires every mcp_servers entry to retain a valid transport even
    // when disabled. Keep a non-executable placeholder so opt-out cannot start
    // Asset-Aware MCP, while user-owned approval/future policy remains valid
    // TOML and can be restored if management is enabled later.
    return [
        CODEX_DORMANT_POLICY_MARKER,
        `[mcp_servers.${serverKey}]`,
        'command = "asset-aware-mcp-management-disabled"',
        'args = []',
        'enabled = false',
        body,
    ].join('\n');
}

function warnSkippedConfigWrite(configPath: string, reason: string): void {
    vscode.window.showWarningMessage(
        `Asset-Aware MCP skipped updating ${configPath}: ${reason}`,
    );
}

function hasSuspiciousTomlSyntax(content: string): boolean {
    return parseTomlConfig(content) === undefined;
}

export function isValidCodexToml(content: string): boolean {
    return !hasSuspiciousTomlSyntax(content);
}

// Kept as a focused scanner helper for regression tests. Semantic validation
// is performed by smol-toml and therefore supports legal multiline values.
function hasBalancedTomlValue(value: string): boolean {
    return parseTomlConfig(`value = ${value}\n`) !== undefined;
}

function configPathIsSymlink(configPath: string): boolean {
    try {
        return fs.lstatSync(configPath).isSymbolicLink();
    } catch (error) {
        if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
            return false;
        }
        throw error;
    }
}

function sameSnapshotStat(left: fs.Stats, right: fs.Stats): boolean {
    return left.dev === right.dev
        && left.ino === right.ino
        && left.size === right.size
        && left.mtimeMs === right.mtimeMs;
}

function readConfig(configPath: string): ConfigSnapshot | undefined {
    try {
        if (configPathIsSymlink(configPath)) {
            warnSkippedConfigWrite(configPath, 'the config path is a symbolic link. Replace it with a regular file and retry.');
            return undefined;
        }
        if (!fs.existsSync(configPath)) {
            return { content: '', exists: false };
        }
        const before = fs.lstatSync(configPath);
        if (!before.isFile()) {
            warnSkippedConfigWrite(configPath, 'the config path is not a regular file.');
            return undefined;
        }
        const content = fs.readFileSync(configPath, 'utf-8');
        const after = fs.lstatSync(configPath);
        if (!sameSnapshotStat(before, after)) {
            warnSkippedConfigWrite(configPath, 'the file changed while it was being read; retry the operation.');
            return undefined;
        }
        return {
            content,
            exists: true,
            dev: after.dev,
            ino: after.ino,
            mtimeMs: after.mtimeMs,
            size: after.size,
        };
    } catch {
        warnSkippedConfigWrite(configPath, 'the file could not be read. Please fix permissions and retry.');
        return undefined;
    }
}

function assertConfigUnchanged(configPath: string, expected: ConfigSnapshot): void {
    if (!expected.exists) {
        if (fs.existsSync(configPath)) {
            throw new Error('Codex config was created concurrently; the new file was preserved');
        }
        return;
    }

    if (configPathIsSymlink(configPath)) {
        throw new Error('Codex config became a symbolic link during update');
    }
    let before: fs.Stats;
    let currentContent: string;
    let after: fs.Stats;
    try {
        before = fs.lstatSync(configPath);
        currentContent = fs.readFileSync(configPath, 'utf-8');
        after = fs.lstatSync(configPath);
    } catch {
        throw new Error('Codex config changed or disappeared during update');
    }
    if (!before.isFile()
        || !sameSnapshotStat(before, after)
        || before.dev !== expected.dev
        || before.ino !== expected.ino
        || before.size !== expected.size
        || before.mtimeMs !== expected.mtimeMs
        || currentContent !== expected.content) {
        throw new Error('Codex config changed concurrently; the newer file was preserved');
    }
}

function restoreClaimIfTargetAbsent(claimPath: string, configPath: string): boolean {
    try {
        fs.linkSync(claimPath, configPath);
        fs.rmSync(claimPath);
        return true;
    } catch (error) {
        if ((error as NodeJS.ErrnoException).code === 'EEXIST') {
            return false;
        }
        throw error;
    }
}

function writeConfigAtomic(
    configPath: string,
    content: string,
    expected?: ConfigSnapshot,
): void {
    fs.mkdirSync(path.dirname(configPath), { recursive: true });
    if (configPathIsSymlink(configPath)) {
        throw new Error('refusing to replace a symbolic-link Codex config');
    }

    const tmpPath = `${configPath}.tmp.${process.pid}.${Date.now()}.${Math.random().toString(16).slice(2)}`;
    const claimPath = `${configPath}.concurrent-backup.${process.pid}.${Date.now()}.${Math.random().toString(16).slice(2)}`;
    let claimActive = false;
    try {
        fs.writeFileSync(tmpPath, content, { encoding: 'utf-8', mode: 0o600, flag: 'wx' });
        if (expected) {
            assertConfigUnchanged(configPath, expected);
            if (!expected.exists) {
                // Hard-linking a fully written private temp file is an atomic
                // create-if-absent operation. It cannot overwrite a config that
                // appeared after the snapshot check.
                fs.linkSync(tmpPath, configPath);
                return;
            }
            // Atomically claim the exact path before installing the new file.
            // A check-then-rename alone has a lost-update window; moving the
            // current file aside lets us validate the claimed inode and use a
            // create-if-absent hard link for the replacement. The claim is
            // retained as a private recovery snapshot after success: a writer
            // may still hold the old inode open and write to it after every
            // finite stat/read check, so deleting it could silently lose that
            // later edit.
            fs.renameSync(configPath, claimPath);
            claimActive = true;
            fs.chmodSync(claimPath, 0o600);
            try {
                assertConfigUnchanged(claimPath, expected);
            } catch (error) {
                if (restoreClaimIfTargetAbsent(claimPath, configPath)) {
                    claimActive = false;
                }
                throw error;
            }
            try {
                fs.linkSync(tmpPath, configPath);
            } catch (error) {
                if (restoreClaimIfTargetAbsent(claimPath, configPath)) {
                    claimActive = false;
                }
                throw error;
            }
            try {
                // Catch a writer that already held the old inode open while it
                // was claimed. If our newly linked target is untouched, restore
                // that later edit atomically; otherwise preserve both paths.
                assertConfigUnchanged(claimPath, expected);
            } catch {
                const targetStat = fs.lstatSync(configPath);
                const tmpStat = fs.lstatSync(tmpPath);
                const targetIsOurUntouchedWrite = sameSnapshotStat(targetStat, tmpStat)
                    && fs.readFileSync(configPath, 'utf-8') === content;
                if (targetIsOurUntouchedWrite) {
                    fs.renameSync(claimPath, configPath);
                    claimActive = false;
                }
                throw new Error(
                    claimActive
                        ? `Codex config changed concurrently; both edits were preserved (recoverable file: ${claimPath})`
                        : 'Codex config changed concurrently; the later edit was restored',
                );
            }
            // Do not unlink the claimed inode. Besides preserving the exact
            // pre-update config, this keeps late writes through an already-open
            // file descriptor recoverable. Idempotent syncs return before this
            // function and therefore do not create additional snapshots.
            claimActive = false;
            return;
        } else if (configPathIsSymlink(configPath)) {
            throw new Error('Codex config became a symbolic link during update');
        }
        fs.renameSync(tmpPath, configPath);
    } finally {
        try {
            fs.rmSync(tmpPath, { force: true });
        } catch {
            // The rename already succeeded or the best-effort cleanup failed.
        }
        if (claimActive && !fs.existsSync(configPath)) {
            try {
                if (restoreClaimIfTargetAbsent(claimPath, configPath)) {
                    claimActive = false;
                }
            } catch {
                // Keep the uniquely named recoverable file instead of deleting
                // potentially concurrent user content.
            }
        }
    }
}

export function installCodexMcpServer(
    context: vscode.ExtensionContext,
    uvPath: string,
    needsUpgrade: boolean = false,
): boolean {
    if (!isWorkspaceTrusted()) {
        return false;
    }
    const config = vscode.workspace.getConfiguration('assetAwareMcp');
    if (!config.get<boolean>('manageCodexConfig', true)) {
        removeCodexMcpServer();
        return false;
    }
    if (!isCodexAvailable()) {
        return false;
    }

    const configPath = getCodexConfigPath();
    const launch = buildAssetAwareLaunchSpec(context, uvPath, {
        needsUpgrade,
        allowLocalSource: false,
        includeWorkspaceEnv: false,
    });
    if (!isAssetAwareLaunch(launch.command, launch.args)) {
        return false;
    }

    const snapshot = readConfig(configPath);
    if (snapshot === undefined) {
        return false;
    }
    let content = snapshot.content;
    const parsed = parseTomlConfig(content);
    if (!parsed) {
        warnSkippedConfigWrite(configPath, 'the TOML is invalid. Please fix the file and retry.');
        return false;
    }
    const original = content;
    const existingServer = getSemanticServer(parsed, ASSET_AWARE_SERVER_KEY);
    const stripped = stripManagedBlock(content, ASSET_AWARE_SERVER_KEY);
    if (stripped.blockedByCustom) {
        return false;
    }

    const existingEnvVars = getStringArray(existingServer?.['env_vars']);
    const safeEnv = buildCodexSafeEnv(launch.env, existingEnvVars);
    const codexCwd = context.globalStorageUri.fsPath;
    fs.mkdirSync(codexCwd, { recursive: true });
    const spec: CodexServerSpec = {
        command: launch.command,
        args: launch.args,
        cwd: codexCwd,
        env: safeEnv.env,
        envVars: safeEnv.envVars,
    };

    const managedBlock = renderManagedBlock(
        ASSET_AWARE_SERVER_KEY,
        spec,
        stripped.preservedPrimaryBody,
    );
    content = stripped.removed && stripped.insertionOffset !== undefined
        ? insertAt(stripped.content, stripped.insertionOffset, managedBlock)
        : ensureTrailingBlankLine(stripped.content) + managedBlock;
    if (content === original) {
        return false;
    }
    if (!parseTomlConfig(content)) {
        warnSkippedConfigWrite(configPath, 'the merged TOML would be invalid; the original file was preserved.');
        return false;
    }

    try {
        writeConfigAtomic(configPath, content, snapshot);
    } catch (error) {
        warnSkippedConfigWrite(configPath, String(error));
        return false;
    }
    return true;
}

export function removeCodexMcpServer(): boolean {
    if (!isWorkspaceTrusted()) {
        return false;
    }
    const configPath = getCodexConfigPath();
    const snapshot = readConfig(configPath);
    if (snapshot === undefined || snapshot.content === '') {
        return false;
    }
    const original = snapshot.content;
    if (!parseTomlConfig(original)) {
        warnSkippedConfigWrite(configPath, 'the TOML is invalid. Please fix the file and retry.');
        return false;
    }
    const stripped = stripManagedBlock(original, ASSET_AWARE_SERVER_KEY);
    if (stripped.blockedByCustom || !stripped.removed) {
        return false;
    }
    const preserved = renderDormantUserPolicy(
        ASSET_AWARE_SERVER_KEY,
        stripped.preservedPrimaryBody ?? '',
    );
    const content = stripped.insertionOffset === undefined
        ? stripped.content
        : insertAt(stripped.content, stripped.insertionOffset, preserved);
    if (!parseTomlConfig(content)) {
        warnSkippedConfigWrite(configPath, 'removing the managed fields would produce invalid TOML; the original file was preserved.');
        return false;
    }

    try {
        writeConfigAtomic(configPath, content, snapshot);
    } catch (error) {
        warnSkippedConfigWrite(configPath, String(error));
        return false;
    }
    return true;
}

export const __test__ = {
    escapeTomlString,
    renderManagedBlock,
    buildCodexSafeEnv,
    isCredentialOrTransportEnvName,
    isSafeHttpUrl,
    isSafeOllamaUrl,
    isSafeOpenRouterUrl,
    isLoopbackHostname,
    isManagedMarkerLine,
    hasManagedMarkerBeforeBlock,
    stripManagedBlock,
    extractManagedBlock,
    extractManagedEnv: (block: string | undefined, serverKey: string): Record<string, string> | undefined => {
        if (!block) {
            return undefined;
        }
        const parsed = parseTomlConfig(block);
        const env = parsed ? getStringRecord(getSemanticServer(parsed, serverKey)?.['env']) : {};
        return Object.keys(env).length > 0 ? env : undefined;
    },
    parseTomlConfig,
    getSemanticServer,
    hasSemanticServer,
    hasSuspiciousTomlSyntax,
    stripTomlComment,
    hasBalancedTomlValue,
    findManagedBlockRange,
    writeConfigAtomic,
};
