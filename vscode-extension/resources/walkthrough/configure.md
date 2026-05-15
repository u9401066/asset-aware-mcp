# Configure Settings

The Settings Panel lets you configure your LLM backend and storage options.

## LLM Backend Options

### 🦙 Ollama (Local)

Run LLMs locally on your machine:

- **Ollama Host**: Usually `http://localhost:11434`
- **LLM Model**: `granite4.1:3b` (CPU default); GPU installs can use `granite4.1:8b`
- **Embedding Model**: `nomic-embed-text` (only required when LightRAG/KG is enabled)

**Recommended Ollama Models:**
- `granite4.1:3b` - Default enterprise-ready local RAG/text-generation model for CPU installs
- `granite4.1:8b` - Recommended Granite default for GPU installs
- `llama3.2` - Meta's latest model
- `mistral` - Fast and efficient

### ☁️ OpenAI (Cloud)

Use OpenAI's cloud API:

- Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)
- **Model**: `gpt-4o-mini` (fast and affordable)
- **Embedding**: `text-embedding-3-small`

## Storage Settings

- **Data Directory**: Where processed documents are stored
- **LightRAG Directory**: Knowledge graph storage
- **LightRAG/KG**: Optional and disabled by default for CPU-only or document-only workflows

## Tips

💡 Use the "Test Connection" button to verify Ollama is running

💡 Settings are saved to `.env` file in your workspace

💡 Changes take effect after restarting the MCP server
