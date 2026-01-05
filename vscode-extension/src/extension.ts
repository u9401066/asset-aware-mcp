/**
 * Asset-Aware MCP VS Code Extension
 * 
 * Provides Medical RAG capabilities with precise document asset retrieval.
 * Integrates with Ollama (local) or OpenAI for LLM backend.
 * 
 * Auto-installs uv if not present, then uses uvx to run from PyPI.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { exec } from 'child_process';
import { promisify } from 'util';
import { AssetAwareMcpProvider } from './mcpProvider';
import { StatusBarManager } from './statusBar';
import { SettingsPanel } from './settingsPanel';
import { EnvManager } from './envManager';
import { StatusTreeProvider } from './statusTreeProvider';
import { DocumentTreeProvider } from './documentTreeProvider';
import { TableTreeProvider } from './tableTreeProvider';

const execAsync = promisify(exec);

// Module-level variables
let mcpProvider: AssetAwareMcpProvider;
let statusBar: StatusBarManager;
let envManager: EnvManager;
let statusTreeProvider: StatusTreeProvider;
let documentTreeProvider: DocumentTreeProvider;
let tableTreeProvider: TableTreeProvider;
let extensionContext: vscode.ExtensionContext;
let outputChannel: vscode.OutputChannel;

// Context keys
const CONTEXT_READY = 'assetAwareMcp.ready';
const CONTEXT_OLLAMA_CONNECTED = 'assetAwareMcp.ollamaConnected';
const FIRST_ACTIVATION_KEY = 'assetAwareMcp.firstActivation';

/**
 * Log message to output channel
 */
function log(message: string): void {
    const timestamp = new Date().toISOString();
    outputChannel?.appendLine(`[${timestamp}] ${message}`);
    console.log(`[Asset-Aware MCP] ${message}`);
}

/**
 * Get potential uv binary paths based on platform
 */
function getUvPaths(): string[] {
    const homeDir = process.env.HOME || process.env.USERPROFILE || '';
    const platform = process.platform;
    
    if (platform === 'win32') {
        return [
            'uv',  // In PATH
            path.join(homeDir, 'AppData', 'Local', 'uv', 'bin', 'uv.exe'),
            path.join(homeDir, '.local', 'bin', 'uv.exe'),
            path.join(homeDir, '.cargo', 'bin', 'uv.exe'),
            'C:\\Program Files\\uv\\uv.exe',
        ];
    } else {
        return [
            'uv',  // In PATH
            path.join(homeDir, '.local', 'bin', 'uv'),
            path.join(homeDir, '.cargo', 'bin', 'uv'),
            '/usr/local/bin/uv',
            '/opt/homebrew/bin/uv',
        ];
    }
}

/**
 * Find the actual uv binary path
 */
async function findUvPath(): Promise<string | null> {
    const paths = getUvPaths();
    
    for (const uvPath of paths) {
        try {
            if (uvPath === 'uv') {
                // Check if in PATH
                await execAsync('uv --version');
                log('Found uv in PATH');
                return 'uv';
            } else if (fs.existsSync(uvPath)) {
                // Verify it works
                await execAsync(`"${uvPath}" --version`);
                log('Found uv at: ' + uvPath);
                return uvPath;
            }
        } catch {
            // Continue to next path
        }
    }
    
    return null;
}

/**
 * Check if uv is installed and return its path
 */
async function isUvInstalled(): Promise<string | null> {
    return await findUvPath();
}

/**
 * Install uv automatically based on platform
 */
