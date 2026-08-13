<!-- Generated from MCP-Resources.md by scripts/build_docs_site.py -->

# MCP Resources

資源數量由 `./scripts/count_tools.sh` 產生：13 resources in 2 modules。來源為 `src/presentation/resources/**`。

## `document_resources.py` - 8 resources

| Resource | URI | 功能 |
|---|---|---|
| `resource_document_list` | `documents://list` | 列出已處理文件 |
| `resource_document_manifest` | `document://{doc_id}/manifest` | 讀取 document manifest |
| `resource_document_segmentation` | `document://{doc_id}/segmentation` | 讀取 unified segmentation schema |
| `resource_document_figures` | `document://{doc_id}/figures` | 列出 figures |
| `resource_document_tables` | `document://{doc_id}/tables` | 列出 tables |
| `resource_document_sections` | `document://{doc_id}/sections` | 列出 sections |
| `resource_document_outline` | `document://{doc_id}/outline` | 文件 outline |
| `resource_knowledge_graph_summary` | `knowledge-graph://summary` | Knowledge graph summary |

## `table_resources.py` - 5 resources

| Resource | URI | 功能 |
|---|---|---|
| `resource_table_list` | `tables://list` | 列出 A2T tables |
| `resource_table_content` | `table://{table_id}/content` | 讀取 table markdown |
| `resource_table_status` | `table://{table_id}/status` | compact table status |
| `resource_draft_list` | `drafts://list` | 列出 drafts |
| `resource_draft_content` | `draft://{draft_id}/content` | 讀取 draft content |

## 使用方式

Resources 是 read-oriented MCP surface，適合 LLM 直接讀取現有 artifacts；Tools 是 operation-oriented surface，適合觸發 ingest、conversion、查詢或 mutation。`document://{doc_id}/segmentation` 在目前版本是 read-only，不會因讀取而重新寫入 `segmentation.json`。
