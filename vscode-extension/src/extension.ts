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
import { exec, execFile } from 'child_process';
import { promisify } from 'util';
import { AssetAwareMcpProvider, LAST_SERVER_VERSION_KEY } from './mcpProvider';
import { StatusBarManager } from './statusBar';
import { SettingsPanel } from './settingsPanel';
import { EnvManager } from './envManager';
import { InstallInfo, StatusTreeProvider } from './statusTreeProvider';
import { DocumentTreeProvider } from './documentTreeProvider';
import { TableTreeProvider } from './tableTreeProvider';
import { DfmEditorService, DfmLanguageFeatures } from './dfm';
import { installAssistantAssets } from './assistantAssets';
import { installClineMcpServer } from './clineMcpConfig';
import { installCodexMcpServer } from './codexMcpConfig';
import { installCopilotMcpConfig } from './copilotMcpConfig';
import {
    checkOllamaModels,
    formatOllamaPullCommands,
    OllamaModelStatus,
} from './ollama';
import {
    DEFAULT_TORCH_BACKEND,
    findUvPath,
    getAssetAwareRuntimeProbeArgs,
    getUvVersion,
    getUvxLaunch,
    MARKER_BACKEND_SECURITY_HOLD_MESSAGE,
    PREFERRED_RUNTIME_PYTHON,
} from './uv';

const execAsync = promisify(exec);
const execFileAsync = promisify(execFile);

// Module-level variables
let mcpProvider: AssetAwareMcpProvider;
let statusBar: StatusBarManager;
let envManager: EnvManager;
let statusTreeProvider: StatusTreeProvider;
let documentTreeProvider: DocumentTreeProvider;
let tableTreeProvider: TableTreeProvider;
let dfmEditorService: DfmEditorService;
let dfmLanguageFeatures: DfmLanguageFeatures;
let extensionContext: vscode.ExtensionContext;
let outputChannel: vscode.OutputChannel;
let resolvedUvPath: string | null = null;
let runtimeSyncListenersRegistered = false;

export interface AssetAwareExtensionApi {
    getMcpProviderForTests(): AssetAwareMcpProvider | undefined;
}

// Context keys
const CONTEXT_READY = 'assetAwareMcp.ready';
const CONTEXT_OLLAMA_CONNECTED = 'assetAwareMcp.ollamaConnected';
const FIRST_ACTIVATION_KEY = 'assetAwareMcp.firstActivation';
const RUNTIME_PREPARED_VERSION_KEY = 'assetAwareMcp.runtimePreparedVersion';
const RUNTIME_PREPARE_TIMEOUT_MS = 10 * 60 * 1000;

/**
 * Log message to output channel
 */