async function installUv(): Promise<string | null> {
    const platform = process.platform;
    log(`Installing uv on ${platform}...`);
    
    return vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: 'Installing uv (Python package manager)',
            cancellable: false
        },
        async (progress) => {
            try {
                progress.report({ message: 'Downloading uv...' });
                
                if (platform === 'win32') {
                    // Windows: Use PowerShell
                    log('Using PowerShell installer for Windows');
                    await execAsync(
                        'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"',
                        { timeout: 120000 }
                    );
                } else {
                    // Linux/macOS: Use curl
                    log('Using curl installer for Unix');
                    await execAsync(
                        'curl -LsSf https://astral.sh/uv/install.sh | sh',
                        { timeout: 120000 }
                    );
                }
                
                progress.report({ message: 'Verifying installation...' });
                
                // Wait a moment for filesystem to sync
                await new Promise(resolve => setTimeout(resolve, 1000));
                
                // Find the installed uv path
                const uvPath = await findUvPath();
                
                if (uvPath) {
                    log('uv installed successfully at: ' + uvPath);
                    
                    // Ask user to reload VS Code for PATH to take effect
                    const choice = await vscode.window.showInformationMessage(
                        '✅ uv installed! Please reload VS Code to complete setup.',
                        'Reload Now',
                        'Later'
                    );
                    
                    if (choice === 'Reload Now') {
                        vscode.commands.executeCommand('workbench.action.reloadWindow');
                    }
                    
                    return uvPath;
                } else {
                    throw new Error('uv installation completed but binary not found. Please reload VS Code.');
                }
            } catch (error) {
                const errorMsg = error instanceof Error ? error.message : String(error);
                log('uv installation failed: ' + errorMsg);
                
                vscode.window.showErrorMessage(
                    `Failed to install uv: ${errorMsg}`,
                    'Install Manually'
                ).then(choice => {
                    if (choice === 'Install Manually') {
                        vscode.env.openExternal(vscode.Uri.parse('https://docs.astral.sh/uv/getting-started/installation/'));
                    }
                });
                
                return null;
            }
        }
    );
}

/**
 * Ensure uv is installed, install if not. Returns the uv path or null.
 */
async function ensureUvInstalled(): Promise<string | null> {
    log('Checking if uv is installed...');
    
    const existingPath = await isUvInstalled();
    if (existingPath) {
        try {
            const cmd = existingPath === 'uv' ? 'uv --version' : `"${existingPath}" --version`;
            const { stdout } = await execAsync(cmd);
            log('uv is already installed: ' + stdout.trim());
            
            // Store the path for mcpProvider to use
            extensionContext.globalState.update('uvPath', existingPath);
            return existingPath;
        } catch {
            return existingPath;
        }
    }
    
    log('uv not found, prompting for installation...');
    
    const choice = await vscode.window.showInformationMessage(
        'Asset-Aware MCP requires "uv" (Python package manager). Install now?',
        'Install uv',
        'Install Manually',
        'Cancel'
    );
    
    if (choice === 'Install uv') {
        const installedPath = await installUv();
        if (installedPath) {
            extensionContext.globalState.update('uvPath', installedPath);
        }
        return installedPath;
    } else if (choice === 'Install Manually') {
        vscode.env.openExternal(vscode.Uri.parse('https://docs.astral.sh/uv/getting-started/installation/'));
        return null;
    }
    
    return null;
}

/**
 * Extension activation
 */
