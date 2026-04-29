import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';
import {
    ASSET_AWARE_SERVER_KEY,
    buildAssetAwareLaunchSpec,
    entriesEqual,
    isAssetAwareLaunch,
} from './mcpConfigCommon';

const CLINE_EXTENSION_ID = 'saoudrizwan.claude-dev';
const CLINE_SETTINGS_SUBDIR = 'settings';
const CLINE_MCP_SETTINGS_FILE = 'cline_mcp_settings.json';

interface ClineMcpServerEntry {
    command: string;
    args: string[];
    env?: Record<string, string>;
    alwaysAllow?: string[];
    disabled?: boolean;
    [key: string]: unknown;
}

interface ClineMcpSettings {
    mcpServers: Record<string, ClineMcpServerEntry>;
    mcpRules?: Record<string, unknown>;
    [key: string]: unknown;
}

function getClineMcpSettingsPath(context: vscode.ExtensionContext): string {
    const globalStorageDir = path.dirname(context.globalStorageUri.fsPath);
    return path.join(globalStorageDir, CLINE_EXTENSION_ID, CLINE_SETTINGS_SUBDIR, CLINE_MCP_SETTINGS_FILE);
}

function readClineSettings(settingsPath: string): ClineMcpSettings {
    if (!fs.existsSync(settingsPath)) {
        return { mcpServers: {} };
    }

    try {
        const raw = fs.readFileSync(settingsPath, 'utf-8');
        const parsed = JSON.parse(raw) as ClineMcpSettings;
        if (!parsed.mcpServers || typeof parsed.mcpServers !== 'object') {
            parsed.mcpServers = {};
        }
        return parsed;
    } catch {
        const backupPath = `${settingsPath}.invalid.${Date.now()}.bak`;
        try {
            fs.copyFileSync(settingsPath, backupPath);
        } catch {
            // Best-effort backup only.
        }
        return { mcpServers: {} };
    }
}

function writeClineSettings(settingsPath: string, settings: ClineMcpSettings): void {
    fs.mkdirSync(path.dirname(settingsPath), { recursive: true });
    const tmpPath = `${settingsPath}.tmp.${Date.now()}.json`;
    fs.writeFileSync(tmpPath, JSON.stringify(settings, null, 2) + '\n', 'utf-8');
    fs.renameSync(tmpPath, settingsPath);
}

function mergeManagedEntry(
    existing: ClineMcpServerEntry | undefined,
    next: ClineMcpServerEntry,
): ClineMcpServerEntry {
    if (!existing || !isAssetAwareLaunch(existing.command, existing.args)) {
        return next;
    }

    return {
        ...existing,
        ...next,
        disabled: existing.disabled ?? next.disabled,
        alwaysAllow: existing.alwaysAllow,
    };
}

function mergeAssetAwareRules(settings: ClineMcpSettings): boolean {
    const rules = settings.mcpRules && typeof settings.mcpRules === 'object' ? settings.mcpRules : {};
    const existingCategory = rules['assetAwareDocs'];
    const category: Record<string, unknown> =
        existingCategory && typeof existingCategory === 'object' && !Array.isArray(existingCategory)
            ? { ...(existingCategory as Record<string, unknown>) }
            : {};

    const servers = Array.isArray(category['servers']) ? [...category['servers'].map(String)] : [];
    if (!servers.includes(ASSET_AWARE_SERVER_KEY)) {
        servers.push(ASSET_AWARE_SERVER_KEY);
    }

    const triggers = Array.isArray(category['triggers']) ? [...category['triggers'].map(String)] : [];
    for (const trigger of [
        'asset-aware',
        'asset aware',
        'document asset',
        'citation-ready',
        'craap',
        'dfm',
        'docx',
        'pdf',
        'table',
        'figure',
        'lightrag',
        '引用',
        '證據',
        '表格',
        '圖片',
        '文件',
    ]) {
        if (!triggers.includes(trigger)) {
            triggers.push(trigger);
        }
    }

    category['servers'] = servers;
    category['triggers'] = triggers;
    category['description'] = category['description']
        ?? 'Asset-aware document tools for PDF/DOCX/DFM assets, citation spans, tables, figures, and LightRAG.';

    const nextRules = {
        ...rules,
        assetAwareDocs: category,
    };
    const changed = !entriesEqual(settings.mcpRules ?? {}, nextRules);
    settings.mcpRules = nextRules;
    return changed;
}

export function isClineInstalled(context: vscode.ExtensionContext): boolean {
    const config = vscode.workspace.getConfiguration('assetAwareMcp');
    if (config.get<boolean>('installClineConfig', false)) {
        return true;
    }
    if (vscode.extensions.getExtension(CLINE_EXTENSION_ID)) {
        return true;
    }

    const globalStorageDir = path.dirname(context.globalStorageUri.fsPath);
    return fs.existsSync(path.join(globalStorageDir, CLINE_EXTENSION_ID));
}

export function installClineMcpServer(
    context: vscode.ExtensionContext,
    uvPath: string,
    needsUpgrade: boolean = false,
): boolean {
    if (!isClineInstalled(context)) {
        return false;
    }

    const settingsPath = getClineMcpSettingsPath(context);
    const settings = readClineSettings(settingsPath);
    const launch = buildAssetAwareLaunchSpec(context, uvPath, { needsUpgrade });
    const nextEntry: ClineMcpServerEntry = {
        command: launch.command,
        args: launch.args,
        env: launch.env,
        disabled: false,
    };

    const existing = settings.mcpServers[ASSET_AWARE_SERVER_KEY];
    if (existing && !isAssetAwareLaunch(existing.command, existing.args)) {
        return false;
    }

    const merged = mergeManagedEntry(existing, nextEntry);
    let changed = !existing || !entriesEqual(existing, merged);
    if (changed) {
        settings.mcpServers[ASSET_AWARE_SERVER_KEY] = merged;
    }

    changed = mergeAssetAwareRules(settings) || changed;
    if (!changed) {
        return false;
    }

    writeClineSettings(settingsPath, settings);
    return true;
}

export function removeClineMcpServer(context: vscode.ExtensionContext): boolean {
    const settingsPath = getClineMcpSettingsPath(context);
    if (!fs.existsSync(settingsPath)) {
        return false;
    }

    const settings = readClineSettings(settingsPath);
    const existing = settings.mcpServers[ASSET_AWARE_SERVER_KEY];
    if (!existing || !isAssetAwareLaunch(existing.command, existing.args)) {
        return false;
    }

    delete settings.mcpServers[ASSET_AWARE_SERVER_KEY];
    writeClineSettings(settingsPath, settings);
    return true;
}

export const __test__ = {
    getClineMcpSettingsPath,
    readClineSettings,
    mergeAssetAwareRules,
};
