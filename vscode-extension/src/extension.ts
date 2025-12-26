/**
 * Asset-Aware MCP VS Code Extension
 * 
 * Provides Medical RAG capabilities with precise document asset retrieval.
 * Integrates with Ollama (local) or OpenAI for LLM backend.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { AssetAwareMcpProvider } from './mcpProvider';
import { StatusBarManager } from './statusBar';
import { SettingsPanel } from './settingsPanel';
import { EnvManager } from './envManager';
import { StatusTreeProvider } from './statusTreeProvider';
import { DocumentTreeProvider } from './documentTreeProvider';

let mcpProvider: AssetAwareMcpProvider;
let statusBar: StatusBarManager;
let envManager: EnvManager;
let statusTreeProvider: StatusTreeProvider;
let documentTreeProvider: DocumentTreeProvider;
let extensionContext: vscode.ExtensionContext;

// Context keys
const CONTEXT_READY = 'assetAwareMcp.ready';
const CONTEXT_OLLAMA_CONNECTED = 'assetAwareMcp.ollamaConnected';
const FIRST_ACTIVATION_KEY = 'assetAwareMcp.firstActivation';

/**
 * Extension activation
 */
export async function activate(context: vscode.ExtensionContext): Promise<void> {
    console.log('Asset-Aware MCP extension is activating...');
    
    extensionContext = context;
    
    try {
        // Step 1: Initialize status bar
        statusBar = new StatusBarManager();
        context.subscriptions.push(statusBar);
        statusBar.setStatus('initializing', 'Asset-Aware MCP: Initializing...');
        
        // Step 2: Initialize env manager
        envManager = new EnvManager(getWorkspaceRoot());
        
        // Step 3: Initialize tree providers
        statusTreeProvider = new StatusTreeProvider(envManager);
        documentTreeProvider = new DocumentTreeProvider(envManager);
        
        vscode.window.registerTreeDataProvider('assetAwareMcp.status', statusTreeProvider);
        vscode.window.registerTreeDataProvider('assetAwareMcp.documents', documentTreeProvider);
        
        // Step 4: Register MCP server provider
        mcpProvider = new AssetAwareMcpProvider(getWorkspaceRoot());
        const providerDisposable = vscode.lm.registerMcpServerDefinitionProvider(
            'asset-aware-mcp.servers',
            mcpProvider
        );
        context.subscriptions.push(providerDisposable);
        
        // Step 5: Register commands
        registerCommands(context);
        
        // Step 6: Check Ollama connection
        await checkAndUpdateOllamaStatus();
        
        // Step 7: Update status
        statusBar.setStatus('ready', 'Asset-Aware MCP: Ready');
        await vscode.commands.executeCommand('setContext', CONTEXT_READY, true);
        
        // Show walkthrough on first activation
        showFirstTimeWalkthrough(context);
        
        console.log('Asset-Aware MCP extension activated successfully');
        
    } catch (error) {
        console.error('Asset-Aware MCP activation error:', error);
        statusBar.setStatus('error', 'Asset-Aware MCP: Activation failed');
        vscode.window.showErrorMessage(`Asset-Aware MCP activation failed: ${error}`);
    }
}

/**
 * Get workspace root path
 */
function getWorkspaceRoot(): string {
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (workspaceFolder) {
        return workspaceFolder.uri.fsPath;
    }
    // Fall back to extension path if no workspace
    return extensionContext.extensionPath;
}

/**
 * Register extension commands
 */
