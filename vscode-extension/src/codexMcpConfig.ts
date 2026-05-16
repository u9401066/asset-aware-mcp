import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import * as vscode from 'vscode';
import {
    ASSET_AWARE_SERVER_KEY,
    buildAssetAwareLaunchSpec,
    isAssetAwareLaunch,
    mergeManagedEnv,
} from './mcpConfigCommon';

interface CodexServerSpec {
    command: string;
    args: string[];
    env: Record<string, string>;
}

interface StripResult {
    content: string;
    removed: boolean;
    blockedByCustom: boolean;
}

function blockHeaderPattern(serverKey: string): RegExp {
    const escapedKey = serverKey.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return new RegExp(`^\\s*\\[\\s*mcp_servers\\.${escapedKey}(?:\\.[^\\]]+)?\\s*\\]\\s*$`);
}

function anyTableHeaderPattern(): RegExp {
    return /^\s*\[\s*[^\]]+\s*\]\s*$/;
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
    if (config.get<boolean>('installCodexConfig', false)) {
        return true;
    }
    return fs.existsSync(getCodexHome());
}

function escapeTomlString(value: string): string {
    return value
        .replace(/\\/g, '\\\\')
        .replace(/"/g, '\\"')
        .replace(/\n/g, '\\n')
        .replace(/\r/g, '\\r')
        .replace(/\t/g, '\\t');
}

function renderArgs(args: string[]): string {
    return '[' + args.map((arg) => `"${escapeTomlString(arg)}"`).join(', ') + ']';
}

function renderManagedBlock(serverKey: string, spec: CodexServerSpec): string {
    const lines: string[] = [
        '# Managed by asset-aware-mcp VS Code extension. Remove this block to opt out.',
        `[mcp_servers.${serverKey}]`,
        `command = "${escapeTomlString(spec.command)}"`,
        `args = ${renderArgs(spec.args)}`,
    ];

    const envKeys = Object.keys(spec.env).sort();
    if (envKeys.length > 0) {
        lines.push('', `[mcp_servers.${serverKey}.env]`);
        for (const key of envKeys) {
            lines.push(`${key} = "${escapeTomlString(spec.env[key])}"`);
        }
    }

    return lines.join('\n') + '\n';
}

function envBlockHeaderPattern(serverKey: string): RegExp {
    const escapedKey = serverKey.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return new RegExp(`^\\s*\\[\\s*mcp_servers\\.${escapedKey}\\.env\\s*\\]\\s*$`);
}

function parseTomlStringValue(value: string): string | undefined {
    const trimmed = value.trim();
    if (trimmed.startsWith("'") && trimmed.endsWith("'") && trimmed.length >= 2) {
        return trimmed.slice(1, -1);
    }
    if (!trimmed.startsWith('"') || !trimmed.endsWith('"') || trimmed.length < 2) {
        return undefined;
    }

    let out = '';
    for (let i = 1; i < trimmed.length - 1; i += 1) {
        const char = trimmed[i];
        if (char !== '\\') {
            out += char;
            continue;
        }
        i += 1;
        const escaped = trimmed[i];
        if (escaped === undefined || i >= trimmed.length - 1) {
            return undefined;
        }
        switch (escaped) {
            case 'n':
                out += '\n';
                break;
            case 'r':
                out += '\r';
                break;
            case 't':
                out += '\t';
                break;
            case '"':
            case '\\':
                out += escaped;
                break;
            default:
                out += escaped;
                break;
        }
    }
    return out;
}

function extractManagedEnv(block: string | undefined, serverKey: string): Record<string, string> | undefined {
    if (!block) {
        return undefined;
    }

    const envHeader = envBlockHeaderPattern(serverKey);
    const anyHeader = anyTableHeaderPattern();
    const env: Record<string, string> = {};
    let inEnv = false;

    for (const rawLine of block.split(/\r?\n/)) {
        if (envHeader.test(rawLine)) {
            inEnv = true;
            continue;
        }
        if (!inEnv) {
            continue;
        }
        if (anyHeader.test(rawLine)) {
            break;
        }

        const line = stripTomlComment(rawLine).trim();
        if (!line) {
            continue;
        }
        const eqIndex = line.indexOf('=');
        if (eqIndex <= 0) {
            continue;
        }
        const key = line.slice(0, eqIndex).trim();
        if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) {
            continue;
        }
        const parsed = parseTomlStringValue(line.slice(eqIndex + 1));
        if (parsed !== undefined) {
            env[key] = parsed;
        }
    }

    return Object.keys(env).length > 0 ? env : undefined;
}

