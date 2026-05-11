# Knowledge Graph

![Knowledge graph workflow](assets/knowledge-graph-workflow.jpg)

## 角色

Knowledge graph 由 LightRAG 提供，用於跨文件查詢、關聯摘要與圖譜匯出。它不是 citation locator 的唯一來源；citation-ready locator 仍以 document artifacts、segmentation 與 citation index 為準。

來源：`src/application/knowledge_service.py`、`src/infrastructure/lightrag_adapter.py`、`src/presentation/tools/knowledge_tools.py`。

## 查詢

```text
consult_knowledge_graph(
  query="...",
  mode="hybrid",
  response_mode="Multiple Paragraphs",
  include_references=true
)
```

`knowledge(op="consult", ...)` 是 consolidated entrypoint。

## 匯出

```text
export_knowledge_graph(format="json", limit=100)
```

可用於視覺化、外部分析或 wiki synthesis。

## 後端與安全行為

目前 LightRAG adapter 會：

- 驗證 `lightrag-hku` distribution。
- 支援 Ollama embeddings batch `/api/embed`，並提供 legacy fallback。
- 暴露 LLM/embedding timeout knobs。
- 在 LightRAG/Ollama 不可用時回傳 bounded diagnostic，而不是無限等待。

## 和 Citation 的關係

KG 適合回答「跨文件有哪些關係」。若要產出可引用結論，流程應回到：

```text
KG query -> source candidates -> find_evidence_spans -> verify_citation_ref
```

也就是說，KG 是 discovery layer；citation index 是 evidence layer。