function registerCommands(context: vscode.ExtensionContext): void {
    // Setup Wizard
    context.subscriptions.push(
        vscode.commands.registerCommand('assetAwareMcp.setupWizard', async () => {
            await runSetupWizard();
        })
    );
    
    // Open Settings Panel
    context.subscriptions.push(
        vscode.commands.registerCommand('assetAwareMcp.openSettings', async () => {
            SettingsPanel.createOrShow(context.extensionUri, envManager);
        })
    );
    
    // Edit .env file
    context.subscriptions.push(
        vscode.commands.registerCommand('assetAwareMcp.editEnv', async () => {
            const envPath = envManager.getEnvPath();
            
            // Ensure .env exists
            if (!fs.existsSync(envPath)) {
                await envManager.createDefaultEnv();
            }
            
            const doc = await vscode.workspace.openTextDocument(envPath);
            await vscode.window.showTextDocument(doc);
        })
    );
    
    // Show Status
    context.subscriptions.push(
        vscode.commands.registerCommand('assetAwareMcp.showStatus', async () => {
            const status = await getExtensionStatus();
            const panel = vscode.window.createWebviewPanel(
                'assetAwareMcpStatus',
                'Asset-Aware MCP Status',
                vscode.ViewColumn.One,
                { enableScripts: true }
            );
            panel.webview.html = getStatusWebviewContent(status);
        })
    );
    
    // Check Ollama Connection
    context.subscriptions.push(
        vscode.commands.registerCommand('assetAwareMcp.checkConnection', async () => {
            statusBar.setStatus('initializing', 'Checking Ollama...');
            const connected = await checkAndUpdateOllamaStatus();
            
            if (connected) {
                vscode.window.showInformationMessage('✅ Ollama is running and accessible!');
                statusBar.setStatus('ready', 'Asset-Aware MCP: Ready');
            } else {
                vscode.window.showWarningMessage(
                    '❌ Cannot connect to Ollama. Make sure Ollama is running.',
                    'Download Ollama'
                ).then(choice => {
                    if (choice === 'Download Ollama') {
                        vscode.env.openExternal(vscode.Uri.parse('https://ollama.com/download'));
                    }
                });
                statusBar.setStatus('warning', 'Asset-Aware MCP: Ollama offline');
            }
        })
    );
    
    // Refresh Status
    context.subscriptions.push(
        vscode.commands.registerCommand('assetAwareMcp.refreshStatus', async () => {
            await statusTreeProvider.refresh();
            await documentTreeProvider.refresh();
            await checkAndUpdateOllamaStatus();
            vscode.window.showInformationMessage('Status refreshed!');
        })
    );
}

/**
 * Run setup wizard
 */
async function runSetupWizard(): Promise<void> {
    const result = await vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: 'Asset-Aware MCP Setup',
            cancellable: false
        },
        async (progress) => {
            // Step 1: Check .env file
            progress.report({ message: 'Checking configuration...', increment: 0 });
            
            if (!fs.existsSync(envManager.getEnvPath())) {
                await envManager.createDefaultEnv();
                progress.report({ message: '.env created ✓', increment: 25 });
            } else {
                progress.report({ message: '.env exists ✓', increment: 25 });
            }
            
            // Step 2: Check Ollama
            progress.report({ message: 'Checking Ollama connection...', increment: 25 });
            const ollamaOk = await checkAndUpdateOllamaStatus();
            
            if (!ollamaOk) {
                const choice = await vscode.window.showWarningMessage(
                    'Ollama is not running. Would you like to use OpenAI instead?',
                    'Download Ollama', 'Use OpenAI', 'Continue Anyway'
                );
                
                if (choice === 'Download Ollama') {
                    vscode.env.openExternal(vscode.Uri.parse('https://ollama.com/download'));
                } else if (choice === 'Use OpenAI') {
                    await envManager.updateEnv('LLM_BACKEND', 'openai');
                    SettingsPanel.createOrShow(extensionContext.extensionUri, envManager);
                }
            }
            
            progress.report({ message: 'Connection check ✓', increment: 25 });
            
            // Step 3: Refresh MCP provider
            progress.report({ message: 'Refreshing MCP server...', increment: 25 });
            mcpProvider.refresh();
            
            return true;
        }
    );
    
    if (result) {
        statusBar.setStatus('ready', 'Asset-Aware MCP: Ready');
        vscode.window.showInformationMessage(
            '🎉 Asset-Aware MCP is ready! Try ingesting a PDF document.',
            'Open Copilot Chat'
        ).then(choice => {
            if (choice === 'Open Copilot Chat') {
                vscode.commands.executeCommand('workbench.action.chat.open');
            }
        });
    }
}

/**
 * Check Ollama connection
 */
async function checkOllamaConnection(): Promise<boolean> {
    const config = vscode.workspace.getConfiguration('assetAwareMcp');
    const host = config.get<string>('ollamaHost', 'http://localhost:11434');
    
    try {
        const response = await fetch(`${host}/api/tags`);
        return response.ok;
    } catch {
        return false;
    }
}

/**
 * Check Ollama and update context
 */
async function checkAndUpdateOllamaStatus(): Promise<boolean> {
    const connected = await checkOllamaConnection();
    await vscode.commands.executeCommand('setContext', CONTEXT_OLLAMA_CONNECTED, connected);
    await statusTreeProvider.refresh();
    return connected;
}

/**
 * Show walkthrough on first activation
 */
function showFirstTimeWalkthrough(context: vscode.ExtensionContext): void {
    const isFirstActivation = context.globalState.get<boolean>(FIRST_ACTIVATION_KEY, true);
    
    if (isFirstActivation) {
        context.globalState.update(FIRST_ACTIVATION_KEY, false);
        vscode.commands.executeCommand(
            'workbench.action.openWalkthrough',
            'asset-aware.asset-aware-mcp#assetAwareMcp.welcome',
            false
        );
    }
}

/**
 * Extension status interface
 */