function extractManagedBlock(content: string, serverKey: string): string | undefined {
    const lines = content.split(/\r?\n/);
    const headerRe = blockHeaderPattern(serverKey);
    const anyHeader = anyTableHeaderPattern();
    const blockLines: string[] = [];
    let inBlock = false;

    for (const line of lines) {
        if (inBlock) {
            if (headerRe.test(line)) {
                blockLines.push(line);
                continue;
            }
            if (anyHeader.test(line)) {
                break;
            }
            blockLines.push(line);
            continue;
        }

        if (headerRe.test(line)) {
            inBlock = true;
            blockLines.push(line);
        }
    }

    return blockLines.length > 0 ? blockLines.join('\n') : undefined;
}

function blockLooksManagedOrAssetAware(block: string | undefined): boolean {
    if (!block) {
        return true;
    }
    const body = block
        .split(/\r?\n/)
        .filter((line) => !blockHeaderPattern(ASSET_AWARE_SERVER_KEY).test(line))
        .join('\n');
    return block.includes('Managed by asset-aware-mcp VS Code extension')
        || body.includes(ASSET_AWARE_SERVER_KEY)
        || block.includes('src.server');
}

function stripManagedBlock(content: string, serverKey: string): StripResult {
    const existingBlock = extractManagedBlock(content, serverKey);
    if (existingBlock && !blockLooksManagedOrAssetAware(existingBlock)) {
        return { content, removed: false, blockedByCustom: true };
    }

    const lines = content.split(/\r?\n/);
    const headerRe = blockHeaderPattern(serverKey);
    const anyHeader = anyTableHeaderPattern();
    const out: string[] = [];
    let removed = false;
    let inManaged = false;

    for (const line of lines) {
        if (inManaged) {
            if (headerRe.test(line)) {
                removed = true;
                continue;
            }
            if (anyHeader.test(line)) {
                inManaged = false;
                out.push(line);
                continue;
            }
            removed = true;
            continue;
        }

        if (headerRe.test(line)) {
            inManaged = true;
            removed = true;
            while (out.length > 0 && out[out.length - 1].trim() === '') {
                out.pop();
            }
            if (out.length > 0 && out[out.length - 1].includes('Managed by asset-aware-mcp VS Code extension')) {
                out.pop();
            }
            continue;
        }

        out.push(line);
    }

    return {
        content: out.join('\n').replace(/\n{3,}$/g, '\n\n'),
        removed,
        blockedByCustom: false,
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

function warnSkippedConfigWrite(configPath: string, reason: string): void {
    vscode.window.showWarningMessage(
        `Asset-Aware MCP skipped updating ${configPath}: ${reason}`,
    );
}

function hasSuspiciousTomlSyntax(content: string): boolean {
    const seenTables = new Set<string>();
    for (const rawLine of content.split(/\r?\n/)) {
        const line = rawLine.trim();
        if (!line || line.startsWith('#')) {
            continue;
        }
        if (line.startsWith('[') && !/^\[\[?[^\]]+\]\]?(?:\s*#.*)?$/.test(line)) {
            return true;
        }
        if (line.startsWith('[')) {
            const tableName = line.replace(/\s*#.*$/, '').replace(/^\[\[?/, '').replace(/\]\]?$/, '').trim();
            if (seenTables.has(tableName)) {
                return true;
            }
            seenTables.add(tableName);
            continue;
        }
        if (line.includes('=') && !hasBalancedTomlValue(stripTomlComment(line).split(/=(.*)/s)[1] ?? '')) {
            return true;
        }
    }
    return false;
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

function hasBalancedTomlValue(value: string): boolean {
    const stack: string[] = [];
    let inString: '"' | "'" | '' = '';
    let escaping = false;
    for (const char of value.trim()) {
        if (inString) {
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
            continue;
        }
        if (char === '[' || char === '{') {
            stack.push(char === '[' ? ']' : '}');
            continue;
        }
        if (char === ']' || char === '}') {
            if (stack.pop() !== char) {
                return false;
            }
        }
    }
    return !inString && stack.length === 0;
}

function readConfig(configPath: string): string | undefined {
    if (!fs.existsSync(configPath)) {
        return '';
    }
    try {
        return fs.readFileSync(configPath, 'utf-8');
    } catch {
        try {
            fs.copyFileSync(configPath, `${configPath}.unreadable.${Date.now()}.bak`);
        } catch {
            // Best-effort backup only.
        }
        warnSkippedConfigWrite(configPath, 'the file could not be read. Please fix permissions and retry.');
        return undefined;
    }
}

function writeConfigAtomic(configPath: string, content: string): void {
    fs.mkdirSync(path.dirname(configPath), { recursive: true });
    const tmpPath = `${configPath}.tmp.${Date.now()}`;
    fs.writeFileSync(tmpPath, content, 'utf-8');
    fs.renameSync(tmpPath, configPath);
}

export function installCodexMcpServer(
    context: vscode.ExtensionContext,
    uvPath: string,
    needsUpgrade: boolean = false,
): boolean {
    if (!isCodexAvailable()) {
        return false;
    }

    const configPath = getCodexConfigPath();
    const launch = buildAssetAwareLaunchSpec(context, uvPath, { needsUpgrade });
    if (!isAssetAwareLaunch(launch.command, launch.args)) {
        return false;
    }

    let content = readConfig(configPath);
    if (content === undefined) {
        return false;
    }
    if (hasSuspiciousTomlSyntax(content)) {
        warnSkippedConfigWrite(configPath, 'the TOML structure looks malformed. Please fix the file and retry.');
        return false;
    }
    const original = content;
    const existingBlock = extractManagedBlock(content, ASSET_AWARE_SERVER_KEY);
    const stripped = stripManagedBlock(content, ASSET_AWARE_SERVER_KEY);
    if (stripped.blockedByCustom) {
        return false;
    }
    const existingEnv = extractManagedEnv(existingBlock, ASSET_AWARE_SERVER_KEY);
    const spec: CodexServerSpec = {
        command: launch.command,
        args: launch.args,
        env: mergeManagedEnv(existingEnv, launch.env) ?? {},
    };

    content = ensureTrailingBlankLine(stripped.content) + renderManagedBlock(ASSET_AWARE_SERVER_KEY, spec);
    if (content === original) {
        return false;
    }

    writeConfigAtomic(configPath, content);
    return true;
}

export function removeCodexMcpServer(): boolean {
    const configPath = getCodexConfigPath();
    if (!fs.existsSync(configPath)) {
        return false;
    }

    const original = readConfig(configPath);
    if (original === undefined) {
        return false;
    }
    const stripped = stripManagedBlock(original, ASSET_AWARE_SERVER_KEY);
    if (stripped.blockedByCustom || !stripped.removed) {
        return false;
    }

    writeConfigAtomic(configPath, stripped.content);
    return true;
}

export const __test__ = {
    escapeTomlString,
    renderManagedBlock,
    stripManagedBlock,
    extractManagedBlock,
    hasSuspiciousTomlSyntax,
    stripTomlComment,
    hasBalancedTomlValue,
};
