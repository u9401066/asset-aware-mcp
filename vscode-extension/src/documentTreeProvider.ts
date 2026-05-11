/**
 * Document Tree Provider
 *
 * Provides a tree view showing ingested documents.
 */

import * as fs from 'fs';
import * as vscode from 'vscode';
import { DocumentArtifact, EnvManager } from './envManager';

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

        if (element.kind === 'document' && element.docId) {
            return this.getDocumentDetails(element.docId);
        }
        if (element.kind === 'artifacts' && element.docId) {
            return this.getArtifactItems(element.docId);
        }
        if (element.kind === 'citations' && element.docId) {
            return this.getCitationItems(element.docId);
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
                doc.id,
                undefined,
                'document'
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

        const artifacts = this.envManager.listDocumentArtifacts(docId);
        if (artifacts.length > 0) {
            items.push(new DocumentItem(
                `Artifacts: ${artifacts.length}`,
                '',
                vscode.TreeItemCollapsibleState.Collapsed,
                'archive',
                docId,
                undefined,
                'artifacts'
            ));
        }

        const citationSpans = this.envManager.listCitationSpans(docId, 1);
        const hasCitationArtifacts = artifacts.some(artifact => artifact.id.startsWith('citation-'));
        if (hasCitationArtifacts || citationSpans.length > 0) {
            items.push(new DocumentItem(
                'Citations',
                '',
                vscode.TreeItemCollapsibleState.Collapsed,
                'references',
                docId,
                undefined,
                'citations'
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

    private getArtifactItems(docId: string): DocumentItem[] {
        const artifacts = this.envManager.listDocumentArtifacts(docId);
        if (artifacts.length === 0) {
            return [new DocumentItem('No artifacts found', '', vscode.TreeItemCollapsibleState.None, 'info')];
        }

        return artifacts.map((artifact: DocumentArtifact) => new DocumentItem(
            artifact.label,
            artifact.kind,
            vscode.TreeItemCollapsibleState.None,
            artifact.icon,
            undefined,
            {
                command: 'vscode.open',
                title: `Open ${artifact.label}`,
                arguments: [vscode.Uri.file(artifact.path)]
            },
            'artifact'
        ));
    }

    private getCitationItems(docId: string): DocumentItem[] {
        const artifacts = this.envManager
            .listDocumentArtifacts(docId)
            .filter(artifact => artifact.id.startsWith('citation-'));
        const spans = this.envManager.listCitationSpans(docId);
        const items: DocumentItem[] = [];

        for (const artifact of artifacts) {
            items.push(new DocumentItem(
                `Open ${artifact.label}`,
                artifact.kind,
                vscode.TreeItemCollapsibleState.None,
                artifact.icon,
                undefined,
                {
                    command: 'vscode.open',
                    title: `Open ${artifact.label}`,
                    arguments: [vscode.Uri.file(artifact.path)]
                },
                'citation-artifact'
            ));
        }

        for (const span of spans) {
            const item = new DocumentItem(
                span.label,
                span.description,
                vscode.TreeItemCollapsibleState.None,
                'quote',
                undefined,
                {
                    command: 'vscode.open',
                    title: 'Open Citation Span',
                    arguments: [
                        vscode.Uri.file(span.path),
                        { selection: new vscode.Range(span.line, 0, span.line, 0) }
                    ]
                },
                'citation-span'
            );
            item.tooltip = span.quote || span.label;
            items.push(item);
        }

        if (items.length === 0) {
            return [new DocumentItem('No citation index found', '', vscode.TreeItemCollapsibleState.None, 'info')];
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
        cmd?: vscode.Command,
        public readonly kind?: string
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
