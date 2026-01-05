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
import * as path from 'path';
import * as fs from 'fs';

export class AssetAwareMcpProvider implements vscode.McpServerDefinitionProvider<vscode.McpStdioServerDefinition> {
    
    private _onDidChangeMcpServerDefinitions = new vscode.EventEmitter<void>();
    readonly onDidChangeMcpServerDefinitions = this._onDidChangeMcpServerDefinitions.event;
    
    private workspaceRoot: string;
    private outputChannel?: vscode.OutputChannel;
    
    constructor(workspaceRoot: string, outputChannel?: vscode.OutputChannel) {
        this.workspaceRoot = workspaceRoot;
        this.outputChannel = outputChannel;
    }
    
    private log(message: string): void {
        this.outputChannel?.appendLine('[MCP Provider] ' + message);
        console.log('[MCP Provider] ' + message);
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
        const servers: vscode.McpStdioServerDefinition[] = [];
        
        // Check for local development mode first
        const mcpServerDir = this.findMcpServerDir();
        
        // Get configuration from VS Code settings
        const config = vscode.workspace.getConfiguration('assetAwareMcp');
        
        // Build environment variables from settings
        const envVars: Record<string, string> = {
            LLM_BACKEND: config.get('llmBackend', 'ollama'),
            OLLAMA_HOST: config.get('ollamaHost', 'http://localhost:11434'),
            OLLAMA_MODEL: config.get('ollamaModel', 'qwen2.5:7b'),
            OLLAMA_EMBEDDING_MODEL: config.get('ollamaEmbeddingModel', 'nomic-embed-text'),
            ENABLE_LIGHTRAG: 'true',
        };
        
        // Add OpenAI settings if configured
        const openaiKey = config.get<string>('openaiApiKey', '');
        if (openaiKey) {
            envVars['OPENAI_API_KEY'] = openaiKey;
            envVars['OPENAI_MODEL'] = config.get('openaiModel', 'gpt-4o-mini');
        }
        
        if (mcpServerDir) {
            // Development Mode: Local source found
            this.log('Development Mode: Using local source at ' + mcpServerDir);
            
            const envPath = path.join(mcpServerDir, '.env');
            
            // Set DATA_DIR relative to project
            envVars['DATA_DIR'] = path.join(mcpServerDir, 'data');
            
            // Merge with .env file if exists
            if (fs.existsSync(envPath)) {
                const fileEnv = this.parseEnvFile(envPath);
                Object.assign(envVars, fileEnv);
                this.log('Merged .env file settings');
            }
            
            this.log('Command: uv run --directory ' + mcpServerDir + ' python -m src.server');
            
            servers.push({
                label: 'Asset-Aware MCP (Dev)',
                command: 'uv',
                args: [
                    'run',
                    '--directory', mcpServerDir,
                    'python', '-m', 'src.server'
                ],
                env: envVars
            });
        } else {
            // Production Mode: Use uvx to run from PyPI
            this.log('Production Mode: Using uvx to run from PyPI');
            
            // Set DATA_DIR to workspace or user's home
            const dataDir = config.get<string>('dataDir', './data');
            if (path.isAbsolute(dataDir)) {
                envVars['DATA_DIR'] = dataDir;
            } else {
                envVars['DATA_DIR'] = path.join(this.workspaceRoot, dataDir);
            }
            
            this.log('Command: uvx asset-aware-mcp');
            this.log('DATA_DIR: ' + envVars['DATA_DIR']);
            
            servers.push({
                label: 'Asset-Aware MCP',
                command: 'uvx',
                args: ['asset-aware-mcp'],
                env: envVars
            });
        }
        
        return servers;
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
    
    /**
     * Find MCP server directory (for development mode)
     * Returns undefined if not found (triggers production mode)
     */
    private findMcpServerDir(): string | undefined {
        // Look for the src directory with server.py
        const possiblePaths = [
            this.workspaceRoot,  // Root directory
            path.join(this.workspaceRoot, 'mcp-server'),
            path.join(this.workspaceRoot, 'asset-aware-mcp'),
            path.dirname(this.workspaceRoot),  // Parent directory (for vscode-extension subfolder)
        ];
        
        this.log('Checking for local development source...');
        
        for (const basePath of possiblePaths) {
            const serverPath = path.join(basePath, 'src', 'server.py');
            const pyprojectPath = path.join(basePath, 'pyproject.toml');
            
            // Must have both server.py and pyproject.toml with asset-aware-mcp
            if (fs.existsSync(serverPath) && fs.existsSync(pyprojectPath)) {
                try {
                    const pyproject = fs.readFileSync(pyprojectPath, 'utf-8');
                    if (pyproject.includes('name = "asset-aware-mcp"')) {
                        this.log('  Found local source at: ' + basePath);
                        return basePath;
                    }
                } catch {
                    // Ignore read errors
                }
            }
        }
        
        this.log('  No local source found, will use PyPI package');
        return undefined;
    }
    
    /**
     * Parse .env file to object
     */
    private parseEnvFile(envPath: string): Record<string, string> {
        const env: Record<string, string> = {};
        
        try {
            const content = fs.readFileSync(envPath, 'utf-8');
            const lines = content.split('\n');
            
            for (const line of lines) {
                const trimmed = line.trim();
                if (trimmed && !trimmed.startsWith('#')) {
                    const eqIndex = trimmed.indexOf('=');
                    if (eqIndex > 0) {
                        const key = trimmed.substring(0, eqIndex).trim();
                        let value = trimmed.substring(eqIndex + 1).trim();
                        
                        // Remove quotes if present
                        if ((value.startsWith('"') && value.endsWith('"')) ||
                            (value.startsWith("'") && value.endsWith("'"))) {
                            value = value.slice(1, -1);
                        }
                        
                        env[key] = value;
                    }
                }
            }
        } catch (error) {
            this.log('Error parsing .env file: ' + String(error));
        }
        
        return env;
    }
}
