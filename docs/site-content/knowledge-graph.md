<!-- Generated from Knowledge-Graph.md by scripts/build_docs_site.py -->

# Knowledge Graph

Knowledge graph 是 opt-in discovery layer。它可以幫 agent 找跨文件主題、關係與候選
引用，但 citation-ready 結論仍要回到 `evidence(...)` 或 `citation_bundle(...)`
驗證 locator、hash 與 context。

## Enable

```bash
ENABLE_LIGHTRAG=true uv run asset-aware-mcp
```

PDF ingest 預設不會寫入 KG。需要建立 index 時明確傳入：

```text
ingest_documents(
  file_paths=["/path/paper.pdf"],
  index_knowledge_graph=true
)
```

## Check Graph State

先確認 graph 有內容，再查詢：

```text
knowledge(op="export", format="summary", limit=20)
```

## Query

```text
knowledge(
  op="consult",
  query="remimazolam dosing in ICU sedation",
  response_mode="structured",
  verify_references=true,
  doc_ids=["doc_..."]
)
```

常見用法：

| 需求 | 入口 |
|---|---|
| Agent 需要可解析結果 | `knowledge(op="consult", response_mode="structured")` |
| 只要 retrieval data | `knowledge(op="consult", response_mode="data")` |
| 人類閱讀摘要 | `knowledge(op="consult", response_mode="text")` |
| 匯出 graph | `knowledge(op="export", format="json")` |

## Evidence Boundary

- KG answer 不是最終引用來源。
- `verify_references=true` 可以附上 verified evidence，但高風險 claim 仍應用
  `citation_bundle(output_format="json")` 或 `evidence(op="verify")` 再查一次。
- `knowledge(op="consult")` / `knowledge(op="export")` 有 MCP request guard；
  Ollama LLM/embedding 呼叫本身仍使用 runtime timeout knobs。
