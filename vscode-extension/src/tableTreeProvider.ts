/**
 * Table Tree Provider
 * 
 * Provides a tree view showing A2T tables and drafts.
 */

import * as vscode from 'vscode';
import { EnvManager } from './envManager';

export class TableTreeProvider implements vscode.TreeDataProvider<TableItem> {
    private _onDidChangeTreeData = new vscode.EventEmitter<TableItem | undefined | void>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;
    
    private envManager: EnvManager;
    
    constructor(envManager: EnvManager) {
        this.envManager = envManager;
    }
    
    async refresh(): Promise<void> {
        this._onDidChangeTreeData.fire();
    }
    
    getTreeItem(element: TableItem): vscode.TreeItem {
        return element;
    }
    
    async getChildren(element?: TableItem): Promise<TableItem[]> {
        if (!element) {
            return [
                new TableItem('Tables', '', vscode.TreeItemCollapsibleState.Expanded, 'table', 'tables-root'),
                new TableItem('Drafts', '', vscode.TreeItemCollapsibleState.Expanded, 'edit', 'drafts-root')
            ];
        }
        
        if (element.contextValue === 'tables-root') {
            return this.getTables();
        }
        
        if (element.contextValue === 'drafts-root') {
            return this.getDrafts();
        }
        
        return [];
    }
    
    private getTables(): TableItem[] {
        const tables = this.envManager.listTables();
        
        if (tables.length === 0) {
            return [new TableItem('No tables generated', '', vscode.TreeItemCollapsibleState.None, 'info')];
        }
        
        return tables.map(t => {
            return new TableItem(
                t.title,
                t.id,
                vscode.TreeItemCollapsibleState.None,
                'table',
                'table-item',
                {
                    command: 'vscode.open',
                    title: 'Open Table',
                    arguments: [vscode.Uri.file(t.mdPath || t.path)]
                }
            );
        });
    }
    
    private getDrafts(): TableItem[] {
        const drafts = this.envManager.listDrafts();
        
        if (drafts.length === 0) {
            return [new TableItem('No drafts found', '', vscode.TreeItemCollapsibleState.None, 'info')];
        }
        
        return drafts.map(d => {
            return new TableItem(
                d.title,
                d.id,
                vscode.TreeItemCollapsibleState.None,
                'edit',
                'draft-item',
                {
                    command: 'vscode.open',
                    title: 'Open Draft',
                    arguments: [vscode.Uri.file(d.path)]
                }
            );
        });
    }
}

class TableItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly value: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        icon?: string,
        contextValue?: string,
        cmd?: vscode.Command
    ) {
        super(label, collapsibleState);
        
        if (value) {
            this.description = value;
        }
        
        if (icon) {
            this.iconPath = new vscode.ThemeIcon(icon);
        }
        
        if (contextValue) {
            this.contextValue = contextValue;
        }
        
        if (cmd) {
            this.command = cmd;
        }
    }
}
