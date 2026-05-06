import * as fs from 'fs';
import { createHash } from 'crypto';
import * as path from 'path';
import * as vscode from 'vscode';

type InstallMode = 'auto' | 'manual';
type ManagedAssetManifest = {
    version: 1;
    files: Record<string, { sha256: string }>;
};

interface InstallSummary {
    installed: number;
    updated: number;
    preserved: number;
    removed: number;
    missingSources: string[];
}

function createSummary(): InstallSummary {
    return {
        installed: 0,
        updated: 0,
        preserved: 0,
        removed: 0,
        missingSources: [],
    };
}

const MANIFEST_RELATIVE_PATH = path.join('.asset-aware-mcp', 'assistant-assets.json');
const RETIRED_MANAGED_ASSET_FRAGMENTS = [
    '.github/zotero-research-workflow.md',
    '.github/agents/research.agent.md',
    '.claude/skills/pubmed-',
    '.claude/skills/pipeline-persistence/',
    '.cline/skills/pubmed-search-mcp-harness/',
    '.cline/skills/zotero-keeper-harness/',
    '.codex/skills/pubmed-search-mcp-harness/',
    '.codex/skills/zotero-keeper-harness/',
    '.clinerules/00-zotero-project.md',
    '.clinerules/10-zotero-python.md',
    '.clinerules/20-zotero-vscode-extension.md',
    '.clinerules/30-zotero-research-workflow.md',
    '.clinerules/40-zotero-release.md',
    '.clinerules/50-pubmed-project.md',
    '.clinerules/60-pubmed-python.md',
    '.clinerules/70-pubmed-mcp-tools.md',
    '.clinerules/80-pubmed-release.md',
    '.clinerules/workflows/pubmed-',
    '.clinerules/workflows/zotero-',
];

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

function sha256(content: string): string {
    return createHash('sha256').update(content, 'utf-8').digest('hex');
}

function normalizeManifestPath(workspaceRoot: string, destinationPath: string): string {
    return path.relative(workspaceRoot, destinationPath).replaceAll(path.sep, '/');
}

function loadManifest(workspaceRoot: string): ManagedAssetManifest {
    const manifestPath = path.join(workspaceRoot, MANIFEST_RELATIVE_PATH);
    if (!fs.existsSync(manifestPath)) {
        return { version: 1, files: {} };
    }

    try {
        const parsed = JSON.parse(fs.readFileSync(manifestPath, 'utf-8')) as ManagedAssetManifest;
        if (parsed.version !== 1 || !parsed.files || typeof parsed.files !== 'object') {
            return { version: 1, files: {} };
        }
        return parsed;
    } catch {
        return { version: 1, files: {} };
    }
}

