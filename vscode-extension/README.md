# Asset-Aware MCP

> 🏥 Medical RAG MCP Server - Precise PDF asset retrieval for AI Agents

[![VS Code Marketplace](https://img.shields.io/visual-studio-marketplace/v/u9401066.asset-aware-mcp)](https://marketplace.visualstudio.com/items?itemName=u9401066.asset-aware-mcp)
[![PyPI](https://img.shields.io/pypi/v/asset-aware-mcp)](https://pypi.org/project/asset-aware-mcp/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

## 🌟 Features

- **📄 Precise Asset Retrieval**: Extract tables, figures, and sections from PDFs with page-level accuracy
- **🧠 Knowledge Graph**: Cross-document queries powered by LightRAG
- **🤖 MCP Native**: Seamless integration with VS Code Copilot Chat
- **🏠 Local-First**: Works with Ollama (no cloud required) or OpenAI

## 🚀 Quick Start

### 1. Install Prerequisites

```bash
# Install Ollama (for local LLM)
curl -fsSL https://ollama.com/install.sh | sh

# Pull required models
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

### 2. Install Extension

1. Open VS Code
2. Go to Extensions (Ctrl+Shift+X)
3. Search for "Asset-Aware MCP"
4. Click Install

### 3. Run Setup Wizard

1. Open Command Palette (Ctrl+Shift+P)
2. Run `Asset-Aware MCP: Setup Wizard`
3. Follow the prompts

## 📖 Usage

### Ingest Documents

In Copilot Chat, use the MCP tool:

```
@workspace Use ingest_documents to process /path/to/paper.pdf
```

### Query Documents

```
@workspace What are the main findings in Table 1?
@workspace Fetch figure 2 from doc_abc123
@workspace Compare sedation outcomes across all papers
```

## ⚙️ Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `assetAwareMcp.llmBackend` | `ollama` | LLM backend |
| `assetAwareMcp.ollamaHost` | `http://localhost:11434` | Ollama URL |
| `assetAwareMcp.ollamaModel` | `qwen2.5:7b` | LLM model |
| `assetAwareMcp.dataDir` | `./data` | Storage directory |

## 🔧 Commands

| Command | Description |
|---------|-------------|
| `Setup Wizard` | Initial configuration |
| `Open Settings Panel` | Visual settings editor |
| `Check Ollama Connection` | Test Ollama status |
| `Refresh Status` | Update status view |

## 📚 MCP Tools

| Tool | Description |
|------|-------------|
| `ingest_documents` | Process PDF files |
| `list_documents` | List all documents |
| `inspect_document_manifest` | View document structure |
| `fetch_document_asset` | Get table/figure/section |
| `consult_knowledge_graph` | Cross-document queries |

## 🔗 Links

- [GitHub Repository](https://github.com/u9401066/asset-aware-mcp)
- [PyPI Package](https://pypi.org/project/asset-aware-mcp/)
- [Documentation](https://github.com/u9401066/asset-aware-mcp#readme)
- [Issues](https://github.com/u9401066/asset-aware-mcp/issues)

## 📝 License

Apache-2.0
