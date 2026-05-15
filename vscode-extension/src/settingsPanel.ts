/**
 * Settings Panel (Webview)
 *
 * Provides a UI for editing .env configuration with visual feedback.
 * Users can input settings and save to local .env file.
 */

import * as vscode from 'vscode';
import {
    DEFAULT_DATA_DIR,
    DEFAULT_ENABLE_LIGHTRAG,
    DEFAULT_ETL_PROFILE,
    DEFAULT_LIGHTRAG_EMBEDDING_MODEL,
    DEFAULT_LIGHTRAG_WORKING_DIR,
    DEFAULT_LLM_BACKEND,
    DEFAULT_OLLAMA_EMBEDDING_MODEL,
    DEFAULT_OLLAMA_HOST,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OPENAI_MODEL,
    envBoolean,
} from './defaults';
import { EnvManager } from './envManager';
import { checkOllamaModels, formatOllamaPullCommands, getRequiredOllamaModelsForLightRag } from './ollama';

function escapeHtml(value: string): string {
    return value
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function getNonce(): string {
    const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let nonce = '';
    for (let i = 0; i < 32; i++) {
        nonce += alphabet.charAt(Math.floor(Math.random() * alphabet.length));
    }
    return nonce;
}

const ALLOWED_ENV_KEYS = new Set([
    'LLM_BACKEND',
    'ETL_PROFILE',
    'OLLAMA_HOST',
    'OLLAMA_MODEL',
    'OLLAMA_EMBEDDING_MODEL',
    'OPENAI_API_KEY',
    'OPENAI_MODEL',
    'LIGHTRAG_EMBEDDING_MODEL',
    'DATA_DIR',
    'LIGHTRAG_WORKING_DIR',
    'ENABLE_LIGHTRAG',
]);

export class SettingsPanel {
    public static currentPanel: SettingsPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private readonly _extensionUri: vscode.Uri;
    private readonly _envManager: EnvManager;
    private _disposables: vscode.Disposable[] = [];

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri, envManager: EnvManager) {
        this._panel = panel;
        this._extensionUri = extensionUri;
        this._envManager = envManager;

        this._update();

        // Handle messages from the webview
        this._panel.webview.onDidReceiveMessage(
            async (message) => {
                switch (message.command) {
                    case 'save':
                        if (message.settings && typeof message.settings === 'object') {
                            await this._saveSettings(message.settings as Record<string, string>);
                        }
                        break;
                    case 'testOllama':
                        await this._testOllamaConnection(message.host);
                        break;
                    case 'refresh':
                        await this._update();
                        break;
                    case 'setProfile':
                        await this._setEtlProfile(message.profile);
                        break;
                }
            },
            null,
            this._disposables
        );

        // Handle panel disposal
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
    }

    public static createOrShow(extensionUri: vscode.Uri, envManager: EnvManager): void {
        const column = vscode.ViewColumn.One;

        if (SettingsPanel.currentPanel) {
            SettingsPanel.currentPanel._panel.reveal(column);
            return;
        }

        const panel = vscode.window.createWebviewPanel(
            'assetAwareMcpSettings',
            'Asset-Aware MCP Settings',
            column,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
            }
        );

        SettingsPanel.currentPanel = new SettingsPanel(panel, extensionUri, envManager);
    }

    private async _update(): Promise<void> {
        const env = await this._envManager.readEnv();
        // Convert EnvConfig to Record<string, string> (filter out undefined values)
        const envRecord: Record<string, string> = {};
        for (const [key, value] of Object.entries(env)) {
            if (value !== undefined) {
                envRecord[key] = value;
            }
        }
        this._panel.webview.html = this._getHtmlContent(envRecord);
    }

    private async _saveSettings(settings: Record<string, string>): Promise<void> {
        try {
            // Update each setting
            for (const [key, value] of Object.entries(settings)) {
                if (!ALLOWED_ENV_KEYS.has(key)) {
                    continue;
                }
                await this._envManager.updateEnv(key, value);
            }

            vscode.window.showInformationMessage('✅ Settings saved to .env file!');

            // Refresh the display
            await this._update();

            // Notify to refresh MCP server
            vscode.commands.executeCommand('assetAwareMcp.refreshStatus');

        } catch (error) {
            vscode.window.showErrorMessage(`Failed to save settings: ${error}`);
        }
    }

    private async _testOllamaConnection(host: string): Promise<void> {
        try {
            const env = await this._envManager.readEnv();
            const status = await checkOllamaModels(
                host,
                getRequiredOllamaModelsForLightRag(
                    env.OLLAMA_MODEL || DEFAULT_OLLAMA_MODEL,
                    env.OLLAMA_EMBEDDING_MODEL || DEFAULT_OLLAMA_EMBEDDING_MODEL,
                    envBoolean(env.ENABLE_LIGHTRAG, DEFAULT_ENABLE_LIGHTRAG),
                ),
            );
            if (status.connected) {
                const models = status.models.join(', ') || 'None';
                vscode.window.showInformationMessage(`✅ Ollama connected! Models: ${models}`);
                if (status.missingModels.length > 0) {
                    vscode.window.showWarningMessage(
                        `Configured Ollama models are missing:\n${formatOllamaPullCommands(status.missingModels)}`,
                    );
                }

                this._panel.webview.postMessage({
                    command: 'ollamaStatus',
                    connected: true,
                    models: status.models,
                    missingModels: status.missingModels,
                });
            } else {
                throw new Error('Connection failed');
            }
        } catch {
            vscode.window.showWarningMessage('❌ Cannot connect to Ollama');
            this._panel.webview.postMessage({ command: 'ollamaStatus', connected: false });
        }
    }

    private async _setEtlProfile(profileName: string): Promise<void> {
        try {
            // This will be called via MCP tool when the server is running
            // For now, just save to .env for next server restart
            await this._envManager.updateEnv('ETL_PROFILE', profileName);
            vscode.window.showInformationMessage(`✅ ETL Profile set to: ${profileName}`);

            // Notify to refresh MCP server
            vscode.commands.executeCommand('assetAwareMcp.refreshStatus');
        } catch (error) {
            vscode.window.showErrorMessage(`Failed to set ETL profile: ${error}`);
        }
    }

    private _getHtmlContent(env: Record<string, string>): string {
        const nonce = getNonce();
        const webview = this._panel.webview;
        const value = (key: string, fallback = '') => escapeHtml(env[key] || fallback);
        const lightRagEnabled = envBoolean(env['ENABLE_LIGHTRAG'], DEFAULT_ENABLE_LIGHTRAG);

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';">
    <title>Asset-Aware MCP Settings</title>
    <style>
        * {
            box-sizing: border-box;
        }
        body {
            font-family: var(--vscode-font-family);
            padding: 20px;
            color: var(--vscode-foreground);
            background: var(--vscode-editor-background);
            max-width: 800px;
            margin: 0 auto;
        }
        h1 {
            display: flex;
            align-items: center;
            gap: 10px;
            color: var(--vscode-titleBar-activeForeground);
            border-bottom: 1px solid var(--vscode-panel-border);
            padding-bottom: 15px;
        }
        .section {
            background: var(--vscode-editor-inactiveSelectionBackground);
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }
        .section h2 {
            margin-top: 0;
            font-size: 16px;
            color: var(--vscode-descriptionForeground);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 6px;
            font-weight: 500;
            color: var(--vscode-foreground);
        }
        .description {
            font-size: 12px;
            color: var(--vscode-descriptionForeground);
            margin-bottom: 8px;
        }
        input[type="text"],
        input[type="password"],
        select {
            width: 100%;
            padding: 10px;
            border: 1px solid var(--vscode-input-border);
            background: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border-radius: 4px;
            font-size: 14px;
        }
        input:focus, select:focus {
            outline: none;
            border-color: var(--vscode-focusBorder);
        }
        .input-group {
            display: flex;
            gap: 10px;
        }
        .input-group input {
            flex: 1;
        }
        .btn {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.2s;
        }
        .btn:hover {
            background: var(--vscode-button-hoverBackground);
        }
        .btn-secondary {
            background: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
        }
        .btn-secondary:hover {
            background: var(--vscode-button-secondaryHoverBackground);
        }
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
        }
        .status-connected {
            background: #1b5e20;
            color: #a5d6a7;
        }
        .status-disconnected {
            background: #b71c1c;
            color: #ef9a9a;
        }
        .status-unknown {
            background: #616161;
            color: #e0e0e0;
        }
        .file-path {
            background: var(--vscode-textCodeBlock-background);
            padding: 8px 12px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
        }
        .actions {
            display: flex;
            gap: 10px;
            justify-content: flex-end;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid var(--vscode-panel-border);
        }
        .hint {
            font-size: 11px;
            color: var(--vscode-descriptionForeground);
            margin-top: 4px;
        }
        .toggle-visibility {
            cursor: pointer;
            padding: 5px;
            background: transparent;
            border: none;
            color: var(--vscode-foreground);
        }
    </style>
