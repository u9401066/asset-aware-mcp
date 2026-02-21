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
    saved: string;
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
        this.sessions.set(session.dfmPath, session);
    }

    /** Get session by .dfm file path */
    getSessionByDfm(dfmPath: string): DfmSession | undefined {
        return this.sessions.get(dfmPath);
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
        for (const session of this.sessions.values()) {
            if (session.docxPath === docxPath) {
                return session;
            }
        }
        return undefined;
    }

    /** Remove a session */
    removeSession(dfmPath: string): boolean {
        return this.sessions.delete(dfmPath);
    }

    /** Mark session as dirty/clean */
    setDirty(dfmPath: string, dirty: boolean): void {
        const session = this.sessions.get(dfmPath);
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
        return this.sessions.has(filePath);
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
            // Just open the existing .dfm
            const doc = await vscode.workspace.openTextDocument(existing.dfmPath);
            await vscode.window.showTextDocument(doc, { preview: false });
            return;
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
        };

        this.sessionManager.addSession(session);

        // Open the .dfm file
        const doc = await vscode.workspace.openTextDocument(session.dfmPath);
        await vscode.window.showTextDocument(doc, { preview: false });

        // Set language to markdown for syntax highlighting
        await vscode.languages.setTextDocumentLanguage(doc, 'markdown');

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

        const result = await vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: `Saving back to ${path.basename(session.docxPath)}...`,
                cancellable: false,
            },
            async () => {
                return await this.callMcpSave(
                    session.docId,
                    outputPath ?? session.docxPath,
                );
            },
        );

        if (!result) {
            vscode.window.showErrorMessage('Failed to save DFM back to docx');
            return false;
        }

        this.sessionManager.setDirty(dfmPath, false);
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
                await this.saveDfmToDocx(dfmPath);
            } else if (choice === 'Cancel') {
                return;
            }
        }

        this.sessionManager.removeSession(dfmPath);
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
                            filters: { 'Word Documents': ['docx'] },
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
                    if (this.sessionManager.isDfmTracked(dfmPath)) {
                        await this.saveDfmToDocx(dfmPath);
                    }
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

            return JSON.parse(text) as IngestResult;
        } catch (error) {
            this.log(`MCP ingest_docx failed: ${error}`);
            return null;
        }
    }

    /**
     * Call MCP save_docx tool.
     */
    protected async callMcpSave(docId: string, outputPath: string): Promise<SaveResult | null> {
        try {
            const tools = await vscode.lm.tools;
            const saveTool = tools.find(t => t.name === 'save_docx');

            if (!saveTool) {
                this.log('ERROR: save_docx MCP tool not found');
                return null;
            }

            const result = await vscode.lm.invokeTool(saveTool.name, {
                input: { doc_id: docId, output_path: outputPath },
                toolInvocationToken: undefined,
            });

            const text = result.content
                .filter((p): p is vscode.LanguageModelTextPart => p instanceof vscode.LanguageModelTextPart)
                .map(p => p.value)
                .join('');

            return JSON.parse(text) as SaveResult;
        } catch (error) {
            this.log(`MCP save_docx failed: ${error}`);
            return null;
        }
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