export async function activate(context: vscode.ExtensionContext): Promise<void> {
    // Create output channel first for logging
    outputChannel = vscode.window.createOutputChannel('Asset-Aware MCP');
    context.subscriptions.push(outputChannel);
    
    log('Extension is activating...');
    
    extensionContext = context;
    
    try {
        // Step 1: Initialize status bar
        log('Step 1: Initializing status bar...');
        statusBar = new StatusBarManager();
        context.subscriptions.push(statusBar);
        statusBar.setStatus('initializing', 'Asset-Aware MCP: Initializing...');
        
        // Step 2: Ensure uv is installed (required for running MCP server)
        log('Step 2: Checking uv installation...');
        statusBar.setStatus('initializing', 'Asset-Aware MCP: Checking uv...');
        const uvPath = await ensureUvInstalled();
        if (!uvPath) {
            log('uv not available - MCP server will not function');
            statusBar.setStatus('warning', 'Asset-Aware MCP: uv not installed');
            vscode.window.showWarningMessage(
                'Asset-Aware MCP requires uv to run. Please install uv and reload.',
                'Install uv'
            ).then(choice => {
                if (choice === 'Install uv') {
                    installUv();
                }
            });
        } else {
            log('uv path: ' + uvPath);
        }
        
        // Step 3: Initialize env manager
        log('Step 3: Initializing env manager...');
        envManager = new EnvManager(getWorkspaceRoot());
        
        // Step 4: Initialize tree providers
        log('Step 4: Initializing tree providers...');
        statusTreeProvider = new StatusTreeProvider(envManager);
        documentTreeProvider = new DocumentTreeProvider(envManager);
        tableTreeProvider = new TableTreeProvider(envManager);
        
        vscode.window.registerTreeDataProvider('assetAwareMcp.status', statusTreeProvider);
        vscode.window.registerTreeDataProvider('assetAwareMcp.documents', documentTreeProvider);
        vscode.window.registerTreeDataProvider('assetAwareMcp.tables', tableTreeProvider);
        
        // Step 5: Register MCP server provider (with error handling)
        log('Step 5: Registering MCP server provider...');
        mcpProvider = new AssetAwareMcpProvider(getWorkspaceRoot(), outputChannel, context);
        
        // Check if MCP API is available (it's a proposed API)
        if (typeof vscode.lm?.registerMcpServerDefinitionProvider === 'function') {
            const providerDisposable = vscode.lm.registerMcpServerDefinitionProvider(
                'asset-aware-mcp.servers',
                mcpProvider
            );
            context.subscriptions.push(providerDisposable);
            log('MCP server provider registered successfully');
        } else {
            log('WARNING: vscode.lm.registerMcpServerDefinitionProvider is not available.');
            log('This might be because:');
            log('  1. VS Code version is too old (need 1.96+)');
            log('  2. The MCP proposed API is not enabled');
            log('  3. GitHub Copilot extension is not installed');
        }
        
        // Step 6: Register commands
        log('Step 6: Registering commands...');
        registerCommands(context);
        
        // Step 7: Check Ollama connection (non-blocking)
        log('Step 7: Checking Ollama connection...');
        checkAndUpdateOllamaStatus().catch(err => {
            log('Ollama check failed (non-critical): ' + String(err));
        });
        
        // Step 8: Update status
        log('Step 8: Updating status to ready...');
        statusBar.setStatus('ready', 'Asset-Aware MCP: Ready');
        await vscode.commands.executeCommand('setContext', CONTEXT_READY, true);
        
        // Show walkthrough on first activation
        showFirstTimeWalkthrough(context);
        
        log('Extension activated successfully!');
        
    } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        log('ACTIVATION ERROR: ' + errorMsg);
        if (error instanceof Error && error.stack) {
            log('Stack trace: ' + error.stack);
        }
        statusBar?.setStatus('error', 'Asset-Aware MCP: Activation failed');
        vscode.window.showErrorMessage('Asset-Aware MCP activation failed: ' + errorMsg + '. Check Output panel for details.');
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
    return extensionContext.extensionPath;
}

/**
 * Register extension commands
 */
