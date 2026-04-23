/**
 * Mock vscode module for unit tests.
 *
 * Provides minimal stubs for types/classes used by DFM modules
 * so they can be tested without the VS Code host.
 */

// FoldingRange mock
export class FoldingRange {
    constructor(
        public start: number,
        public end: number,
        public kind?: number,
    ) {}
}

export enum FoldingRangeKind {
    Comment = 1,
    Imports = 2,
    Region = 3,
}

// Range mock
export class Range {
    constructor(
        public startLine: number,
        public startCharacter: number,
        public endLine: number,
        public endCharacter: number,
    ) {}
}

// OverviewRulerLane mock
export enum OverviewRulerLane {
    Left = 1,
    Center = 2,
    Right = 4,
    Full = 7,
}

// Uri mock
export class Uri {
    constructor(public fsPath: string) {}

    static file(path: string): Uri {
        return new Uri(path);
    }

    static parse(value: string): Uri {
        return new Uri(value);
    }
}

// EventEmitter mock
export class EventEmitter<T> {
    readonly event = (_listener: (value: T) => void) => ({ dispose() { /* no-op */ } });

    fire(_value?: T): void {
        // no-op
    }

    dispose(): void {
        // no-op
    }
}

// TextEditorDecorationType mock
export class MockDecorationType {
    dispose(): void {
        // no-op
    }
}

// Window mock
export const window = {
    createTextEditorDecorationType(_options: any): MockDecorationType {
        return new MockDecorationType();
    },
    createOutputChannel(_name: string) {
        return {
            appendLine(_msg: string) { /* no-op */ },
            show() { /* no-op */ },
            dispose() { /* no-op */ },
        };
    },
    showInformationMessage: async (..._args: any[]) => undefined,
    showWarningMessage: async (..._args: any[]) => undefined,
    showErrorMessage: async (..._args: any[]) => undefined,
    showOpenDialog: async () => undefined,
    showSaveDialog: async () => undefined,
    showQuickPick: async () => undefined,
    withProgress: async (_options: any, task: any) => task({ report() { /* no-op */ } }),
    activeTextEditor: undefined as any,
    onDidChangeActiveTextEditor: () => ({ dispose() { /* no-op */ } }),
};

// Workspace mock
const configurationValues = new Map<string, unknown>();

export function __setConfigurationValue(key: string, value: unknown): void {
    configurationValues.set(key, value);
}

export function __resetConfiguration(): void {
    configurationValues.clear();
}

export const workspace = {
    onDidChangeTextDocument: () => ({ dispose() { /* no-op */ } }),
    onDidCloseTextDocument: () => ({ dispose() { /* no-op */ } }),
    openTextDocument: async (path: string) => ({ uri: Uri.file(path), getText: () => '' }),
    getConfiguration: () => ({
        get: (key: string, defaultValue?: any) => configurationValues.has(`assetAwareMcp.${key}`)
            ? configurationValues.get(`assetAwareMcp.${key}`)
            : defaultValue,
    }),
    workspaceFolders: undefined as any,
};

// Languages mock
export const languages = {
    registerFoldingRangeProvider: () => ({ dispose() { /* no-op */ } }),
    setTextDocumentLanguage: async () => undefined,
};

// Commands mock
export const commands = {
    registerCommand: (_id: string, _handler: any) => ({ dispose() { /* no-op */ } }),
    executeCommand: async () => undefined,
    getCommands: async () => [],
};

// ProgressLocation mock
export enum ProgressLocation {
    SourceControl = 1,
    Window = 10,
    Notification = 15,
}

// Extensions mock
export const extensions = {
    getExtension: () => undefined,
};

// Env mock
export const env = {
    openExternal: async () => true,
};

// LM mock
export const lm = {
    tools: [] as any[],
    invokeTool: async () => ({ content: [] }),
};

// LanguageModelTextPart mock
export class LanguageModelTextPart {
    constructor(public value: string) {}
}

// Version
export const version = '1.96.0';
