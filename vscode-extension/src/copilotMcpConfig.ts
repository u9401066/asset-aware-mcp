import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';
import {
    ASSET_AWARE_SERVER_KEY,
    buildAssetAwareLaunchSpec,
    entriesEqual,
    getPrimaryWorkspaceRoot,
    isAssetAwareLaunch,
} from './mcpConfigCommon';

interface CopilotMcpServerEntry {
    type: 'stdio';
    command: string;
    args: string[];
    env?: Record<string, string>;
    [key: string]: unknown;
}

interface CopilotMcpSettings {
    servers: Record<string, CopilotMcpServerEntry>;
    [key: string]: unknown;
}

function getCopilotMcpConfigPath(workspaceRoot: string): string {
    return path.join(workspaceRoot, '.vscode', 'mcp.json');
}

function warnSkippedConfigWrite(configPath: string): void {
    vscode.window.showWarningMessage(
        `Asset-Aware MCP skipped updating ${configPath} because it could not be parsed. Please fix the file and retry.`,
    );
}

function readCopilotSettings(configPath: string): CopilotMcpSettings | undefined {
    if (!fs.existsSync(configPath)) {
        return { servers: {} };
    }

    try {
        const parsed = JSON.parse(fs.readFileSync(configPath, 'utf-8')) as CopilotMcpSettings;
        if (!parsed.servers || typeof parsed.servers !== 'object') {
            parsed.servers = {};
        }
        return parsed;
    } catch {
        const backupPath = `${configPath}.invalid.${Date.now()}.bak`;
        try {
            fs.copyFileSync(configPath, backupPath);
        } catch {
            // Best-effort backup only.
        }
        warnSkippedConfigWrite(configPath);
        return undefined;
    }
}

function writeCopilotSettings(configPath: string, settings: CopilotMcpSettings): void {
    fs.mkdirSync(path.dirname(configPath), { recursive: true });
    const tmpPath = `${configPath}.tmp.${Date.now()}.json`;
    fs.writeFileSync(tmpPath, JSON.stringify(settings, null, 2) + '\n', 'utf-8');
    fs.renameSync(tmpPath, configPath);
}

function mergeManagedEntry(
    existing: CopilotMcpServerEntry | undefined,
    next: CopilotMcpServerEntry,
): CopilotMcpServerEntry {
    if (!existing || !isAssetAwareLaunch(existing.command, existing.args)) {
        return next;
    }

    return {
        ...existing,
        ...next,
        type: 'stdio',
    };
}

export function installCopilotMcpConfig(
    context: vscode.ExtensionContext,
    uvPath: string,
    needsUpgrade: boolean = false,
): boolean {
    const config = vscode.workspace.getConfiguration('assetAwareMcp');
    if (!config.get<boolean>('installCopilotWorkspaceConfig', true)) {
        return false;
    }

    const workspaceRoot = getPrimaryWorkspaceRoot();
    if (!workspaceRoot) {
        return false;
    }

    const configPath = getCopilotMcpConfigPath(workspaceRoot);
    const settings = readCopilotSettings(configPath);
    if (!settings) {
        return false;
    }
    const launch = buildAssetAwareLaunchSpec(context, uvPath, { workspaceRoot, needsUpgrade });
    const nextEntry: CopilotMcpServerEntry = {
        type: 'stdio',
        command: launch.command,
        args: launch.args,
        env: launch.env,
    };

    const existing = settings.servers[ASSET_AWARE_SERVER_KEY];
    if (existing && !isAssetAwareLaunch(existing.command, existing.args)) {
        return false;
    }

    const merged = mergeManagedEntry(existing, nextEntry);
    if (existing && entriesEqual(existing, merged)) {
        return false;
    }

    settings.servers[ASSET_AWARE_SERVER_KEY] = merged;
    writeCopilotSettings(configPath, settings);
    return true;
}

export function removeCopilotMcpConfig(): boolean {
    const workspaceRoot = getPrimaryWorkspaceRoot();
    if (!workspaceRoot) {
        return false;
    }

    const configPath = getCopilotMcpConfigPath(workspaceRoot);
    if (!fs.existsSync(configPath)) {
        return false;
    }

    const settings = readCopilotSettings(configPath);
    if (!settings) {
        return false;
    }
    const existing = settings.servers[ASSET_AWARE_SERVER_KEY];
    if (!existing || !isAssetAwareLaunch(existing.command, existing.args)) {
        return false;
    }

    delete settings.servers[ASSET_AWARE_SERVER_KEY];
    writeCopilotSettings(configPath, settings);
    return true;
}

export const __test__ = {
    getCopilotMcpConfigPath,
    readCopilotSettings,
};
