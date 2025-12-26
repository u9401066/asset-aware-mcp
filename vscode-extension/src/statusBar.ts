/**
 * Status Bar Manager
 * 
 * Shows extension status in VS Code status bar.
 */

import * as vscode from 'vscode';

export type StatusType = 'initializing' | 'ready' | 'warning' | 'error';

export class StatusBarManager implements vscode.Disposable {
    private statusBarItem: vscode.StatusBarItem;
    
    constructor() {
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            100
        );
        this.statusBarItem.command = 'assetAwareMcp.showStatus';
        this.statusBarItem.show();
    }
    
    /**
     * Update status bar display
     */
    setStatus(type: StatusType, text: string): void {
        this.statusBarItem.text = this.getIcon(type) + ' ' + text;
        this.statusBarItem.tooltip = this.getTooltip(type);
        this.statusBarItem.backgroundColor = this.getBackgroundColor(type);
    }
    
    private getIcon(type: StatusType): string {
        switch (type) {
            case 'initializing':
                return '$(sync~spin)';
            case 'ready':
                return '$(book)';
            case 'warning':
                return '$(warning)';
            case 'error':
                return '$(error)';
        }
    }
    
    private getTooltip(type: StatusType): string {
        switch (type) {
            case 'initializing':
                return 'Asset-Aware MCP is initializing...';
            case 'ready':
                return 'Asset-Aware MCP is ready. Click for status.';
            case 'warning':
                return 'Asset-Aware MCP has warnings. Click for details.';
            case 'error':
                return 'Asset-Aware MCP error. Click for details.';
        }
    }
    
    private getBackgroundColor(type: StatusType): vscode.ThemeColor | undefined {
        switch (type) {
            case 'error':
                return new vscode.ThemeColor('statusBarItem.errorBackground');
            case 'warning':
                return new vscode.ThemeColor('statusBarItem.warningBackground');
            default:
                return undefined;
        }
    }
    
    /**
     * Dispose resources
     */
    dispose(): void {
        this.statusBarItem.dispose();
    }
}
