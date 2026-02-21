/**
 * DFM Language Features
 *
 * Provides folding ranges for DFM comment blocks and
 * decorations that visually distinguish protected vs editable regions.
 */

import * as vscode from 'vscode';

/** Regex patterns for DFM block markers */
export const DFM_PATTERNS = {
    /** Opening compound tag: <!-- dfm:TYPE @b:ID ... --> */
    compoundOpen: /^<!--\s*dfm:(\w+)\s+@b:(\S+)/,
    /** Closing compound tag: <!-- /dfm:TYPE --> */
    compoundClose: /^<!--\s*\/dfm:(\w+)\s*-->/,
    /** Single-line block annotation: <!-- @b:ID ... --> */
    simpleBlock: /^<!--\s*@b:(\S+)/,
    /** Bookmark: <!-- dfm:bookmark @b:ID --> */
    bookmark: /^<!--\s*dfm:bookmark\s+@b:(\S+)\s*-->/,
    /** Break: <!-- dfm:break @b:ID type:... --> */
    breakMark: /^<!--\s*dfm:break\s+@b:(\S+)/,
    /** Styles block start: <!-- dfm:styles -->  */
    stylesOpen: /^<!--\s*dfm:styles\s*$/,
    /** Protected block types */
    protectedTypes: new Set([
        'chart', 'toc', 'header', 'footer', 'field', 'macro', 'break',
        'bookmark', 'styles',
    ]),
    /** Editable compound types */
    editableTypes: new Set([
        'table', 'format', 'image', 'footnote', 'caption',
    ]),
};

/**
 * Folding range provider for DFM files.
 * Folds compound blocks (<!-- dfm:X --> ... <!-- /dfm:X -->) and
 * the frontmatter/styles blocks.
 */
export class DfmFoldingProvider implements vscode.FoldingRangeProvider {
    provideFoldingRanges(
        document: vscode.TextDocument,
    ): vscode.FoldingRange[] {
        return computeFoldingRanges(document);
    }
}

/**
 * Pure function to compute folding ranges — testable without VS Code runtime.
 */
export function computeFoldingRanges(
    document: { lineCount: number; lineAt(i: number): { text: string } },
): vscode.FoldingRange[] {
    const ranges: vscode.FoldingRange[] = [];
    const stack: { type: string; line: number }[] = [];

    let inFrontmatter = false;
    let frontmatterStart = -1;

    for (let i = 0; i < document.lineCount; i++) {
        const text = document.lineAt(i).text.trim();

        // Frontmatter (---)
        if (text === '---') {
            if (!inFrontmatter) {
                inFrontmatter = true;
                frontmatterStart = i;
            } else {
                inFrontmatter = false;
                if (frontmatterStart >= 0) {
                    ranges.push(new vscode.FoldingRange(
                        frontmatterStart, i,
                        vscode.FoldingRangeKind.Region,
                    ));
                    frontmatterStart = -1;
                }
            }
            continue;
        }

        // Styles block
        if (DFM_PATTERNS.stylesOpen.test(text)) {
            stack.push({ type: 'styles', line: i });
            continue;
        }

        // Compound opening
        const openMatch = DFM_PATTERNS.compoundOpen.exec(text);
        if (openMatch) {
            stack.push({ type: openMatch[1], line: i });
            continue;
        }

        // Compound closing
        const closeMatch = DFM_PATTERNS.compoundClose.exec(text);
        if (closeMatch) {
            const closeType = closeMatch[1];
            // Find matching opening
            for (let j = stack.length - 1; j >= 0; j--) {
                if (stack[j].type === closeType) {
                    ranges.push(new vscode.FoldingRange(
                        stack[j].line, i,
                        vscode.FoldingRangeKind.Region,
                    ));
                    stack.splice(j, 1);
                    break;
                }
            }
        }

        // Comment ending with --> that closes styles
        if (text.endsWith('-->') && stack.length > 0) {
            const top = stack[stack.length - 1];
            if (top.type === 'styles' && i > top.line) {
                ranges.push(new vscode.FoldingRange(
                    top.line, i,
                    vscode.FoldingRangeKind.Region,
                ));
                stack.pop();
            }
        }
    }

    return ranges;
}

/** Decoration types for DFM rendering */
export interface DfmDecorationTypes {
    protectedBlock: vscode.TextEditorDecorationType;
    editableAnnotation: vscode.TextEditorDecorationType;
    blockId: vscode.TextEditorDecorationType;
}

/** Create decoration types */
export function createDecorationTypes(): DfmDecorationTypes {
    return {
        protectedBlock: vscode.window.createTextEditorDecorationType({
            backgroundColor: 'rgba(255, 165, 0, 0.05)',
            isWholeLine: true,
            overviewRulerColor: 'rgba(255, 165, 0, 0.5)',
            overviewRulerLane: vscode.OverviewRulerLane.Left,
        }),
        editableAnnotation: vscode.window.createTextEditorDecorationType({
            opacity: '0.4',
            isWholeLine: true,
        }),
        blockId: vscode.window.createTextEditorDecorationType({
            opacity: '0.3',
            fontStyle: 'italic',
        }),
    };
}

