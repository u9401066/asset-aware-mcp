# Asset-Aware MCP VS Code Extension

VS Code Extension for Medical RAG MCP Server with precise document asset retrieval.

## Features

- 🔌 **MCP Native**: Built with VS Code MCP API for seamless AI integration
- ⚙️ **Settings Panel**: Visual configuration with .env file management
- 📊 **Status View**: Real-time status of Ollama connection and documents
- 📁 **Document Browser**: View ingested documents and their assets

## Installation

1. Clone or download the extension
2. Install dependencies:
   ```bash
   cd vscode-extension
   npm install
   ```
3. Compile TypeScript:
   ```bash
   npm run compile
   ```
4. Press F5 in VS Code to launch Extension Development Host

## Usage

### Setup Wizard

Run `Asset-Aware MCP: Setup Wizard` command to:
- Create .env configuration
- Check Ollama connection
- Initialize MCP server

### Settings Panel

Run `Asset-Aware MCP: Open Settings Panel` to configure:
- LLM backend (Ollama/OpenAI)
- Ollama host and models
- OpenAI API key
- Storage directories

### Status View

The sidebar shows:
- Configuration status
- Ollama connection
- Ingested documents count

## Extension Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `assetAwareMcp.llmBackend` | `ollama` | LLM backend (ollama/openai) |
| `assetAwareMcp.ollamaHost` | `http://localhost:11434` | Ollama server URL |
| `assetAwareMcp.ollamaModel` | `qwen2.5:7b` | Ollama LLM model |
| `assetAwareMcp.ollamaEmbeddingModel` | `nomic-embed-text` | Embedding model |
| `assetAwareMcp.dataDir` | `./data` | Document storage directory |

## Commands

| Command | Description |
|---------|-------------|
| `Asset-Aware MCP: Setup Wizard` | Run initial setup |
| `Asset-Aware MCP: Open Settings Panel` | Configure settings |
| `Asset-Aware MCP: Show Status` | View detailed status |
| `Asset-Aware MCP: Check Ollama Connection` | Test Ollama |
| `Asset-Aware MCP: Edit .env Configuration` | Open .env file |
| `Asset-Aware MCP: Refresh Status` | Refresh status view |

## Development

```bash
# Install dependencies
npm install

# Compile
npm run compile

# Watch mode
npm run watch

# Package
npm run package
```

## License

Apache-2.0
