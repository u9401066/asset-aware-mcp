/**
 * Document Tree Provider
 *
 * Provides a tree view showing ingested documents.
 */

import * as fs from 'fs';
import * as vscode from 'vscode';
import { EnvManager } from './envManager';

type ManifestSummary = {
    title?: string;
    page_count?: number;
    pages?: number;
    assets?: {
        tables?: { id: string }[];
        figures?: { id: string }[];
        sections?: { id: string }[];
    };
    tables?: { id: string }[];
    figures?: { id: string }[];
    sections?: { id: string }[];
};

export class DocumentTreeProvider implements vscode.TreeDataProvider<DocumentItem> {
    private _onDidChangeTreeData = new vscode.EventEmitter<DocumentItem | undefined | void>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    private envManager: EnvManager;

    constructor(envManager: EnvManager) {
        this.envManager = envManager;
    }

    async refresh(): Promise<void> {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: DocumentItem): vscode.TreeItem {
        return element;
    }

    async getChildren(element?: DocumentItem): Promise<DocumentItem[]> {
        if (!element) {
            return this.getDocuments();
        }

        // Show document details when expanded
        if (element.docId) {
            return this.getDocumentDetails(element.docId);
        }

        return [];
    }

    private getDocuments(): DocumentItem[] {
        const documents = this.envManager.listDocuments();

        if (documents.length === 0) {
            return [new DocumentItem(
                'No documents ingested',
                '',
                vscode.TreeItemCollapsibleState.None,
                'info'
            )];
        }

        return documents.map(doc => {
            // Try to get title from manifest
            const manifest = this.envManager.readManifest(doc.id) as ManifestSummary | null;
            const title = manifest?.title || doc.id.replace('doc_', '').replace(/_[a-f0-9]+$/, '').replace(/_/g, ' ');

            return new DocumentItem(
                title,
                doc.id,
                vscode.TreeItemCollapsibleState.Collapsed,
                'file-pdf',
                doc.id
            );
        });
    }

    private getDocumentDetails(docId: string): DocumentItem[] {
        const manifest = this.envManager.readManifest(docId) as ManifestSummary | null;

        if (!manifest) {
            return [new DocumentItem('Manifest not found', '', vscode.TreeItemCollapsibleState.None, 'warning')];
        }

        const items: DocumentItem[] = [];

        // Pages
        const pageCount = manifest.page_count ?? manifest.pages;
        if (pageCount) {
            items.push(new DocumentItem(
                `Pages: ${pageCount}`,
                '',
                vscode.TreeItemCollapsibleState.None,
                'book'
            ));
        }

        // Tables count
        const tableCount = manifest.assets?.tables?.length || manifest.tables?.length || 0;
        items.push(new DocumentItem(
            `Tables: ${tableCount}`,
            '',
            vscode.TreeItemCollapsibleState.None,
            'list-unordered'
        ));

        // Figures count
        const figureCount = manifest.assets?.figures?.length || manifest.figures?.length || 0;
        items.push(new DocumentItem(
            `Figures: ${figureCount}`,
            '',
            vscode.TreeItemCollapsibleState.None,
            'file-media'
        ));

        // Sections count
        const sectionCount = manifest.assets?.sections?.length || manifest.sections?.length || 0;
        items.push(new DocumentItem(
            `Sections: ${sectionCount}`,
            '',
            vscode.TreeItemCollapsibleState.None,
            'list-ordered'
        ));

        const segmentationPath = `${this.envManager.getDataDir()}/${docId}/segmentation.json`;
        if (fs.existsSync(segmentationPath)) {
            items.push(new DocumentItem(
                'Open Segmentation',
                '',
                vscode.TreeItemCollapsibleState.None,
                'symbol-structure',
                undefined,
                {
                    command: 'vscode.open',
                    title: 'Open Segmentation',
                    arguments: [vscode.Uri.file(segmentationPath)]
                }
            ));
        }

        // Open manifest command
        const manifestPath = this.envManager.getManifestPath(docId);
        if (manifestPath) {
            items.push(new DocumentItem(
                'Open Manifest',
                '',
                vscode.TreeItemCollapsibleState.None,
                'json',
                undefined,
                {
                    command: 'vscode.open',
                    title: 'Open Manifest',
                    arguments: [vscode.Uri.file(manifestPath)]
                }
            ));
        }

        return items;
    }
}

class DocumentItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly value: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        icon?: string,
        public readonly docId?: string,
        cmd?: vscode.Command
    ) {
        super(label, collapsibleState);

        if (value) {
            this.description = value;
        }

        if (icon) {
            this.iconPath = new vscode.ThemeIcon(icon);
        }

        if (cmd) {
            this.command = cmd;
        }
    }
}