/**
 * Compute decoration ranges from document text.
 * Pure function — testable without VS Code runtime.
 */
export function computeDecorations(
    document: { lineCount: number; lineAt(i: number): { text: string } },
): {
    protectedRanges: { start: number; end: number }[];
    annotationLines: number[];
    blockIdLines: number[];
} {
    const protectedRanges: { start: number; end: number }[] = [];
    const annotationLines: number[] = [];
    const blockIdLines: number[] = [];

    let inProtected = false;
    let protectedStart = -1;

    for (let i = 0; i < document.lineCount; i++) {
        const text = document.lineAt(i).text.trim();

        // Block ID annotations (<!-- @b:xxx -->)
        if (DFM_PATTERNS.simpleBlock.test(text)) {
            annotationLines.push(i);
            blockIdLines.push(i);
            continue;
        }

        // Bookmark / break (single-line protected)
        if (DFM_PATTERNS.bookmark.test(text) || DFM_PATTERNS.breakMark.test(text)) {
            protectedRanges.push({ start: i, end: i });
            continue;
        }

        // Compound opening
        const openMatch = DFM_PATTERNS.compoundOpen.exec(text);
        if (openMatch) {
            const blockType = openMatch[1];

            // Mark opening line as annotation
            annotationLines.push(i);
            blockIdLines.push(i);

            if (DFM_PATTERNS.protectedTypes.has(blockType)) {
                inProtected = true;
                protectedStart = i;
            }
            continue;
        }

        // Compound closing
        const closeMatch = DFM_PATTERNS.compoundClose.exec(text);
        if (closeMatch) {
            annotationLines.push(i);

            if (inProtected && protectedStart >= 0) {
                protectedRanges.push({ start: protectedStart, end: i });
                inProtected = false;
                protectedStart = -1;
            }
        }
    }

    return { protectedRanges, annotationLines, blockIdLines };
}

/**
 * Apply decorations to an editor based on computed ranges.
 */
export function applyDecorations(
    editor: vscode.TextEditor,
    decorations: DfmDecorationTypes,
    computed: ReturnType<typeof computeDecorations>,
): void {
    const protectedRanges = computed.protectedRanges.map(r =>
        new vscode.Range(r.start, 0, r.end, editor.document.lineAt(r.end).text.length),
    );

    const annotationRanges = computed.annotationLines.map(line =>
        new vscode.Range(line, 0, line, editor.document.lineAt(line).text.length),
    );

    const blockIdRanges = computed.blockIdLines.map(line =>
        new vscode.Range(line, 0, line, editor.document.lineAt(line).text.length),
    );

    editor.setDecorations(decorations.protectedBlock, protectedRanges);
    editor.setDecorations(decorations.editableAnnotation, annotationRanges);
    editor.setDecorations(decorations.blockId, blockIdRanges);
}

/**
 * DFM Language Feature Manager
 * Registers folding provider and manages decorations lifecycle.
 */
export class DfmLanguageFeatures implements vscode.Disposable {
    private readonly disposables: vscode.Disposable[] = [];
    private decorationTypes: DfmDecorationTypes | null = null;

    register(): void {
        // Folding provider for .dfm and .md files
        this.disposables.push(
            vscode.languages.registerFoldingRangeProvider(
                [{ language: 'markdown' }, { pattern: '**/*.dfm' }],
                new DfmFoldingProvider(),
            ),
        );

        // Create decorations
        this.decorationTypes = createDecorationTypes();

        // Apply decorations on editor change
        this.disposables.push(
            vscode.window.onDidChangeActiveTextEditor(editor => {
                if (editor && this.isDfmFile(editor.document)) {
                    this.updateDecorations(editor);
                }
            }),
        );

        this.disposables.push(
            vscode.workspace.onDidChangeTextDocument(e => {
                const editor = vscode.window.activeTextEditor;
                if (editor && editor.document === e.document && this.isDfmFile(e.document)) {
                    this.updateDecorations(editor);
                }
            }),
        );

        // Apply to currently active editor
        const active = vscode.window.activeTextEditor;
        if (active && this.isDfmFile(active.document)) {
            this.updateDecorations(active);
        }
    }

    private isDfmFile(document: vscode.TextDocument): boolean {
        return (
            document.uri.fsPath.endsWith('.dfm') ||
            document.getText(new vscode.Range(0, 0, 0, 20)).includes('dfm_version')
        );
    }

    private updateDecorations(editor: vscode.TextEditor): void {
        if (!this.decorationTypes) {
            return;
        }
        const computed = computeDecorations(editor.document);
        applyDecorations(editor, this.decorationTypes, computed);
    }

    dispose(): void {
        if (this.decorationTypes) {
            this.decorationTypes.protectedBlock.dispose();
            this.decorationTypes.editableAnnotation.dispose();
            this.decorationTypes.blockId.dispose();
        }
        for (const d of this.disposables) {
            d.dispose();
        }
    }
}
