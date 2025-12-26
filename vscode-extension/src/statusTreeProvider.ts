/**
 * Status Tree Provider
 * 
 * Provides a tree view showing the current status of the extension.
 */

import * as vscode from 'vscode';
import { EnvManager } from './envManager';

export class StatusTreeProvider implements vscode.TreeDataProvider<StatusItem> {
    private _onDidChangeTreeData = new vscode.EventEmitter<StatusItem | undefined | void>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;
    
    private envManager: EnvManager;
    
    constructor(envManager: EnvManager) {
        this.envManager = envManager;
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
        const ollamaConnected = await this.checkOllama(env.OLLAMA_HOST || 'http://localhost:11434');
        items.push(new StatusItem(
            'Ollama',
            ollamaConnected ? 'Connected' : 'Disconnected',
            vscode.TreeItemCollapsibleState.None,
            ollamaConnected ? 'check' : 'error',
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
        
        // Documents count
        const documents = this.envManager.listDocuments();
        items.push(new StatusItem(
            'Ingested Documents',
            `${documents.length} documents`,
            vscode.TreeItemCollapsibleState.None,
            'file-directory'
        ));
        
        return items;
    }
    
    private async checkOllama(host: string): Promise<boolean> {
        try {
            const response = await fetch(`${host}/api/tags`);
            return response.ok;
        } catch {
            return false;
        }
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
