# Configure Settings

The Settings Panel lets you configure your LLM backend and storage options.

## LLM Backend Options

### 🦙 Ollama (Local)

Run LLMs locally on your machine:

- **Ollama Host**: Usually `http://localhost:11434`
- **LLM Model**: `granite4.1:3b` (CPU default); GPU installs can use `granite4.1:8b`
- **Embedding Model**: `nomic-embed-text` (only required when LightRAG/KG is enabled)
- The Settings Panel includes CPU/GPU preset choices and keeps a custom model field for other installed Ollama models.

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

### OpenRouter (Fast/free preset)

Use OpenRouter's OpenAI-compatible API for low-cost summaries and draft RAG answers:

- **API Key**: stored locally as `OPENROUTER_API_KEY`
- **Base URL**: `https://openrouter.ai/api/v1`
- **Preset model**: `liquid/lfm-2.5-1.2b-instruct:free`
- LightRAG retrieval still uses the configured embedding backend, such as `OLLAMA_EMBEDDING_MODEL=nomic-embed-text`.

## Storage Settings

- **Data Directory**: Where processed documents are stored
- **LightRAG Directory**: Knowledge graph storage
- **LightRAG/KG**: Optional and disabled by default for CPU-only or document-only workflows

## Tips

💡 Use the "Test Connection" button to verify Ollama is running

💡 Settings are saved to `.env` file in your workspace

💡 Changes take effect after restarting the MCP server
