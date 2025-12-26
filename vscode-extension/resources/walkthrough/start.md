# Start Using Asset-Aware MCP

Congratulations! 🎉 You're ready to use Asset-Aware MCP with GitHub Copilot.

## Available MCP Tools

### 📥 `ingest_documents`
Process PDF files and create Document Manifests.

**Example prompts:**
- "Ingest the PDF at /path/to/paper.pdf"
- "Process this medical document"

### 📋 `list_documents`
See all processed documents.

**Example prompts:**
- "List all documents"
- "What papers have I ingested?"

### 🔍 `inspect_document_manifest`
Get details about a specific document.

**Example prompts:**
- "Show manifest for doc_xyz"
- "What tables are in this document?"

### 📊 `fetch_document_asset`
Retrieve tables, figures, or sections.

**Example prompts:**
- "Get Table 1 from the document"
- "Show me Figure 2"
- "Extract the Methods section"

### 🧠 `consult_knowledge_graph`
Query across all indexed documents.

**Example prompts:**
- "What are the dosing recommendations for remimazolam?"
- "Compare sedation outcomes between propofol and remimazolam"

## Workflow Example

1. **Ingest a paper:**
   > "Ingest the PDF at ~/Downloads/medical_paper.pdf"

2. **Check what's available:**
   > "What tables and figures are in this paper?"

3. **Extract specific content:**
   > "Show me Table 2 with the patient demographics"

4. **Query knowledge:**
   > "Based on the paper, what are the main findings?"

## Tips

💡 Use natural language - the AI understands context

💡 Reference figures by number ("Figure 1") or description

💡 The knowledge graph learns from all ingested documents
