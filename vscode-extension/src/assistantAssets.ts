import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';

type InstallMode = 'auto' | 'manual';

interface InstallSummary {
    installed: number;
    updated: number;
    preserved: number;
    missingSources: string[];
}

function createSummary(): InstallSummary {
    return {
        installed: 0,
        updated: 0,
        preserved: 0,
        missingSources: [],
    };
}

function getAssetPath(context: vscode.ExtensionContext, ...segments: string[]): string {
    return path.join(context.extensionPath, 'resources', 'repo-assets', 'asset-aware', ...segments);
}

function ensureParentDirectory(filePath: string): void {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

function readUtf8IfExists(filePath: string): string | undefined {
    if (!fs.existsSync(filePath)) {
        return undefined;
    }
    return fs.readFileSync(filePath, 'utf-8');
}

function isAssetAwareCopilotInstructions(content: string): boolean {
    return content.includes('MCP Server — Asset-Aware Medical RAG')
        || content.includes('VSIX / MCP Harness 同步');
}

function isAssetAwareAgentsFile(content: string): boolean {
    return content.includes('# Asset-Aware MCP Codex Harness')
        && content.includes('citation-ready document workflows');
}

function copyBundledFile(sourcePath: string, destinationPath: string): boolean {
    ensureParentDirectory(destinationPath);
    const incoming = fs.readFileSync(sourcePath, 'utf-8');
    const existing = readUtf8IfExists(destinationPath);
    if (existing === incoming) {
        return false;
    }
    fs.writeFileSync(destinationPath, incoming, 'utf-8');
    return true;
}

function collectFilesRecursive(rootDir: string): string[] {
    const files: string[] = [];

    for (const entry of fs.readdirSync(rootDir, { withFileTypes: true })) {
        const fullPath = path.join(rootDir, entry.name);
        if (entry.isDirectory()) {
            files.push(...collectFilesRecursive(fullPath));
        } else if (entry.isFile()) {
            files.push(fullPath);
        }
    }

    return files;
}

function syncManagedDirectory(
    sourceDir: string,
    destinationDir: string,
    summary: InstallSummary,
    overwriteExisting: boolean,
): void {
    if (!fs.existsSync(sourceDir)) {
        summary.missingSources.push(sourceDir);
        return;
    }

    for (const sourceFile of collectFilesRecursive(sourceDir)) {
        const relativePath = path.relative(sourceDir, sourceFile);
        const destinationFile = path.join(destinationDir, relativePath);
        const alreadyExists = fs.existsSync(destinationFile);

        if (alreadyExists && !overwriteExisting) {
            summary.preserved++;
            continue;
        }

        if (!copyBundledFile(sourceFile, destinationFile)) {
            continue;
        }

        if (alreadyExists) {
            summary.updated++;
        } else {
            summary.installed++;
        }
    }
}

function syncFileWithDetector(
    sourcePath: string,
    destinationPath: string,
    detector: (content: string) => boolean,
    summary: InstallSummary,
    mode: InstallMode,
): void {
    if (!fs.existsSync(sourcePath)) {
        summary.missingSources.push(sourcePath);
        return;
    }

    const existing = readUtf8IfExists(destinationPath);
    if (!existing) {
        copyBundledFile(sourcePath, destinationPath);
        summary.installed++;
        return;
    }

    if (detector(existing)) {
        if (copyBundledFile(sourcePath, destinationPath)) {
            summary.updated++;
        }
        return;
    }

    if (mode === 'manual') {
        summary.preserved++;
        return;
    }

    summary.preserved++;
}

export async function installAssistantAssets(
    context: vscode.ExtensionContext,
    mode: InstallMode = 'auto',
): Promise<InstallSummary | undefined> {
    const config = vscode.workspace.getConfiguration('assetAwareMcp');
    if (mode === 'auto' && !config.get<boolean>('installAssistantAssets', true)) {
        return undefined;
    }

    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (!workspaceFolder) {
        if (mode === 'manual') {
            vscode.window.showWarningMessage('Please open a workspace folder first.');
        }
        return undefined;
    }

    if (mode === 'manual') {
        const choice = await vscode.window.showInformationMessage(
            'Install/update Asset-Aware MCP Copilot, Cline, and Codex harness assets? Existing custom instructions will be preserved.',
            'Install',
            'Cancel',
        );
        if (choice !== 'Install') {
            return undefined;
        }
    }

    const workspaceRoot = workspaceFolder.uri.fsPath;
    const summary = createSummary();

    syncFileWithDetector(
        getAssetPath(context, 'AGENTS.md'),
        path.join(workspaceRoot, 'AGENTS.md'),
        isAssetAwareAgentsFile,
        summary,
        mode,
    );
    syncFileWithDetector(
        getAssetPath(context, '.github', 'copilot-instructions.md'),
        path.join(workspaceRoot, '.github', 'copilot-instructions.md'),
        isAssetAwareCopilotInstructions,
        summary,
        mode,
    );

    syncManagedDirectory(
        getAssetPath(context, '.github', 'agents'),
        path.join(workspaceRoot, '.github', 'agents'),
        summary,
        true,
    );
    syncManagedDirectory(
        getAssetPath(context, '.cline', 'skills'),
        path.join(workspaceRoot, '.cline', 'skills'),
        summary,
        true,
    );
    syncManagedDirectory(
        getAssetPath(context, '.codex', 'skills'),
        path.join(workspaceRoot, '.codex', 'skills'),
        summary,
        true,
    );
    syncManagedDirectory(
        getAssetPath(context, '.clinerules'),
        path.join(workspaceRoot, '.clinerules'),
        summary,
        true,
    );

    if (mode === 'manual') {
        if (summary.missingSources.length > 0) {
            vscode.window.showWarningMessage(
                `Installed ${summary.installed} and updated ${summary.updated} assistant asset(s), but ${summary.missingSources.length} bundled source path(s) were missing.`,
            );
        } else if (summary.installed > 0 || summary.updated > 0) {
            vscode.window.showInformationMessage(
                `Installed ${summary.installed} and updated ${summary.updated} Asset-Aware assistant asset(s). Preserved ${summary.preserved} custom file(s).`,
            );
        } else {
            vscode.window.showInformationMessage(
                summary.preserved > 0
                    ? `No Asset-Aware assistant assets changed. Preserved ${summary.preserved} custom file(s).`
                    : 'No Asset-Aware assistant assets needed updating.',
            );
        }
    }

    return summary;
}

export const __test__ = {
    isAssetAwareCopilotInstructions,
    isAssetAwareAgentsFile,
};