function log(message: string): void {
    const timestamp = new Date().toISOString();
    outputChannel?.appendLine(`[${timestamp}] ${message}`);
    console.log(`[Asset-Aware MCP] ${message}`);
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

                    await extensionContext.globalState.update('uvPath', uvPath);
                    mcpProvider?.refresh();
                    statusTreeProvider?.refresh();

                    return uvPath;
                } else {
                    throw new Error('uv installation completed but the binary could not be located.');
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
            log('uv is already installed: ' + await getUvVersion(existingPath));

            // Store the path for mcpProvider to use
            await extensionContext.globalState.update('uvPath', existingPath);
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
export async function activate(context: vscode.ExtensionContext): Promise<AssetAwareExtensionApi> {
    // Create output channel first for logging
    outputChannel = vscode.window.createOutputChannel('Asset-Aware MCP');
    context.subscriptions.push(outputChannel);

    log('Extension is activating...');

    extensionContext = context;
    const installInfo = getInstallInfo(context);
    log(`Install scope: ${installInfo.scope}`);
    log(`Extension path: ${installInfo.path}`);

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
        resolvedUvPath = uvPath;
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
        const storageRoot = getStorageRoot();
        envManager = new EnvManager(storageRoot);

        // Step 4: Initialize tree providers
        log('Step 4: Initializing tree providers...');
        statusTreeProvider = new StatusTreeProvider(envManager, installInfo, storageRoot);
        documentTreeProvider = new DocumentTreeProvider(envManager);
        tableTreeProvider = new TableTreeProvider(envManager);

        vscode.window.registerTreeDataProvider('assetAwareMcp.status', statusTreeProvider);
        vscode.window.registerTreeDataProvider('assetAwareMcp.documents', documentTreeProvider);
        vscode.window.registerTreeDataProvider('assetAwareMcp.tables', tableTreeProvider);

        // Step 5: Register MCP server provider (with version pinning & auto-upgrade)
        log('Step 5: Registering MCP server provider...');
        const currentVersion = context.extension.packageJSON.version as string;
        const lastServerVersion = context.globalState.get<string>(LAST_SERVER_VERSION_KEY);
        const needsUpgrade = lastServerVersion !== currentVersion;
        if (needsUpgrade) {
            log(`Server upgrade needed: ${lastServerVersion ?? '(first install)'} → ${currentVersion}`);
        } else {
            log(`Server version matches: ${currentVersion} (using cache)`);
        }
        mcpProvider = new AssetAwareMcpProvider(storageRoot, outputChannel, context, needsUpgrade);
        // Persist current version so next launch won't trigger upgrade again
        context.globalState.update(LAST_SERVER_VERSION_KEY, currentVersion);

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

        // Step 6a: Configure external MCP consumers and assistant assets
        log('Step 6a: Synchronizing MCP consumers and assistant assets...');
        if (uvPath) {
            ensureExternalMcpRuntimeAndSync(context, uvPath, needsUpgrade, true);
        }
        await installAssistantAssets(context);

        // Step 6b: Initialize DFM editor service
        log('Step 6b: Initializing DFM editor service...');
        dfmEditorService = new DfmEditorService(context, outputChannel);
        dfmEditorService.registerCommands();
        context.subscriptions.push(dfmEditorService);

        // Step 6c: Initialize DFM language features
        log('Step 6c: Initializing DFM language features...');
        dfmLanguageFeatures = new DfmLanguageFeatures();
        dfmLanguageFeatures.register();
        context.subscriptions.push(dfmLanguageFeatures);

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

    return {
        getMcpProviderForTests: () => mcpProvider,
    };
}

/**
 * Get workspace root path
 */
function getPrimaryWorkspaceRoot(): string | undefined {
    return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
}

function getInstallInfo(context: vscode.ExtensionContext): InstallInfo {
    switch (context.extensionMode) {
        case vscode.ExtensionMode.Development:
            return { scope: 'Workspace (development)', path: context.extensionUri.fsPath };
        case vscode.ExtensionMode.Test:
            return { scope: 'Workspace (test)', path: context.extensionUri.fsPath };
        default:
            return { scope: 'User (global)', path: context.extensionUri.fsPath };
    }
}

function getStorageRoot(): string {
    const workspaceRoot = getPrimaryWorkspaceRoot();
    const root = workspaceRoot ?? extensionContext.globalStorageUri.fsPath;
    fs.mkdirSync(root, { recursive: true });
    log(`Storage root set to ${root} (${workspaceRoot ? 'workspace' : 'global storage fallback'})`);
    return root;
}

function syncExternalMcpConsumers(
    context: vscode.ExtensionContext,
    uvPath: string,
    needsUpgrade: boolean = false,
    notifyUser: boolean = false,
    forceClineWorkspace: boolean = false,
): void {
    const updatedConsumers: string[] = [];

    try {
        if (installCopilotMcpConfig(context, uvPath, needsUpgrade)) {
            updatedConsumers.push('Copilot');
            log('Copilot workspace MCP config updated');
        }
    } catch (error) {
        log('Failed to update Copilot MCP config: ' + String(error));
    }

    try {
        if (installClineMcpServer(context, uvPath, needsUpgrade, { forceWorkspace: forceClineWorkspace })) {
            updatedConsumers.push('Cline');
            log('Cline MCP config updated');
        }
    } catch (error) {
        log('Failed to update Cline MCP config: ' + String(error));
    }

    try {
        if (installCodexMcpServer(context, uvPath, needsUpgrade)) {
            updatedConsumers.push('Codex');
            log('Codex MCP config updated');
        }
    } catch (error) {
        log('Failed to update Codex MCP config: ' + String(error));
    }

    if (notifyUser && updatedConsumers.length > 0) {
        vscode.window.showInformationMessage(
            `Asset-Aware MCP configured for ${updatedConsumers.join(', ')}. Reload the relevant client if it was already open.`,
        );
    }
}

async function prepareMcpServerRuntime(
    uvPath: string,
    needsUpgrade: boolean = false,
    progress?: vscode.Progress<{ message?: string; increment?: number }>,
): Promise<boolean> {
    const config = vscode.workspace.getConfiguration('assetAwareMcp');
    const extensionVersion = extensionContext.extension.packageJSON.version as string;
    const enableMarkerBackend = config.get('enableMarkerBackend', false);
    const torchBackend = config.get('torchBackend', DEFAULT_TORCH_BACKEND);
    const launch = getUvxLaunch(
        uvPath,
        PREFERRED_RUNTIME_PYTHON,
        enableMarkerBackend,
        torchBackend,
        extensionVersion,
        needsUpgrade,
    );
    const args = getAssetAwareRuntimeProbeArgs(launch.args);
    const uvCacheDir = path.join(getStorageRoot(), '.uv-cache');
    fs.mkdirSync(uvCacheDir, { recursive: true });
    const runtimeEnv = {
        ...process.env,
        UV_CACHE_DIR: uvCacheDir,
    };

    try {
        progress?.report({ message: `Preparing asset-aware-mcp ${extensionVersion} runtime...` });
        log(`Preparing MCP runtime: ${launch.command} ${args.join(' ')}`);
        log(
            `Preparing MCP runtime details: version=${extensionVersion}; ` +
            `mode=package; marker_backend=${String(enableMarkerBackend)}; ` +
            `torch_backend=${torchBackend}; timeout_ms=${RUNTIME_PREPARE_TIMEOUT_MS}`,
        );
        if (enableMarkerBackend) {
            log(MARKER_BACKEND_SECURITY_HOLD_MESSAGE);
        }
        log(`Preparing MCP runtime UV cache: ${uvCacheDir}`);
        const { stdout, stderr } = await execFileAsync(launch.command, args, {
            timeout: RUNTIME_PREPARE_TIMEOUT_MS,
            env: runtimeEnv,
        });
        const trimmedStdout = stdout.trim();
        const trimmedStderr = stderr.trim();
        if (trimmedStdout) {
            log('MCP runtime preparation stdout: ' + trimmedStdout);
        }
        if (trimmedStderr) {
            log('MCP runtime preparation stderr: ' + trimmedStderr);
        }
        await extensionContext.globalState.update(RUNTIME_PREPARED_VERSION_KEY, extensionVersion);
        log(`MCP runtime prepared for asset-aware-mcp ${extensionVersion}`);
        return true;
    } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        log(`MCP runtime preparation failed: ${message}`);
        const output = error as { stdout?: string; stderr?: string };
        if (output.stdout?.trim()) {
            log('MCP runtime preparation stdout: ' + output.stdout.trim());
        }
        if (output.stderr?.trim()) {
            log('MCP runtime preparation stderr: ' + output.stderr.trim());
        }
        return false;
    }
}