interface ExtensionStatus {
    envExists: boolean;
    envPath: string;
    llmBackend: string;
    ollamaHost: string;
    ollamaModel: string;
    ollamaConnected: boolean;
    openaiConfigured: boolean;
    dataDir: string;
    documentCount: number;
}

/**
 * Get extension status
 */
async function getExtensionStatus(): Promise<ExtensionStatus> {
    const config = vscode.workspace.getConfiguration('assetAwareMcp');
    const env = await envManager.readEnv();
    const dataDir = path.resolve(getWorkspaceRoot(), env.DATA_DIR || './data');
    
    // Count documents
    let documentCount = 0;
    if (fs.existsSync(dataDir)) {
        const files = fs.readdirSync(dataDir);
        documentCount = files.filter(f => fs.statSync(path.join(dataDir, f)).isDirectory()).length;
    }
    
    return {
        envExists: fs.existsSync(envManager.getEnvPath()),
        envPath: envManager.getEnvPath(),
        llmBackend: env.LLM_BACKEND || 'ollama',
        ollamaHost: env.OLLAMA_HOST || config.get<string>('ollamaHost', 'http://localhost:11434'),
        ollamaModel: env.OLLAMA_MODEL || config.get<string>('ollamaModel', 'qwen2.5:7b'),
        ollamaConnected: await checkOllamaConnection(),
        openaiConfigured: !!(env.OPENAI_API_KEY),
        dataDir: dataDir,
        documentCount: documentCount
    };
}

/**
 * Generate status webview HTML
 */
function getStatusWebviewContent(status: ExtensionStatus): string {
    const checkmark = '✅';
    const cross = '❌';
    const warning = '⚠️';
    
    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Asset-Aware MCP Status</title>
    <style>
        body {
            font-family: var(--vscode-font-family);
            padding: 20px;
            color: var(--vscode-foreground);
            background: var(--vscode-editor-background);
        }
        h1 { 
            color: var(--vscode-titleBar-activeForeground);
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .section {
            background: var(--vscode-editor-inactiveSelectionBackground);
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
        }
        .section h2 {
            margin-top: 0;
            font-size: 14px;
            color: var(--vscode-descriptionForeground);
        }
        .item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid var(--vscode-panel-border);
        }
        .item:last-child { border-bottom: none; }
        .status { font-weight: bold; }
        .ok { color: #4caf50; }
        .error { color: #f44336; }
        .warning { color: #ff9800; }
        .info { color: #2196f3; }
        code {
            background: var(--vscode-textCodeBlock-background);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 12px;
        }
        .actions {
            margin-top: 20px;
        }
        .btn {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            margin-right: 10px;
        }
        .btn:hover {
            background: var(--vscode-button-hoverBackground);
        }
    </style>
</head>
<body>
    <h1>📚 Asset-Aware MCP Status</h1>
    
    <div class="section">
        <h2>Configuration</h2>
        <div class="item">
            <span>.env File:</span>
            <span class="status ${status.envExists ? 'ok' : 'error'}">
                ${status.envExists ? checkmark + ' Exists' : cross + ' Missing'}
            </span>
        </div>
        <div class="item">
            <span>Path:</span>
            <code>${status.envPath}</code>
        </div>
        <div class="item">
            <span>LLM Backend:</span>
            <span class="info">${status.llmBackend.toUpperCase()}</span>
        </div>
    </div>
    
    <div class="section">
        <h2>Ollama Connection</h2>
        <div class="item">
            <span>Host:</span>
            <code>${status.ollamaHost}</code>
        </div>
        <div class="item">
            <span>Model:</span>
            <span>${status.ollamaModel}</span>
        </div>
        <div class="item">
            <span>Status:</span>
            <span class="status ${status.ollamaConnected ? 'ok' : 'error'}">
                ${status.ollamaConnected ? checkmark + ' Connected' : cross + ' Disconnected'}
            </span>
        </div>
    </div>
    
    <div class="section">
        <h2>OpenAI</h2>
        <div class="item">
            <span>API Key:</span>
            <span class="status ${status.openaiConfigured ? 'ok' : 'warning'}">
                ${status.openaiConfigured ? checkmark + ' Configured' : warning + ' Not configured'}
            </span>
        </div>
    </div>
    
    <div class="section">
        <h2>Documents</h2>
        <div class="item">
            <span>Data Directory:</span>
            <code>${status.dataDir}</code>
        </div>
        <div class="item">
            <span>Ingested Documents:</span>
            <span class="info">${status.documentCount}</span>
        </div>
    </div>
</body>
</html>`;
}

/**
 * Extension deactivation
 */
export function deactivate(): void {
    console.log('Asset-Aware MCP extension is deactivating...');
    statusBar?.dispose();
}
