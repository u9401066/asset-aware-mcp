/**
 * DFM Editor Service
 *
 * Manages docx ↔ DFM lifecycle:
 *  1. Open .docx → call MCP ingest_docx → get .dfm
 *  2. User edits .dfm in VS Code (markdown mode)
 *  3. Save → call MCP save_docx → write back to .docx
 *
 * Tracks open sessions to map .dfm files back to their source .docx.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

const CONTEXT_DFM_TRACKED = 'assetAwareMcp.dfmTracked';
const SESSION_STORAGE_KEY = 'assetAwareMcp.dfmSessions';

export function normalizeSessionPath(
    filePath: string,
    platform: NodeJS.Platform = process.platform,
): string {
    if (platform === 'win32') {
        return path.win32.normalize(path.win32.resolve(filePath)).toLowerCase();
    }

    return path.normalize(path.resolve(filePath));
}

/** Represents an active DFM editing session */
export interface DfmSession {
    /** Unique doc_id from MCP server */
    docId: string;
    /** Absolute path to the original .docx file */
    docxPath: string;
    /** Absolute path to the generated .dfm file */
    dfmPath: string;
    /** Absolute path to the session data directory */
    dataDir: string;
    /** Timestamp when the session was created */
    createdAt: number;
    /** Whether the .dfm has unsaved changes relative to .docx */
    dirty: boolean;
    /** Source DOCX mtime when this DFM session was created or last saved. */
    sourceMtimeMs?: number;
}

/** Result from MCP ingest_docx tool */
export interface IngestResult {
    doc_id: string;
    dfm_path: string;
    data_dir: string;
    blocks: number;
    assets: number;
    editable_blocks: number;
}

/** Result from MCP save_docx tool */
export interface SaveResult {
    /** Final user-facing DOCX path after any extension-side copy. */
    saved: string;
    /** Server-created DOCX artifact path under the MCP data directory. */
    output_path: string;
    blocks_updated: number;
}

/**
 * Manages DFM editing sessions.
 * Pure logic — no direct VS Code API calls for testability.
 */
export class DfmSessionManager {
    private sessions = new Map<string, DfmSession>();

    /** Register a new editing session */
    addSession(session: DfmSession): void {
        session.docxPath = normalizeSessionPath(session.docxPath);
        session.dfmPath = normalizeSessionPath(session.dfmPath);
        session.dataDir = normalizeSessionPath(session.dataDir);
        this.sessions.set(session.dfmPath, session);
    }

    /** Get session by .dfm file path */
    getSessionByDfm(dfmPath: string): DfmSession | undefined {
        return this.sessions.get(normalizeSessionPath(dfmPath));
    }

    /** Get session by doc_id */
    getSessionByDocId(docId: string): DfmSession | undefined {
        for (const session of this.sessions.values()) {
            if (session.docId === docId) {
                return session;
            }
        }
        return undefined;
    }

    /** Get session by .docx path */
    getSessionByDocx(docxPath: string): DfmSession | undefined {
        const normalizedDocxPath = normalizeSessionPath(docxPath);
        for (const session of this.sessions.values()) {
            if (session.docxPath === normalizedDocxPath) {
                return session;
            }
        }
        return undefined;
    }

    /** Remove a session */
    removeSession(dfmPath: string): boolean {
        return this.sessions.delete(normalizeSessionPath(dfmPath));
    }

    /** Mark session as dirty/clean */
    setDirty(dfmPath: string, dirty: boolean): void {
        const session = this.sessions.get(normalizeSessionPath(dfmPath));
        if (session) {
            session.dirty = dirty;
        }
    }

    /** Get all active sessions */
    getAllSessions(): DfmSession[] {
        return Array.from(this.sessions.values());
    }

    /** Check if a file path is a tracked .dfm file */
    isDfmTracked(filePath: string): boolean {
        return this.sessions.has(normalizeSessionPath(filePath));
    }

    /** Get count of active sessions */
    get size(): number {
        return this.sessions.size;
    }
}

/**
 * VS Code integration for DFM editing.
 * Handles commands, file watchers, and MCP tool calls.
 */
export class DfmEditorService implements vscode.Disposable {
    private readonly sessionManager = new DfmSessionManager();
    private readonly disposables: vscode.Disposable[] = [];
    private readonly outputChannel: vscode.OutputChannel;