function saveManifest(workspaceRoot: string, manifest: ManagedAssetManifest): void {
    const manifestPath = path.join(workspaceRoot, MANIFEST_RELATIVE_PATH);
    ensureParentDirectory(manifestPath);
    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n', 'utf-8');
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

function syncManagedFile(
    sourcePath: string,
    destinationPath: string,
    workspaceRoot: string,
    manifest: ManagedAssetManifest,
    summary: InstallSummary,
    activeRelativePaths?: Set<string>,
    options: { legacyManaged?: boolean } = {},
): void {
    const incoming = fs.readFileSync(sourcePath, 'utf-8');
    const incomingHash = sha256(incoming);
    const relativePath = normalizeManifestPath(workspaceRoot, destinationPath);
    activeRelativePaths?.add(relativePath);
    const existing = readUtf8IfExists(destinationPath);

    if (existing === undefined) {
        copyBundledFile(sourcePath, destinationPath);
        manifest.files[relativePath] = { sha256: incomingHash };
        summary.installed++;
        return;
    }

    const existingHash = sha256(existing);
    if (existingHash === incomingHash) {
        manifest.files[relativePath] = { sha256: incomingHash };
        return;
    }

    const priorHash = manifest.files[relativePath]?.sha256;
    if (priorHash && existingHash === priorHash) {
        copyBundledFile(sourcePath, destinationPath);
        manifest.files[relativePath] = { sha256: incomingHash };
        summary.updated++;
        return;
    }

    if (options.legacyManaged) {
        copyBundledFile(sourcePath, destinationPath);
        manifest.files[relativePath] = { sha256: incomingHash };
        summary.updated++;
        return;
    }

    // Fail closed: without a matching manifest hash, treat the file as user-owned.
    summary.preserved++;
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
    workspaceRoot: string,
    manifest: ManagedAssetManifest,
    summary: InstallSummary,
    activeRelativePaths?: Set<string>,
): void {
    if (!fs.existsSync(sourceDir)) {
        summary.missingSources.push(sourceDir);
        return;
    }

    for (const sourceFile of collectFilesRecursive(sourceDir)) {
        const relativePath = path.relative(sourceDir, sourceFile);
        const destinationFile = path.join(destinationDir, relativePath);
        syncManagedFile(
            sourceFile,
            destinationFile,
            workspaceRoot,
            manifest,
            summary,
            activeRelativePaths,
        );
    }
}

function syncFileWithDetector(
    sourcePath: string,
    destinationPath: string,
    detector: (content: string) => boolean,
    summary: InstallSummary,
    workspaceRoot: string,
    manifest: ManagedAssetManifest,
    mode: InstallMode,
    activeRelativePaths?: Set<string>,
): void {
    if (!fs.existsSync(sourcePath)) {
        summary.missingSources.push(sourcePath);
        return;
    }

    const existing = readUtf8IfExists(destinationPath);
    if (existing === undefined || detector(existing)) {
        const relativePath = normalizeManifestPath(workspaceRoot, destinationPath);
        syncManagedFile(
            sourcePath,
            destinationPath,
            workspaceRoot,
            manifest,
            summary,
            activeRelativePaths,
            {
                legacyManaged: existing !== undefined && manifest.files[relativePath] === undefined,
            },
        );
        return;
    }

    if (mode === 'manual') {
        summary.preserved++;
        return;
    }

    summary.preserved++;
}

function pruneRetiredManagedFiles(
    workspaceRoot: string,
    manifest: ManagedAssetManifest,
    activeRelativePaths: Set<string>,
    summary: InstallSummary,
    options: { onlyKnownRetired?: boolean } = {},
): void {
    for (const [relativePath, entry] of Object.entries({ ...manifest.files })) {
        if (activeRelativePaths.has(relativePath)) {
            continue;
        }
        if (
            options.onlyKnownRetired
            && !RETIRED_MANAGED_ASSET_FRAGMENTS.some((fragment) => relativePath.includes(fragment))
        ) {
            continue;
        }

        const destinationPath = path.join(workspaceRoot, relativePath);
        const existing = readUtf8IfExists(destinationPath);
        if (existing === undefined) {
            delete manifest.files[relativePath];
            continue;
        }

        if (sha256(existing) !== entry.sha256) {
            summary.preserved++;
            continue;
        }

        fs.rmSync(destinationPath, { force: true });
        delete manifest.files[relativePath];
        summary.removed++;
    }
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
    const manifest = loadManifest(workspaceRoot);
    const activeRelativePaths = new Set<string>();

    syncFileWithDetector(
        getAssetPath(context, 'AGENTS.md'),
        path.join(workspaceRoot, 'AGENTS.md'),
        isAssetAwareAgentsFile,
        summary,
        workspaceRoot,
        manifest,
        mode,
        activeRelativePaths,
    );
    syncFileWithDetector(
        getAssetPath(context, '.github', 'copilot-instructions.md'),
        path.join(workspaceRoot, '.github', 'copilot-instructions.md'),
        isAssetAwareCopilotInstructions,
        summary,
        workspaceRoot,
        manifest,
        mode,
        activeRelativePaths,
    );

    syncManagedDirectory(
        getAssetPath(context, '.github', 'agents'),
        path.join(workspaceRoot, '.github', 'agents'),
        workspaceRoot,
        manifest,
        summary,
        activeRelativePaths,
    );
    syncManagedDirectory(
        getAssetPath(context, '.github', 'bylaws'),
        path.join(workspaceRoot, '.github', 'bylaws'),
        workspaceRoot,
        manifest,
        summary,
        activeRelativePaths,
    );
    syncManagedDirectory(
        getAssetPath(context, '.claude', 'skills'),
        path.join(workspaceRoot, '.claude', 'skills'),
        workspaceRoot,
        manifest,
        summary,
        activeRelativePaths,
    );
    syncManagedDirectory(
        getAssetPath(context, '.cline', 'skills'),
        path.join(workspaceRoot, '.cline', 'skills'),
        workspaceRoot,
        manifest,
        summary,
        activeRelativePaths,
    );
    syncManagedDirectory(
        getAssetPath(context, '.codex', 'skills'),
        path.join(workspaceRoot, '.codex', 'skills'),
        workspaceRoot,
        manifest,
        summary,
        activeRelativePaths,
    );
    syncManagedDirectory(
        getAssetPath(context, '.clinerules'),
        path.join(workspaceRoot, '.clinerules'),
        workspaceRoot,
        manifest,
        summary,
        activeRelativePaths,
    );

    pruneRetiredManagedFiles(workspaceRoot, manifest, activeRelativePaths, summary, {
        onlyKnownRetired: summary.missingSources.length > 0,
    });
    saveManifest(workspaceRoot, manifest);

    if (mode === 'manual') {
        if (summary.missingSources.length > 0) {
            vscode.window.showWarningMessage(
                `Installed ${summary.installed} and updated ${summary.updated} assistant asset(s), but ${summary.missingSources.length} bundled source path(s) were missing.`,
            );
        } else if (summary.installed > 0 || summary.updated > 0 || summary.removed > 0) {
            vscode.window.showInformationMessage(
                `Installed ${summary.installed}, updated ${summary.updated}, and removed ${summary.removed} retired Asset-Aware assistant asset(s). Preserved ${summary.preserved} custom file(s).`,
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
