/**
 * Status Tree Provider
 *
 * Provides a tree view showing the current status of the extension.
 */

import * as vscode from 'vscode';
import { EnvManager } from './envManager';
import { checkOllamaModels } from './ollama';

export interface InstallInfo {
    scope: string;
    path: string;
}

export class StatusTreeProvider implements vscode.TreeDataProvider<StatusItem> {
    private _onDidChangeTreeData = new vscode.EventEmitter<StatusItem | undefined | void>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    private envManager: EnvManager;
    private installInfo: InstallInfo;
    private storageRoot: string;

    constructor(envManager: EnvManager, installInfo: InstallInfo, storageRoot: string) {
        this.envManager = envManager;
        this.installInfo = installInfo;
        this.storageRoot = storageRoot;
    }

    async refresh(): Promise<void> {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: StatusItem): vscode.TreeItem {
        return element;
    }

    async getChildren(element?: StatusItem): Promise<StatusItem[]> {
        if (!element) {
            return this.getRootItems();
        }
        return [];
    }

    private async getRootItems(): Promise<StatusItem[]> {
        const items: StatusItem[] = [];
        const env = await this.envManager.readEnv();

        // Extension install scope and storage root
        items.push(new StatusItem(
            'Install Scope',
            this.installInfo.scope,
            vscode.TreeItemCollapsibleState.None,
            'globe'
        ));

        items.push(new StatusItem(
            'Storage Root',
            this.storageRoot,
            vscode.TreeItemCollapsibleState.None,
            'file-directory'
        ));

        // Configuration file status
        const envExists = this.envManager.exists();
        items.push(new StatusItem(
            '.env Configuration',
            envExists ? 'Configured' : 'Missing',
            vscode.TreeItemCollapsibleState.None,
            envExists ? 'check' : 'warning',
            'assetAwareMcp.editEnv'
        ));

        // LLM Backend
        const backend = env.LLM_BACKEND || 'ollama';
        items.push(new StatusItem(
            'LLM Backend',
            backend.toUpperCase(),
            vscode.TreeItemCollapsibleState.None,
            backend === 'ollama' ? 'hubot' : 'cloud'
        ));

        // Ollama Connection
        const ollamaStatus = await checkOllamaModels(
            env.OLLAMA_HOST || 'http://localhost:11434',
            [
                env.OLLAMA_MODEL || 'qwen2.5:7b',
                env.OLLAMA_EMBEDDING_MODEL || 'nomic-embed-text',
            ],
        );
        items.push(new StatusItem(
            'Ollama',
            ollamaStatus.connected ? 'Connected' : 'Disconnected',
            vscode.TreeItemCollapsibleState.None,
            ollamaStatus.connected ? 'check' : 'error',
            'assetAwareMcp.checkConnection'
        ));

        items.push(new StatusItem(
            'Ollama Models',
            ollamaStatus.connected && ollamaStatus.missingModels.length === 0
                ? 'Available'
                : ollamaStatus.connected
                    ? `Missing: ${ollamaStatus.missingModels.join(', ')}`
                    : 'Not checked',
            vscode.TreeItemCollapsibleState.None,
            ollamaStatus.connected && ollamaStatus.missingModels.length === 0 ? 'check' : 'warning',
            'assetAwareMcp.checkConnection'
        ));

        // OpenAI API Key
        const openaiConfigured = !!(env.OPENAI_API_KEY);
        items.push(new StatusItem(
            'OpenAI API',
            openaiConfigured ? 'Configured' : 'Not Set',
            vscode.TreeItemCollapsibleState.None,
            openaiConfigured ? 'check' : 'dash'
        ));

        // Data Directory
        const dataDir = this.envManager.getDataDir();
        items.push(new StatusItem(
            'Data Directory (workspace)',
            dataDir,
            vscode.TreeItemCollapsibleState.None,
            'folder'
        ));

        // Documents count
        const documents = this.envManager.listDocuments();
        items.push(new StatusItem(
            'Ingested Documents',
            `${documents.length} documents`,
            vscode.TreeItemCollapsibleState.None,
            'file-directory'
        ));

        const jobs = this.envManager.listJobs();
        const activeJobs = jobs.filter(job => job.status === 'running' || job.status === 'pending');
        const jobLabel = activeJobs.length > 0
            ? `${activeJobs.length} active / ${jobs.length} total`
            : `${jobs.length} total`;
        items.push(new StatusItem(
            'ETL Jobs',
            jobLabel,
            vscode.TreeItemCollapsibleState.None,
            activeJobs.length > 0 ? 'sync~spin' : 'history'
        ));

        return items;
    }

}

class StatusItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly value: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        icon?: string,
        command?: string
    ) {
        super(label, collapsibleState);
        this.description = value;

        if (icon) {
            this.iconPath = new vscode.ThemeIcon(icon);
        }

        if (command) {
            this.command = {
                command: command,
                title: label
            };
        }
    }
}