async function prepareRuntimeWithProgress(uvPath: string, needsUpgrade: boolean = false): Promise<boolean> {
    return vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: 'Preparing Asset-Aware MCP server runtime',
            cancellable: false,
        },
        async (progress) => prepareMcpServerRuntime(uvPath, needsUpgrade, progress),
    );
}

function ensureExternalMcpRuntimeAndSync(
    context: vscode.ExtensionContext,
    uvPath: string,
    needsUpgrade: boolean,
    notifyUser: boolean,
): void {
    const currentVersion = context.extension.packageJSON.version as string;
    const preparedVersion = context.globalState.get<string>(RUNTIME_PREPARED_VERSION_KEY);
    if (preparedVersion === currentVersion) {
        syncExternalMcpConsumers(context, uvPath, needsUpgrade, notifyUser);
        registerRuntimeSyncListeners(context);
        return;
    }

    prepareMcpServerRuntime(uvPath, needsUpgrade).then((prepared) => {
        if (!prepared) {
            vscode.window.showWarningMessage(
                'Asset-Aware MCP server runtime is not ready yet, so external MCP clients were not auto-updated. Run "Asset-Aware MCP: Prepare Server Runtime" and then configure MCP clients.',
            );
            return;
        }

        syncExternalMcpConsumers(context, uvPath, needsUpgrade, notifyUser);
        registerRuntimeSyncListeners(context);
    });
}

