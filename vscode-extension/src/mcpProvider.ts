/**
 * MCP Server Definition Provider
 * 
 * Provides the Asset-Aware MCP server definition to VS Code.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

export class AssetAwareMcpProvider implements vscode.McpServerDefinitionProvider<vscode.McpStdioServerDefinition> {
    
    private _onDidChangeMcpServerDefinitions = new vscode.EventEmitter<void>();
    readonly onDidChangeMcpServerDefinitions = this._onDidChangeMcpServerDefinitions.event;
    
    private workspaceRoot: string;
    
    constructor(workspaceRoot: string) {
        this.workspaceRoot = workspaceRoot;
    }
    
    /**
     * Refresh MCP server definitions
     */
    refresh(): void {
        this._onDidChangeMcpServerDefinitions.fire();
    }
    
    /**
     * Provide MCP server definitions
     */
    provideMcpServerDefinitions(
        _token: vscode.CancellationToken
    ): vscode.ProviderResult<vscode.McpStdioServerDefinition[]> {
        const servers: vscode.McpStdioServerDefinition[] = [];
        
        // Find the MCP server directory
        const mcpServerDir = this.findMcpServerDir();
        
        if (mcpServerDir) {
            // Use path.join for cross-platform compatibility (Linux/Windows)
            const envPath = path.join(mcpServerDir, '.env');
            
            // Default environment variables (used when .env doesn't exist)
            const defaultEnv: Record<string, string> = {
                LLM_BACKEND: 'ollama',
                OLLAMA_HOST: 'http://localhost:11434',
                OLLAMA_MODEL: 'qwen2.5:7b',
                OLLAMA_EMBEDDING_MODEL: 'nomic-embed-text',
                ENABLE_LIGHTRAG: 'true',
                DATA_DIR: path.join(mcpServerDir, 'data')
            };
            
            // Merge default env with .env file if it exists
            const envVars = fs.existsSync(envPath) 
                ? { ...defaultEnv, ...this.parseEnvFile(envPath) }
                : defaultEnv;
            
            servers.push({
                label: 'Asset-Aware MCP',
                command: 'uv',
                args: [
                    'run',
                    '--directory', mcpServerDir,
                    'python', '-m', 'src.server'
                ],
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
        console.log(`Resolving MCP server: ${server.label}`);
        return server;
    }
    
    /**
     * Find MCP server directory
     */
    private findMcpServerDir(): string | undefined {
        // Look for the src directory with server.py
        const possiblePaths = [
            this.workspaceRoot,  // Root directory
            path.join(this.workspaceRoot, 'mcp-server'),
            path.dirname(this.workspaceRoot),  // Parent directory
        ];
        
        for (const basePath of possiblePaths) {
            const serverPath = path.join(basePath, 'src', 'server.py');
            if (fs.existsSync(serverPath)) {
                return basePath;
            }
        }
        
        // If running from vscode-extension subdirectory, check parent
        const parentServerPath = path.join(path.dirname(this.workspaceRoot), 'src', 'server.py');
        if (fs.existsSync(parentServerPath)) {
            return path.dirname(this.workspaceRoot);
        }
        
        console.warn('Could not find MCP server directory');
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
            console.error('Error parsing .env file:', error);
        }
        
        return env;
    }
}
