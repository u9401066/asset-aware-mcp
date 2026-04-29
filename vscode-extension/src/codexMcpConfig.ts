import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import * as vscode from 'vscode';
import {
    ASSET_AWARE_SERVER_KEY,
    buildAssetAwareLaunchSpec,
    isAssetAwareLaunch,
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

function readConfig(configPath: string): string {
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
        return '';
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
    const spec: CodexServerSpec = {
        command: launch.command,
        args: launch.args,
        env: launch.env,
    };

    if (!isAssetAwareLaunch(spec.command, spec.args)) {
        return false;
    }

    let content = readConfig(configPath);
    const original = content;
    const stripped = stripManagedBlock(content, ASSET_AWARE_SERVER_KEY);
    if (stripped.blockedByCustom) {
        return false;
    }

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
};