    constructor(
        private readonly context: vscode.ExtensionContext,
        outputChannel?: vscode.OutputChannel,
    ) {
        this.outputChannel = outputChannel ??
            vscode.window.createOutputChannel('Asset-Aware DFM');

        this.registerFileWatcher();
        this.restorePersistedSessions();
        this.updateDfmTrackedContext(vscode.window.activeTextEditor);
    }

    /** Expose session manager for testing */
    get sessions(): DfmSessionManager {
        return this.sessionManager;
    }

    /**
     * Open a .docx file as DFM for editing.
     * Calls MCP ingest_docx, then opens the resulting .dfm in editor.
     */
    async openDocxAsDfm(docxPath: string): Promise<void> {
        // Check if already open
        const existing = this.sessionManager.getSessionByDocx(docxPath);
        if (existing) {
            if (!fs.existsSync(existing.dfmPath)) {
                this.sessionManager.removeSession(existing.dfmPath);
                this.persistSessions();
            } else {
                // Just open the existing .dfm
                const doc = await vscode.workspace.openTextDocument(existing.dfmPath);
                await vscode.window.showTextDocument(doc, { preview: false });
                return;
            }
        }

        const result = await vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: `Converting ${path.basename(docxPath)} to DFM...`,
                cancellable: false,
            },
            async () => {
                return await this.callMcpIngest(docxPath);
            },
        );

        if (!result) {
            vscode.window.showErrorMessage(
                `Failed to convert ${path.basename(docxPath)} to DFM`,
            );
            return;
        }

        const session: DfmSession = {
            docId: result.doc_id,
            docxPath: docxPath,
            dfmPath: result.dfm_path,
            dataDir: result.data_dir,
            createdAt: Date.now(),
            dirty: false,
            sourceMtimeMs: this.getMtimeMs(docxPath),
        };

        this.sessionManager.addSession(session);
        this.persistSessions();

        // Open the .dfm file
        const doc = await vscode.workspace.openTextDocument(session.dfmPath);
        const editor = await vscode.window.showTextDocument(doc, { preview: false });

        // Set language to markdown for syntax highlighting
        await vscode.languages.setTextDocumentLanguage(doc, 'markdown');
        this.updateDfmTrackedContext(editor);

        this.log(`Opened ${path.basename(docxPath)} as DFM (${result.blocks} blocks, ${result.assets} assets)`);

        vscode.window.showInformationMessage(
            `✅ ${path.basename(docxPath)} → DFM (${result.editable_blocks} editable blocks)`,
        );
    }

    /**
     * Save a .dfm file back to .docx.
     */
    async saveDfmToDocx(dfmPath: string, outputPath?: string): Promise<boolean> {
        const session = this.sessionManager.getSessionByDfm(dfmPath);
        if (!session) {
            vscode.window.showWarningMessage('This file is not tracked as a DFM session.');
            return false;
        }

        const openDocument = vscode.workspace.textDocuments?.find(
            doc => normalizeSessionPath(doc.uri.fsPath) === normalizeSessionPath(dfmPath),
        );
        if (openDocument?.isDirty) {
            const saved = await openDocument.save();
            if (!saved) {
                vscode.window.showErrorMessage('DFM file has unsaved editor changes and could not be saved.');
                return false;
            }
        }

        const result = await vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: `Saving back to ${path.basename(session.docxPath)}...`,
                cancellable: false,
            },
            async () => {
                return await this.callMcpSave(session.docId);
            },
        );

        if (!result) {
            vscode.window.showErrorMessage('Failed to save DFM back to docx');
            return false;
        }

        const targetPath = outputPath ?? session.docxPath;
        if (!await this.confirmNoSourceConflict(session, targetPath)) {
            return false;
        }
        try {
            this.copyServerOutputToTarget(result.output_path, targetPath);
            result.saved = targetPath;
            session.sourceMtimeMs = this.getMtimeMs(targetPath);
        } catch (error) {
            this.log(`Failed to copy DFM output to target: ${error}`);
            vscode.window.showErrorMessage(`Failed to write DOCX target: ${error}`);
            return false;
        }

        this.sessionManager.setDirty(dfmPath, false);
        this.persistSessions();
        this.log(`Saved ${path.basename(session.docxPath)} (${result.blocks_updated} blocks updated)`);

        vscode.window.showInformationMessage(
            `✅ Saved to ${path.basename(result.saved)} (${result.blocks_updated} blocks updated)`,
        );

        return true;
    }

    /**
     * Close a DFM session and clean up.
     */
    async closeSession(dfmPath: string): Promise<void> {
        const session = this.sessionManager.getSessionByDfm(dfmPath);
        if (!session) {
            return;
        }

        if (session.dirty) {
            const choice = await vscode.window.showWarningMessage(
                `${path.basename(session.docxPath)} has unsaved DFM changes. Save back to docx?`,
                'Save', 'Discard', 'Cancel',
            );
            if (choice === 'Save') {
                const saved = await this.saveDfmToDocx(dfmPath);
                if (!saved) {
                    return;
                }
            } else if (choice === 'Cancel') {
                return;
            }
        }

        this.sessionManager.removeSession(dfmPath);
        this.persistSessions();
        this.updateDfmTrackedContext(vscode.window.activeTextEditor);
        this.log(`Closed DFM session for ${path.basename(session.docxPath)}`);
    }

    /** Register commands with VS Code */
    registerCommands(): void {
        this.disposables.push(
            vscode.commands.registerCommand(
                'assetAwareMcp.openDocxAsDfm',
                async (uri?: vscode.Uri) => {
                    let docxPath: string;
                    if (uri) {
                        docxPath = uri.fsPath;
                    } else {
                        const uris = await vscode.window.showOpenDialog({
                            filters: { 'Word Documents': ['docx', 'doc'] },
                            canSelectMany: false,
                        });
                        if (!uris || uris.length === 0) {
                            return;
                        }
                        docxPath = uris[0].fsPath;
                    }
                    await this.openDocxAsDfm(docxPath);
                },
            ),
        );

        this.disposables.push(
            vscode.commands.registerCommand(
                'assetAwareMcp.saveDfmToDocx',
                async () => {
                    const editor = vscode.window.activeTextEditor;
                    if (!editor) {
                        return;
                    }
                    const dfmPath = editor.document.uri.fsPath;
                    await this.saveDfmToDocx(dfmPath);
                },
            ),
        );

        this.disposables.push(
            vscode.commands.registerCommand(
                'assetAwareMcp.saveDfmToDocxAs',
                async () => {
                    const editor = vscode.window.activeTextEditor;
                    if (!editor) {
                        return;
                    }
                    const dfmPath = editor.document.uri.fsPath;
                    const session = this.sessionManager.getSessionByDfm(dfmPath);
                    if (!session) {
                        vscode.window.showWarningMessage('This file is not tracked as a DFM session.');
                        return;
                    }

                    const uri = await vscode.window.showSaveDialog({
                        defaultUri: vscode.Uri.file(session.docxPath),
                        filters: { 'Word Documents': ['docx'] },
                    });
                    if (uri) {
                        await this.saveDfmToDocx(dfmPath, uri.fsPath);
                    }
                },
            ),
        );

        this.disposables.push(
            vscode.commands.registerCommand(
                'assetAwareMcp.closeDfmSession',
                async () => {
                    const editor = vscode.window.activeTextEditor;
                    if (!editor) {
                        return;
                    }
                    await this.closeSession(editor.document.uri.fsPath);
                },
            ),
        );

        this.disposables.push(
            vscode.commands.registerCommand(
                'assetAwareMcp.listDfmSessions',
                () => {
                    const sessions = this.sessionManager.getAllSessions();
                    if (sessions.length === 0) {
                        vscode.window.showInformationMessage('No active DFM sessions.');
                        return;
                    }

                    const items = sessions.map(s => ({
                        label: path.basename(s.docxPath),
                        description: s.dirty ? '(modified)' : '',
                        detail: s.docxPath,
                        session: s,
                    }));

                    vscode.window.showQuickPick(items, {
                        placeHolder: 'Select a DFM session to open',
                    }).then(async selected => {
                        if (selected) {
                            const doc = await vscode.workspace.openTextDocument(
                                selected.session.dfmPath,
                            );
                            await vscode.window.showTextDocument(doc);
                        }
                    });
                },
            ),
        );
    }

    /** Watch for .dfm file changes to mark sessions dirty */
    private registerFileWatcher(): void {
        const activeEditorWatcher = vscode.window.onDidChangeActiveTextEditor(editor => {
            this.updateDfmTrackedContext(editor);
        });
        this.disposables.push(activeEditorWatcher);

        const watcher = vscode.workspace.onDidChangeTextDocument(e => {
            const filePath = e.document.uri.fsPath;
            if (this.sessionManager.isDfmTracked(filePath) && e.contentChanges.length > 0) {
                this.sessionManager.setDirty(filePath, true);
            }
        });
        this.disposables.push(watcher);

        // Watch for file close to clean up sessions
        const closeWatcher = vscode.workspace.onDidCloseTextDocument(doc => {
            const filePath = doc.uri.fsPath;
            if (this.sessionManager.isDfmTracked(filePath)) {
                // Don't auto-remove — user might reopen
                this.log(`DFM file closed: ${path.basename(filePath)}`);
            }
        });
        this.disposables.push(closeWatcher);
    }

    private updateDfmTrackedContext(editor?: vscode.TextEditor): void {
        const isTracked = editor
            ? this.sessionManager.isDfmTracked(editor.document.uri.fsPath)
            : false;
        vscode.commands.executeCommand('setContext', CONTEXT_DFM_TRACKED, isTracked).then(
            undefined,
            error => this.log(`Failed to update DFM context: ${error}`),
        );
    }

    private restorePersistedSessions(): void {
        const stored = this.context.workspaceState?.get<DfmSession[]>(SESSION_STORAGE_KEY, []) ?? [];
        let restored = 0;
        for (const session of stored) {
            if (!session.dfmPath || !session.docxPath || !fs.existsSync(session.dfmPath)) {
                continue;
            }
            this.sessionManager.addSession(session);
            restored += 1;
        }
        if (restored !== stored.length) {
            this.persistSessions();
        }
    }

    private persistSessions(): void {
        const workspaceState = this.context.workspaceState;
        if (!workspaceState) {
            return;
        }
        workspaceState.update(SESSION_STORAGE_KEY, this.sessionManager.getAllSessions()).then(
            undefined,
            error => this.log(`Failed to persist DFM sessions: ${error}`),
        );
    }

    /**
     * Call MCP ingest_docx tool.
     * In production, this calls the MCP server via the tool interface.
     * Subclass or mock for testing.
     */
    protected async callMcpIngest(docxPath: string): Promise<IngestResult | null> {
        try {
            // Use VS Code's MCP tool calling mechanism
            const tools = await vscode.lm.tools;
            const ingestTool = tools.find(t => t.name === 'ingest_docx');

            if (!ingestTool) {
                this.log('ERROR: ingest_docx MCP tool not found');
                return null;
            }

            const result = await vscode.lm.invokeTool(ingestTool.name, {
                input: { file_path: docxPath },
                toolInvocationToken: undefined,
            });

            // Parse the result
            const text = result.content
                .filter((p): p is vscode.LanguageModelTextPart => p instanceof vscode.LanguageModelTextPart)
                .map(p => p.value)
                .join('');

            return this.parseIngestResult(text);
        } catch (error) {
            this.log(`MCP ingest_docx failed: ${error}`);
            return null;
        }
    }

    /**
     * Call MCP save_docx tool.
     */
    protected async callMcpSave(docId: string): Promise<SaveResult | null> {
        try {
            const tools = await vscode.lm.tools;
            const saveTool = tools.find(t => t.name === 'save_docx');

            if (!saveTool) {
                this.log('ERROR: save_docx MCP tool not found');
                return null;
            }

            const result = await vscode.lm.invokeTool(saveTool.name, {
                input: { doc_id: docId },
                toolInvocationToken: undefined,
            });

            const text = result.content
                .filter((p): p is vscode.LanguageModelTextPart => p instanceof vscode.LanguageModelTextPart)
                .map(p => p.value)
                .join('');

            return this.parseSaveResult(text);
        } catch (error) {
            this.log(`MCP save_docx failed: ${error}`);
            return null;
        }
    }

    protected parseIngestResult(text: string): IngestResult {
        const json = this.tryParseJson<Record<string, any>>(text);
        const docId = json?.doc_id ?? json?.docId;
        const dfmPath = json?.dfm_path ?? json?.dfmPath;
        if (json && docId && dfmPath) {
            return {
                doc_id: docId,
                dfm_path: dfmPath,
                data_dir: json.data_dir ?? json.dataDir ?? path.dirname(dfmPath),
                blocks: json.blocks ?? json.total_blocks ?? json.totalBlocks ?? 0,
                assets: json.assets ?? json.asset_count ?? json.assetCount ?? 0,
                editable_blocks: json.editable_blocks ?? json.editableBlocks ?? 0,
            };
        }

        const markdownDocId = this.extractMarkdownField(text, 'doc_id');
        const markdownDfmPath = this.extractMarkdownFieldAny(text, ['DFM 路徑', 'DFM path', 'dfm_path']);
        if (!markdownDocId || !markdownDfmPath) {
            throw new Error('Unable to parse ingest_docx result');
        }

        return {
            doc_id: markdownDocId,
            dfm_path: markdownDfmPath,
            data_dir: path.dirname(markdownDfmPath),
            blocks: this.extractMarkdownNumberAny(text, ['總區塊數', 'Total blocks', 'total_blocks', 'blocks']),
            assets: this.extractMarkdownNumberAny(text, ['資產數', 'Assets', 'assets']),
            editable_blocks: this.extractMarkdownNumberAny(text, ['可編輯區塊', 'Editable blocks', 'editable_blocks']),
        };
    }

    protected parseSaveResult(text: string): SaveResult {
        const json = this.tryParseJson<Record<string, any>>(text);
        const jsonOutputPath = json?.output_path ?? json?.saved;
        if (json && jsonOutputPath) {
            return {
                saved: json.saved ?? jsonOutputPath,
                output_path: jsonOutputPath,
                blocks_updated: json.blocks_updated ?? 0,
            };
        }

        const outputPath = this.extractMarkdownFieldAny(text, ['輸出路徑', 'Output path', 'output_path', 'saved']);
        if (!outputPath) {
            throw new Error('Unable to parse save_docx result');
        }

        return {
            saved: outputPath,
            output_path: outputPath,
            blocks_updated: this.extractBlocksUpdated(text),
        };
    }

    private tryParseJson<T>(text: string): T | null {
        const candidates = [text.trim()];
        const fenced = /```(?:json)?\s*([\s\S]*?)```/i.exec(text);
        if (fenced) {
            candidates.unshift(fenced[1].trim());
        }

        for (const candidate of candidates) {
            try {
                return JSON.parse(candidate) as T;
            } catch {
                // Try the next representation.
            }
        }
        return null;
    }

    private extractMarkdownField(text: string, label: string): string {
        const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const pattern = new RegExp(`^\\s*[-*]?\\s*\\*\\*${escaped}\\*\\*\\s*:\\s+\`?([^\\n\`]+)\`?`, 'im');
        return pattern.exec(text)?.[1]?.trim() ?? '';
    }

    private extractMarkdownFieldAny(text: string, labels: string[]): string {
        for (const label of labels) {
            const value = this.extractMarkdownField(text, label);
            if (value) {
                return value;
            }
        }
        return '';
    }

    private extractMarkdownNumber(text: string, label: string): number {
        const value = this.extractMarkdownField(text, label);
        const parsed = Number.parseInt(value, 10);
        return Number.isFinite(parsed) ? parsed : 0;
    }

    private extractMarkdownNumberAny(text: string, labels: string[]): number {
        for (const label of labels) {
            const parsed = this.extractMarkdownNumber(text, label);
            if (parsed) {
                return parsed;
            }
        }
        return 0;
    }

    private extractBlocksUpdated(text: string): number {
        const match = /(\d+)\s+blocks?\s+updated/i.exec(text);
        return match ? Number.parseInt(match[1], 10) : 0;
    }

    private copyServerOutputToTarget(serverOutputPath: string, targetPath: string): void {
        const source = normalizeSessionPath(serverOutputPath);
        const target = normalizeSessionPath(targetPath);
        if (source === target) {
            return;
        }
        if (!fs.existsSync(serverOutputPath)) {
            throw new Error(`Server output not found: ${serverOutputPath}`);
        }
        fs.mkdirSync(path.dirname(targetPath), { recursive: true });
        fs.copyFileSync(serverOutputPath, targetPath);
    }

    private getMtimeMs(filePath: string): number | undefined {
        try {
            return fs.statSync(filePath).mtimeMs;
        } catch {
            return undefined;
        }
    }

    private async confirmNoSourceConflict(session: DfmSession, targetPath: string): Promise<boolean> {
        if (normalizeSessionPath(targetPath) !== normalizeSessionPath(session.docxPath)) {
            return true;
        }
        const currentMtime = this.getMtimeMs(session.docxPath);
        if (
            currentMtime === undefined ||
            session.sourceMtimeMs === undefined ||
            currentMtime <= session.sourceMtimeMs + 1
        ) {
            return true;
        }

        const choice = await vscode.window.showWarningMessage(
            `${path.basename(session.docxPath)} changed on disk after this DFM session was opened. Overwrite it?`,
            'Overwrite',
            'Cancel',
        );
        return choice === 'Overwrite';
    }

    private log(message: string): void {
        const timestamp = new Date().toISOString();
        this.outputChannel.appendLine(`[DFM ${timestamp}] ${message}`);
    }

    dispose(): void {
        for (const d of this.disposables) {
            d.dispose();
        }
    }
}
