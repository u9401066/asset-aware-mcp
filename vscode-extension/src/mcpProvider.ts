/**
 * MCP Server Definition Provider
 *
 * Provides the Asset-Aware MCP server definition to VS Code.
 *
 * Two modes:
 * 1. Production Mode (default): Uses `uvx asset-aware-mcp` to run from PyPI
 * 2. Development Mode: Uses local source code if found in workspace
 */

import * as vscode from 'vscode';
import * as fs from 'fs';
import { buildAssetAwareLaunchSpec } from './mcpConfigCommon';
import {
    DEFAULT_TORCH_BACKEND,
    getUvPaths,
    PREFERRED_RUNTIME_PYTHON,
} from './uv';

export const LAST_SERVER_VERSION_KEY = 'lastServerVersion';

export class AssetAwareMcpProvider implements vscode.McpServerDefinitionProvider<vscode.McpStdioServerDefinition> {

    private _onDidChangeMcpServerDefinitions = new vscode.EventEmitter<void>();
    readonly onDidChangeMcpServerDefinitions = this._onDidChangeMcpServerDefinitions.event;

    private workspaceRoot: string;
    private outputChannel?: vscode.OutputChannel;
    private context?: vscode.ExtensionContext;
    private needsUpgrade: boolean;

    constructor(workspaceRoot: string, outputChannel?: vscode.OutputChannel, context?: vscode.ExtensionContext, needsUpgrade: boolean = false) {
        this.workspaceRoot = workspaceRoot;
        this.outputChannel = outputChannel;
        this.context = context;
        this.needsUpgrade = needsUpgrade;
    }

    private log(message: string): void {
        this.outputChannel?.appendLine('[MCP Provider] ' + message);
        console.log('[MCP Provider] ' + message);
    }

    /**
     * Get the uv/uvx command path
     */
    private getUvCommand(): string {
        // Try to get stored path from context
        const storedPath = this.context?.globalState.get<string>('uvPath');
        if (storedPath) {
            this.log('Using stored uv path: ' + storedPath);
            return storedPath;
        }

        // Fallback: try common paths
        const possiblePaths = getUvPaths().filter(candidate => candidate !== 'uv');

        for (const p of possiblePaths) {
            if (fs.existsSync(p)) {
                this.log('Found uv at: ' + p);
                return p;
            }
        }

        // Default to hoping it's in PATH
        this.log('Using uv from PATH');
        return 'uv';
    }

    /**
     * Refresh MCP server definitions
     */
    refresh(): void {
        this.log('Refreshing MCP server definitions...');
        this._onDidChangeMcpServerDefinitions.fire();
    }

    /**
     * Provide MCP server definitions
     */
    provideMcpServerDefinitions(
        _token: vscode.CancellationToken
    ): vscode.ProviderResult<vscode.McpStdioServerDefinition[]> {
        const launchContext = this.context ?? ({
            globalStorageUri: vscode.Uri.file(this.workspaceRoot),
            extension: { packageJSON: {} },
        } as vscode.ExtensionContext);
        const spec = buildAssetAwareLaunchSpec(
            launchContext,
            this.getUvCommand(),
            {
                workspaceRoot: this.workspaceRoot,
                needsUpgrade: this.needsUpgrade,
            },
        );
        const config = vscode.workspace.getConfiguration('assetAwareMcp');

        if (spec.mode === 'local') {
            this.log('Development Mode: Using local source launch spec');
        } else {
            this.log('Production Mode: Using uvx to run from PyPI');
        }
        this.log('Launch mode: ' + spec.mode);
        this.log('Command: ' + spec.command + ' ' + spec.args.join(' '));
        this.log('DATA_DIR: ' + spec.env['DATA_DIR']);
        this.log('Preferred Python runtime: ' + PREFERRED_RUNTIME_PYTHON);
        if (launchContext.extension?.packageJSON?.version) {
            this.log('Server version pin: ' + launchContext.extension.packageJSON.version);
        }
        if (this.needsUpgrade) {
            this.log('Upgrade flag: enabled (version changed)');
        }
        this.log('Marker backend enabled: ' + String(config.get('enableMarkerBackend', false)));
        if (config.get('enableMarkerBackend', false)) {
            this.log('Torch backend: ' + config.get('torchBackend', DEFAULT_TORCH_BACKEND));
            this.log('Marker output log: ' + spec.env['ASSET_AWARE_MARKER_OUTPUT_LOG']);
            this.log(
                'Marker cold start may download marker-pdf, torch, and model dependencies; ' +
                'run "Asset-Aware MCP: Prepare Server Runtime" before connecting Cline/Copilot/Codex.',
            );
        }

        return [
            {
                label: spec.mode === 'local' ? 'Asset-Aware MCP (Dev)' : 'Asset-Aware MCP',
                command: spec.command,
                args: spec.args,
                env: spec.env,
            },
        ];
    }

    /**
     * Resolve server definition before starting
     */
    resolveMcpServerDefinition(
        server: vscode.McpStdioServerDefinition,
        _token: vscode.CancellationToken
    ): vscode.ProviderResult<vscode.McpStdioServerDefinition> {
        this.log('Resolving MCP server: ' + server.label);
        return server;
    }

}