function registerCommands(context: vscode.ExtensionContext): void {
    context.subscriptions.push(
        vscode.commands.registerCommand('assetAwareMcp.setupWizard', async () => {
            await runSetupWizard();
        })
    );
    
    context.subscriptions.push(
        vscode.commands.registerCommand('assetAwareMcp.openSettings', async () => {
            SettingsPanel.createOrShow(context.extensionUri, envManager);
        })
    );
    
    context.subscriptions.push(
        vscode.commands.registerCommand('assetAwareMcp.editEnv', async () => {
            const envPath = envManager.getEnvPath();
            if (!fs.existsSync(envPath)) {
                await envManager.createDefaultEnv();
            }
            const doc = await vscode.workspace.openTextDocument(envPath);
            await vscode.window.showTextDocument(doc);
        })
    );
    
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
    
    context.subscriptions.push(
        vscode.commands.registerCommand('assetAwareMcp.refreshStatus', async () => {
            await statusTreeProvider.refresh();
            await documentTreeProvider.refresh();
            await tableTreeProvider.refresh();
            await checkAndUpdateOllamaStatus();
            vscode.window.showInformationMessage('Status refreshed!');
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('assetAwareMcp.checkDependencies', async () => {
            await checkSystemDependencies();
        })
    );
    
    context.subscriptions.push(
        vscode.commands.registerCommand('assetAwareMcp.showOutput', () => {
            outputChannel.show();
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('assetAwareMcp.openTableExcel', async (item: any) => {
            if (item && item.value) {
                const dataDir = envManager.getDataDir();
                const tablesDir = path.join(dataDir, 'tables');
                
                // Find the most recent Excel file for this table
                const files = fs.readdirSync(tablesDir);
                const excelFiles = files.filter(f => f.startsWith(item.value) && f.endsWith('.xlsx'));
                
                if (excelFiles.length > 0) {
                    // Sort by name (which includes timestamp) and get the last one
                    excelFiles.sort();
                    const latestExcel = excelFiles[excelFiles.length - 1];
                    const excelPath = path.join(tablesDir, latestExcel);
                    vscode.env.openExternal(vscode.Uri.file(excelPath));
                } else {
                    vscode.window.showWarningMessage('No Excel file found for this table. Use "render_table" tool to generate one.');
                }
            }
        })
    );
}

/**
 * Check system dependencies
 */
async function checkSystemDependencies(): Promise<void> {
    const depChannel = vscode.window.createOutputChannel('Asset-Aware MCP Dependencies');
    depChannel.show();
    depChannel.appendLine('=== Checking System Dependencies ===');
    depChannel.appendLine('');

    let allOk = true;

    // Check uv
    try {
        const { stdout } = await execAsync('uv --version');
        depChannel.appendLine('✅ uv: ' + stdout.trim());
    } catch {
        depChannel.appendLine('❌ uv: NOT FOUND (required)');
        depChannel.appendLine('   Run "Asset-Aware MCP: Setup Wizard" to install');
        allOk = false;
    }

    // Check uvx can find asset-aware-mcp
    depChannel.appendLine('');
    depChannel.appendLine('=== Checking MCP Server ===');
    
    try {
        await execAsync('uvx --help', { timeout: 5000 });
        depChannel.appendLine('✅ uvx: available');
        
        // Check if asset-aware-mcp is accessible via uvx
        depChannel.appendLine('   Will use: uvx asset-aware-mcp');
        depChannel.appendLine('   (Package will be auto-installed from PyPI on first use)');
    } catch {
        depChannel.appendLine('⚠️ uvx: not available (uv may need update)');
    }
    
    // Check for local development source
    const workspaceRoot = getWorkspaceRoot();
    const serverPath = path.join(workspaceRoot, 'src', 'server.py');
    const pyprojectPath = path.join(workspaceRoot, 'pyproject.toml');
    
    if (fs.existsSync(serverPath) && fs.existsSync(pyprojectPath)) {
        depChannel.appendLine('');
        depChannel.appendLine('📁 Local development source detected:');
        depChannel.appendLine('   ' + workspaceRoot);
        depChannel.appendLine('   (Will use local source instead of PyPI)');
    }
    
    depChannel.appendLine('');
    depChannel.appendLine('=== VS Code Info ===');
    depChannel.appendLine('VS Code Version: ' + vscode.version);
    depChannel.appendLine('MCP API Available: ' + String(typeof vscode.lm?.registerMcpServerDefinitionProvider === 'function'));

    depChannel.appendLine('');
    if (allOk) {
        depChannel.appendLine('✅ All required dependencies are met!');
        vscode.window.showInformationMessage('✅ All system dependencies are met!');
    } else {
        depChannel.appendLine('❌ Some dependencies are missing. See above for details.');
        vscode.window.showErrorMessage('❌ Some dependencies are missing. Check output for details.');
    }
}

async function runSetupWizard(): Promise<void> {
    log('Running setup wizard...');
    
    const result = await vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: 'Asset-Aware MCP Setup',
            cancellable: false
        },
        async (progress) => {
            progress.report({ message: 'Checking configuration...', increment: 0 });
            
            if (!fs.existsSync(envManager.getEnvPath())) {
                await envManager.createDefaultEnv();
                progress.report({ message: '.env created ✓', increment: 25 });
            } else {
                progress.report({ message: '.env exists ✓', increment: 25 });
            }
            
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

async function checkOllamaConnection(): Promise<boolean> {
    const config = vscode.workspace.getConfiguration('assetAwareMcp');
    const host = config.get<string>('ollamaHost', 'http://localhost:11434');
    
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        const response = await fetch(host + '/api/tags', { signal: controller.signal });
        clearTimeout(timeoutId);
        return response.ok;
    } catch {
        return false;
    }
}

async function checkAndUpdateOllamaStatus(): Promise<boolean> {
    const connected = await checkOllamaConnection();
    await vscode.commands.executeCommand('setContext', CONTEXT_OLLAMA_CONNECTED, connected);
    await statusTreeProvider?.refresh();
    return connected;
}

function showFirstTimeWalkthrough(context: vscode.ExtensionContext): void {
    const isFirstActivation = context.globalState.get<boolean>(FIRST_ACTIVATION_KEY, true);
    
    if (isFirstActivation) {
        context.globalState.update(FIRST_ACTIVATION_KEY, false);
        vscode.commands.executeCommand(
            'workbench.action.openWalkthrough',
            'u9401066.asset-aware-mcp#assetAwareMcp.welcome',
            false
        );
    }
}

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
    vscodeVersion: string;
    mcpApiAvailable: boolean;
}

async function getExtensionStatus(): Promise<ExtensionStatus> {
    const config = vscode.workspace.getConfiguration('assetAwareMcp');
    const env = await envManager.readEnv();
    const dataDir = path.resolve(getWorkspaceRoot(), env.DATA_DIR || './data');
    
    let documentCount = 0;
    if (fs.existsSync(dataDir)) {
        const files = fs.readdirSync(dataDir);
        documentCount = files.filter(f => {
            try { return fs.statSync(path.join(dataDir, f)).isDirectory(); }
            catch { return false; }
        }).length;
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
        documentCount: documentCount,
        vscodeVersion: vscode.version,
        mcpApiAvailable: typeof vscode.lm?.registerMcpServerDefinitionProvider === 'function'
    };
}

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
        body { font-family: var(--vscode-font-family); padding: 20px; color: var(--vscode-foreground); background: var(--vscode-editor-background); }
        h1 { color: var(--vscode-titleBar-activeForeground); display: flex; align-items: center; gap: 10px; }
        .section { background: var(--vscode-editor-inactiveSelectionBackground); padding: 15px; border-radius: 8px; margin: 15px 0; }
        .section h2 { margin-top: 0; font-size: 14px; color: var(--vscode-descriptionForeground); }
        .item { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid var(--vscode-panel-border); }
        .item:last-child { border-bottom: none; }
        .status { font-weight: bold; }
        .ok { color: #4caf50; }
        .error { color: #f44336; }
        .warning { color: #ff9800; }
        .info { color: #2196f3; }
        code { background: var(--vscode-textCodeBlock-background); padding: 2px 6px; border-radius: 4px; font-size: 12px; }
    </style>
</head>
<body>
    <h1>📚 Asset-Aware MCP Status</h1>
    <div class="section">
        <h2>VS Code Environment</h2>
        <div class="item"><span>VS Code Version:</span><span class="info">${status.vscodeVersion}</span></div>
        <div class="item"><span>MCP API Available:</span><span class="status ${status.mcpApiAvailable ? 'ok' : 'error'}">${status.mcpApiAvailable ? checkmark + ' Yes' : cross + ' No (Need VS Code 1.96+ & Copilot)'}</span></div>
    </div>
    <div class="section">
        <h2>Configuration</h2>
        <div class="item"><span>.env File:</span><span class="status ${status.envExists ? 'ok' : 'error'}">${status.envExists ? checkmark + ' Exists' : cross + ' Missing'}</span></div>
        <div class="item"><span>Path:</span><code>${status.envPath}</code></div>
        <div class="item"><span>LLM Backend:</span><span class="info">${status.llmBackend.toUpperCase()}</span></div>
    </div>
    <div class="section">
        <h2>Ollama Connection</h2>
        <div class="item"><span>Host:</span><code>${status.ollamaHost}</code></div>
        <div class="item"><span>Model:</span><span>${status.ollamaModel}</span></div>
        <div class="item"><span>Status:</span><span class="status ${status.ollamaConnected ? 'ok' : 'error'}">${status.ollamaConnected ? checkmark + ' Connected' : cross + ' Disconnected'}</span></div>
    </div>
    <div class="section">
        <h2>OpenAI</h2>
        <div class="item"><span>API Key:</span><span class="status ${status.openaiConfigured ? 'ok' : 'warning'}">${status.openaiConfigured ? checkmark + ' Configured' : warning + ' Not configured'}</span></div>
    </div>
    <div class="section">
        <h2>Documents</h2>
        <div class="item"><span>Data Directory:</span><code>${status.dataDir}</code></div>
        <div class="item"><span>Ingested Documents:</span><span class="info">${status.documentCount}</span></div>
    </div>
</body>
</html>`;
}

export function deactivate(): void {
    log('Extension is deactivating...');
    statusBar?.dispose();
}