function registerRuntimeSyncListeners(context: vscode.ExtensionContext): void {
    if (runtimeSyncListenersRegistered) {
        return;
    }

    context.subscriptions.push(
        vscode.workspace.onDidChangeConfiguration((event) => {
            if (!event.affectsConfiguration('assetAwareMcp') || !resolvedUvPath) {
                return;
            }
            syncExternalMcpConsumers(context, resolvedUvPath);
        }),
    );

    context.subscriptions.push(
        vscode.workspace.onDidChangeWorkspaceFolders(() => {
            if (resolvedUvPath) {
                syncExternalMcpConsumers(context, resolvedUvPath);
            }
            installAssistantAssets(context).catch((error) => {
                log('Failed to sync assistant assets after workspace change: ' + String(error));
            });
        }),
    );

    runtimeSyncListenersRegistered = true;
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
        vscode.commands.registerCommand('assetAwareMcp.installAssistantAssets', async () => {
            await installAssistantAssets(context, 'manual');
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('assetAwareMcp.configureExternalMcp', async () => {
            if (!resolvedUvPath) {
                resolvedUvPath = await ensureUvInstalled();
            }
            if (!resolvedUvPath) {
                vscode.window.showErrorMessage('Asset-Aware MCP requires uv before MCP clients can be configured.');
                return;
            }
            const prepared = await prepareRuntimeWithProgress(resolvedUvPath, false);
            if (!prepared) {
                vscode.window.showWarningMessage(
                    'Asset-Aware MCP server runtime is not ready. Dependency downloads may still be running or blocked; MCP clients were not updated to avoid startup timeouts.',
                );
                return;
            }
            syncExternalMcpConsumers(context, resolvedUvPath, false, true, true);
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('assetAwareMcp.prepareServer', async () => {
            if (!resolvedUvPath) {
                resolvedUvPath = await ensureUvInstalled();
            }
            if (!resolvedUvPath) {
                vscode.window.showErrorMessage('Asset-Aware MCP requires uv before the server runtime can be prepared.');
                return;
            }

            const prepared = await prepareRuntimeWithProgress(resolvedUvPath, false);
            if (prepared) {
                vscode.window.showInformationMessage('Asset-Aware MCP server runtime is ready.');
            } else {
                vscode.window.showWarningMessage('Asset-Aware MCP server runtime could not be prepared. Check the Asset-Aware MCP output log for details.');
            }
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
            panel.webview.html = getStatusWebviewContent(status, panel.webview);
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('assetAwareMcp.checkConnection', async () => {
            statusBar.setStatus('initializing', 'Checking Ollama...');
            const status = await getOllamaModelStatus();
            await checkAndUpdateOllamaStatus(status);

            if (status.connected && status.missingModels.length === 0) {
                vscode.window.showInformationMessage('✅ Ollama is running and configured models are available!');
                statusBar.setStatus('ready', 'Asset-Aware MCP: Ready');
            } else if (status.connected) {
                vscode.window.showWarningMessage(
                    `Ollama is running, but configured models are missing:\n${formatOllamaPullCommands(status.missingModels)}`,
                );
                statusBar.setStatus('warning', 'Asset-Aware MCP: Ollama model missing');
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
        vscode.commands.registerCommand('assetAwareMcp.upgradeServer', async () => {
            const currentVersion = extensionContext.extension.packageJSON.version as string;
            log(`Force upgrade: clearing cached server version to trigger --upgrade`);
            // Reset stored version so next MCP launch will pass --upgrade
            await extensionContext.globalState.update(LAST_SERVER_VERSION_KEY, undefined);

            // Recreate provider with upgrade flag
            mcpProvider = new AssetAwareMcpProvider(getStorageRoot(), outputChannel, extensionContext, true);

            if (typeof vscode.lm?.registerMcpServerDefinitionProvider === 'function') {
                const providerDisposable = vscode.lm.registerMcpServerDefinitionProvider(
                    'asset-aware-mcp.servers',
                    mcpProvider
                );
                context.subscriptions.push(providerDisposable);
            }
            mcpProvider.refresh();

            vscode.window.showInformationMessage(
                `Asset-Aware MCP: Server will upgrade to v${currentVersion} on next MCP connection.`
            );
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
        const uvPath = await findUvPath();
        if (!uvPath) {
            throw new Error('uv not found');
        }

        depChannel.appendLine('✅ uv: ' + await getUvVersion(uvPath));
        depChannel.appendLine('   Path: ' + uvPath);
    } catch {
        depChannel.appendLine('❌ uv: NOT FOUND (required)');
        depChannel.appendLine('   Run "Asset-Aware MCP: Setup Wizard" to install');
        allOk = false;
    }

    // Check uvx can find asset-aware-mcp
    depChannel.appendLine('');
    depChannel.appendLine('=== Checking MCP Server ===');

    try {
        const uvPath = await findUvPath();
        if (!uvPath) {
            throw new Error('uv not found');
        }

        const config = vscode.workspace.getConfiguration('assetAwareMcp');
        const enableMarkerBackend = config.get('enableMarkerBackend', false);
        const torchBackend = config.get('torchBackend', DEFAULT_TORCH_BACKEND);
        const extensionVersion = extensionContext.extension.packageJSON.version as string;
        const lastVersion = extensionContext.globalState.get<string>(LAST_SERVER_VERSION_KEY);
        const launch = getUvxLaunch(
            uvPath,
            PREFERRED_RUNTIME_PYTHON,
            enableMarkerBackend,
            torchBackend,
            extensionVersion,
            lastVersion !== extensionVersion,
        );
        const preparedVersion = extensionContext.globalState.get<string>(RUNTIME_PREPARED_VERSION_KEY);
        depChannel.appendLine('✅ MCP launcher: available');

        // Check if asset-aware-mcp is accessible via uvx
        depChannel.appendLine('   Will use: ' + launch.command + ' ' + [...launch.args, 'asset-aware-mcp'].join(' '));
        depChannel.appendLine('   Preferred Python runtime: ' + PREFERRED_RUNTIME_PYTHON);
        depChannel.appendLine('   Server version pin: ' + extensionVersion);
        depChannel.appendLine('   Cached version: ' + (lastVersion ?? '(first install)'));
        depChannel.appendLine('   Marker backend enabled: ' + String(enableMarkerBackend));
        if (enableMarkerBackend) {
            depChannel.appendLine('   ' + MARKER_BACKEND_SECURITY_HOLD_MESSAGE);
        }
        depChannel.appendLine('   Runtime prepared: ' + (preparedVersion === extensionVersion ? 'yes' : 'no'));
        if (preparedVersion !== extensionVersion) {
            allOk = false;
            depChannel.appendLine('   Run "Asset-Aware MCP: Prepare Server Runtime" before connecting Cline/Copilot/Codex.');
        }
    } catch {
        depChannel.appendLine('⚠️ MCP launcher: not available (uv may need update)');
    }

    // Check for local development source
    const workspaceRoot = getPrimaryWorkspaceRoot();
    const serverPath = workspaceRoot ? path.join(workspaceRoot, 'src', 'server.py') : '';
    const pyprojectPath = workspaceRoot ? path.join(workspaceRoot, 'pyproject.toml') : '';

    if (workspaceRoot && fs.existsSync(serverPath) && fs.existsSync(pyprojectPath)) {
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
            const ollamaStatus = await getOllamaModelStatus();
            const ollamaOk = await checkAndUpdateOllamaStatus(ollamaStatus);

            if (ollamaStatus.connected && ollamaStatus.missingModels.length > 0) {
                vscode.window.showWarningMessage(
                    `Ollama is running, but configured models are missing:\n${formatOllamaPullCommands(ollamaStatus.missingModels)}`,
                );
            } else if (!ollamaOk) {
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

function getRequiredOllamaModels(): string[] {
    const config = vscode.workspace.getConfiguration('assetAwareMcp');
    return [
        config.get<string>('ollamaModel', 'qwen2.5:7b'),
        config.get<string>('ollamaEmbeddingModel', 'nomic-embed-text'),
    ];
}

async function getOllamaModelStatus(): Promise<OllamaModelStatus> {
    const config = vscode.workspace.getConfiguration('assetAwareMcp');
    const host = config.get<string>('ollamaHost', 'http://localhost:11434');
    return checkOllamaModels(host, getRequiredOllamaModels());
}

async function checkAndUpdateOllamaStatus(status?: OllamaModelStatus): Promise<boolean> {
    const ollamaStatus = status ?? await getOllamaModelStatus();
    await vscode.commands.executeCommand('setContext', CONTEXT_OLLAMA_CONNECTED, ollamaStatus.connected);
    await statusTreeProvider?.refresh();
    return ollamaStatus.connected && ollamaStatus.missingModels.length === 0;
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
    ollamaMissingModels: string[];
    openaiConfigured: boolean;
    dataDir: string;
    documentCount: number;
    vscodeVersion: string;
    mcpApiAvailable: boolean;
}

async function getExtensionStatus(): Promise<ExtensionStatus> {
    const config = vscode.workspace.getConfiguration('assetAwareMcp');
    const env = await envManager.readEnv();
    const dataDir = envManager.getDataDir();
    const ollamaStatus = await getOllamaModelStatus();

    const documentCount = envManager.listDocuments().length;

    return {
        envExists: fs.existsSync(envManager.getEnvPath()),
        envPath: envManager.getEnvPath(),
        llmBackend: env.LLM_BACKEND || 'ollama',
        ollamaHost: env.OLLAMA_HOST || config.get<string>('ollamaHost', 'http://localhost:11434'),
        ollamaModel: env.OLLAMA_MODEL || config.get<string>('ollamaModel', 'qwen2.5:7b'),
        ollamaConnected: ollamaStatus.connected,
        ollamaMissingModels: ollamaStatus.missingModels,
        openaiConfigured: !!(env.OPENAI_API_KEY),
        dataDir: dataDir,
        documentCount: documentCount,
        vscodeVersion: vscode.version,
        mcpApiAvailable: typeof vscode.lm?.registerMcpServerDefinitionProvider === 'function'
    };
}

function escapeHtml(value: string): string {
    return value
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function getStatusWebviewContent(status: ExtensionStatus, webview: vscode.Webview): string {
    const checkmark = '✅';
    const cross = '❌';
    const warning = '⚠️';
    const vscodeVersion = escapeHtml(status.vscodeVersion);
    const envPath = escapeHtml(status.envPath);
    const llmBackend = escapeHtml(status.llmBackend.toUpperCase());
    const ollamaHost = escapeHtml(status.ollamaHost);
    const ollamaModel = escapeHtml(status.ollamaModel);
    const missingModels = escapeHtml(status.ollamaMissingModels.join(', ') || 'None');
    const dataDir = escapeHtml(status.dataDir);

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline';">
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
	        <div class="item"><span>VS Code Version:</span><span class="info">${vscodeVersion}</span></div>
	        <div class="item"><span>MCP API Available:</span><span class="status ${status.mcpApiAvailable ? 'ok' : 'error'}">${status.mcpApiAvailable ? checkmark + ' Yes' : cross + ' No (Need VS Code 1.96+ & Copilot)'}</span></div>
	    </div>
	    <div class="section">
	        <h2>Configuration</h2>
	        <div class="item"><span>.env File:</span><span class="status ${status.envExists ? 'ok' : 'error'}">${status.envExists ? checkmark + ' Exists' : cross + ' Missing'}</span></div>
	        <div class="item"><span>Path:</span><code>${envPath}</code></div>
	        <div class="item"><span>LLM Backend:</span><span class="info">${llmBackend}</span></div>
	    </div>
	    <div class="section">
	        <h2>Ollama Connection</h2>
	        <div class="item"><span>Host:</span><code>${ollamaHost}</code></div>
	        <div class="item"><span>Model:</span><span>${ollamaModel}</span></div>
	        <div class="item"><span>Status:</span><span class="status ${status.ollamaConnected ? 'ok' : 'error'}">${status.ollamaConnected ? checkmark + ' Connected' : cross + ' Disconnected'}</span></div>
	        <div class="item"><span>Missing Models:</span><span class="status ${status.ollamaMissingModels.length === 0 ? 'ok' : 'warning'}">${missingModels}</span></div>
	    </div>
    <div class="section">
        <h2>OpenAI</h2>
        <div class="item"><span>API Key:</span><span class="status ${status.openaiConfigured ? 'ok' : 'warning'}">${status.openaiConfigured ? checkmark + ' Configured' : warning + ' Not configured'}</span></div>
    </div>
	    <div class="section">
	        <h2>Documents</h2>
	        <div class="item"><span>Data Directory:</span><code>${dataDir}</code></div>
	        <div class="item"><span>Ingested Documents:</span><span class="info">${status.documentCount}</span></div>
    </div>
</body>
</html>`;
}

export function deactivate(): void {
    log('Extension is deactivating...');
    statusBar?.dispose();
}