</head>
<body>
    <h1>⚙️ Asset-Aware MCP Settings</h1>

    <div class="file-path">
        <span>📁 Configuration file: <code>.env</code></span>
        <span id="ollamaStatus" class="status-badge status-unknown">
            Status: Unknown
        </span>
    </div>

    <form id="settingsForm">
        <div class="section">
            <h2>🤖 LLM Backend</h2>

            <div class="form-group">
                <label for="llmBackend">Backend</label>
                <p class="description">Choose between local Ollama or cloud OpenAI</p>
                <select id="llmBackend" name="LLM_BACKEND">
                    <option value="ollama" ${env['LLM_BACKEND'] === DEFAULT_LLM_BACKEND || !env['LLM_BACKEND'] ? 'selected' : ''}>Ollama (Local)</option>
                    <option value="openai" ${env['LLM_BACKEND'] === 'openai' ? 'selected' : ''}>OpenAI (Cloud)</option>
                </select>
            </div>
        </div>

        <div class="section">
            <h2>📄 ETL Profile</h2>

            <div class="form-group">
                <label for="etlProfile">Document Format Profile</label>
                <p class="description">Different journals/formats need different extraction settings. Choose a profile that matches your documents.</p>
                <select id="etlProfile" name="ETL_PROFILE">
                    <option value="default" ${env['ETL_PROFILE'] === DEFAULT_ETL_PROFILE || !env['ETL_PROFILE'] ? 'selected' : ''}>Default (General purpose)</option>
                    <option value="arxiv" ${env['ETL_PROFILE'] === 'arxiv' ? 'selected' : ''}>arXiv (Double-column preprints)</option>
                    <option value="nature" ${env['ETL_PROFILE'] === 'nature' ? 'selected' : ''}>Nature/Scientific Reports</option>
                    <option value="ieee" ${env['ETL_PROFILE'] === 'ieee' ? 'selected' : ''}>IEEE (Roman numeral sections)</option>
                    <option value="elsevier" ${env['ETL_PROFILE'] === 'elsevier' ? 'selected' : ''}>Elsevier Journals</option>
                </select>
                <p class="hint">Profile affects: heading detection thresholds, noise filtering, caption patterns, section keywords</p>
            </div>
        </div>

        <div class="section" id="ollamaSection">
            <h2>🦙 Ollama Settings</h2>

            <div class="form-group">
                <label for="ollamaHost">Ollama Host URL</label>
                <div class="input-group">
                    <input type="text" id="ollamaHost" name="OLLAMA_HOST"
                           value="${value('OLLAMA_HOST', DEFAULT_OLLAMA_HOST)}"
                           placeholder="${DEFAULT_OLLAMA_HOST}">
                    <button type="button" id="testOllamaButton" class="btn btn-secondary">Test Connection</button>
                </div>
            </div>

            <div class="form-group">
                <label for="ollamaModel">LLM Model</label>
                <p class="description">Model for text generation (CPU default: granite4.1:3b; GPU hint: granite4.1:8b)</p>
                <input type="text" id="ollamaModel" name="OLLAMA_MODEL"
                       value="${value('OLLAMA_MODEL', DEFAULT_OLLAMA_MODEL)}"
                       placeholder="${DEFAULT_OLLAMA_MODEL}">
            </div>

            <div class="form-group">
                <label for="ollamaEmbeddingModel">Embedding Model</label>
                <p class="description">Model for text embeddings (e.g., nomic-embed-text)</p>
                <input type="text" id="ollamaEmbeddingModel" name="OLLAMA_EMBEDDING_MODEL"
                       value="${value('OLLAMA_EMBEDDING_MODEL', DEFAULT_OLLAMA_EMBEDDING_MODEL)}"
                       placeholder="${DEFAULT_OLLAMA_EMBEDDING_MODEL}">
            </div>
        </div>

        <div class="section" id="openaiSection">
            <h2>🔑 OpenAI Settings</h2>

            <div class="form-group">
                <label for="openaiApiKey">API Key</label>
                <p class="description">Your OpenAI API key (starts with sk-)</p>
                <div class="input-group">
                    <input type="password" id="openaiApiKey" name="OPENAI_API_KEY"
                           value="${value('OPENAI_API_KEY')}"
                           placeholder="sk-...">
                    <button type="button" id="toggleOpenaiApiKey" class="toggle-visibility">👁️</button>
                </div>
                <p class="hint">Get your API key from <a href="https://platform.openai.com/api-keys">OpenAI Dashboard</a></p>
            </div>

            <div class="form-group">
                <label for="openaiModel">Model</label>
                <input type="text" id="openaiModel" name="OPENAI_MODEL"
                       value="${value('OPENAI_MODEL', DEFAULT_OPENAI_MODEL)}"
                       placeholder="${DEFAULT_OPENAI_MODEL}">
            </div>

            <div class="form-group">
                <label for="openaiEmbeddingModel">Embedding Model</label>
                <input type="text" id="openaiEmbeddingModel" name="LIGHTRAG_EMBEDDING_MODEL"
                       value="${escapeHtml(env['LIGHTRAG_EMBEDDING_MODEL'] || env['OPENAI_EMBEDDING_MODEL'] || DEFAULT_LIGHTRAG_EMBEDDING_MODEL)}"
                       placeholder="${DEFAULT_LIGHTRAG_EMBEDDING_MODEL}">
            </div>
        </div>

        <div class="section">
            <h2>📂 Storage</h2>

            <div class="form-group">
                <label for="dataDir">Data Directory</label>
                <p class="description">Directory for storing processed documents and manifests</p>
                <input type="text" id="dataDir" name="DATA_DIR"
                       value="${value('DATA_DIR', DEFAULT_DATA_DIR)}"
                       placeholder="${DEFAULT_DATA_DIR}">
            </div>

            <div class="form-group">
                <label for="lightragDir">LightRAG Directory</label>
                <p class="description">Directory for LightRAG knowledge graph data</p>
                <input type="text" id="lightragDir" name="LIGHTRAG_WORKING_DIR"
                       value="${escapeHtml(env['LIGHTRAG_WORKING_DIR'] || env['LIGHTRAG_DIR'] || DEFAULT_LIGHTRAG_WORKING_DIR)}"
                       placeholder="${DEFAULT_LIGHTRAG_WORKING_DIR}">
            </div>

            <div class="form-group">
                <label for="enableLightRag">
                    <input type="checkbox" id="enableLightRag" name="ENABLE_LIGHTRAG" value="true" ${lightRagEnabled ? 'checked' : ''}>
                    Enable LightRAG knowledge graph
                </label>
                <p class="description">Optional KG indexing and querying. Leave disabled for CPU-only or document-only workflows.</p>
            </div>
        </div>

        <div class="actions">
            <button type="button" id="refreshButton" class="btn btn-secondary">↻ Refresh</button>
            <button type="submit" class="btn">💾 Save Settings</button>
        </div>
    </form>

    <script nonce="${nonce}">
        const vscode = acquireVsCodeApi();

        // Toggle backend sections visibility
        function updateSectionVisibility() {
            const backend = document.getElementById('llmBackend').value;
            document.getElementById('ollamaSection').style.display =
                backend === 'ollama' ? 'block' : 'none';
            document.getElementById('openaiSection').style.display =
                backend === 'openai' ? 'block' : 'none';
        }

        document.getElementById('llmBackend').addEventListener('change', updateSectionVisibility);
        document.getElementById('etlProfile').addEventListener('change', (event) => {
            setProfile(event.target.value);
        });
        document.getElementById('testOllamaButton').addEventListener('click', testOllama);
        document.getElementById('toggleOpenaiApiKey').addEventListener('click', () => {
            togglePassword('openaiApiKey');
        });
        document.getElementById('refreshButton').addEventListener('click', refreshForm);
        updateSectionVisibility();

        // Form submission
        document.getElementById('settingsForm').addEventListener('submit', (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const settings = {};
            formData.forEach((value, key) => {
                settings[key] = value;
            });
            document.querySelectorAll('input[type="checkbox"][name]').forEach((input) => {
                settings[input.name] = input.checked ? 'true' : 'false';
            });
            vscode.postMessage({ command: 'save', settings });
        });

        // Test Ollama connection
        function testOllama() {
            const host = document.getElementById('ollamaHost').value;
            document.getElementById('ollamaStatus').className = 'status-badge status-unknown';
            document.getElementById('ollamaStatus').textContent = 'Testing...';
            vscode.postMessage({ command: 'testOllama', host });
        }

        // Set ETL Profile
        function setProfile(profileName) {
            vscode.postMessage({ command: 'setProfile', profile: profileName });
        }

        // Toggle password visibility
        function togglePassword(id) {
            const input = document.getElementById(id);
            input.type = input.type === 'password' ? 'text' : 'password';
        }

        // Refresh form
        function refreshForm() {
            vscode.postMessage({ command: 'refresh' });
        }

        // Handle messages from extension
        window.addEventListener('message', (event) => {
            const message = event.data;
            if (message.command === 'ollamaStatus') {
                const statusEl = document.getElementById('ollamaStatus');
                if (message.connected) {
                    statusEl.className = 'status-badge status-connected';
                    statusEl.textContent = '✓ Connected';
                } else {
                    statusEl.className = 'status-badge status-disconnected';
                    statusEl.textContent = '✗ Disconnected';
                }
            }
        });

        // Test connection on load
        setTimeout(() => testOllama(), 500);
    </script>
</body>
</html>`;
    }

    public dispose(): void {
        SettingsPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) {
            const x = this._disposables.pop();
            if (x) {
                x.dispose();
            }
        }
    }
}
