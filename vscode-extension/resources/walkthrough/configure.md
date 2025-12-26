# Configure Settings

The Settings Panel lets you configure your LLM backend and storage options.

## LLM Backend Options

### 🦙 Ollama (Local)

Run LLMs locally on your machine:

- **Ollama Host**: Usually `http://localhost:11434`
- **LLM Model**: `qwen2.5:7b` (recommended)
- **Embedding Model**: `nomic-embed-text`

**Recommended Ollama Models:**
- `qwen2.5:7b` - Good balance of speed and quality
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

## Tips

💡 Use the "Test Connection" button to verify Ollama is running

💡 Settings are saved to `.env` file in your workspace

💡 Changes take effect after restarting the MCP server
