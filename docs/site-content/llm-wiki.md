<!-- Generated from LLM-Wiki-Knowledge-Base.md by scripts/build_docs_site.py -->

# LLM Wiki Knowledge Base

LLM wiki 是把文件 evidence、table/figure asset、KG discovery candidate 與人工整理的
topic note 放進同一個 Foam-compatible Markdown 知識庫。它的目標不是取代 citation
index，而是讓人類和 LLM 都能用 wiki link 讀、找、引用、回查來源。

## 何時使用

| 情境 | 建議流程 |
|---|---|
| 想把一篇 PDF 變成可審查的 evidence note | `citation_bundle(output_format="foam")` |
| 想把 table/figure 變成獨立知識卡 | `document_asset(op="foam_notes")` |
| 想從 KG 找跨文件主題 | `consult_knowledge_graph(..., verify_references=true)` 後再回到 evidence bundle |
| 想檢查 wiki 引用是否還能回到原始文件 | `evidence(op="health")` |

KG 是 discovery layer；LLM wiki 是 presentation/synthesis layer；citation bundle 和
AssetRef 才是可驗證 evidence layer。

## Wiki Root

先選一個 wiki root。若專案已經有 Foam workspace，使用既有 `.foam/` 或 notes 目錄；若
只是做小型實驗，可以用：

```text
wiki/
  index.md
  evidence/
  assets/
  claims/
```

寫檔工具都會限制輸出不能逃出 `wiki_root`。若檔案已存在，預設不覆蓋；需要覆蓋時明確傳
`overwrite=true`。

## 最小實例：PDF 到 Evidence Pack

先攝入 PDF，取得 `doc_id`：

```text
ingest_documents(file_paths=["/papers/trial.pdf"], async_mode=true)
get_job_status(job_id="...")
```

找到可引用 span，先用 JSON 看內容：

```text
evidence(
  op="bundle",
  doc_id="doc_abc",
  query="primary outcome",
  output_format="json"
)
```

確認後寫成 Foam evidence note：

```text
citation_bundle(
  doc_id="doc_abc",
  query="primary outcome",
  output_format="foam",
  citation_key="trial-2026-primary-outcome",
  wiki_root="/path/to/wiki",
  output_path="evidence/trial-2026-primary-outcome.md",
  update_index=true
)
```

產物會是普通 Markdown，含 YAML frontmatter、Foam block anchor、source locator、
AssetRef JSON 與 verification status/issues。這讓 topic note 可以連到 evidence note，而不是
把來源資訊藏在聊天紀錄裡。

## 最小實例：Table/Figure Notes

若 manifest 裡有 table/figure asset，可以把它們寫成獨立 note：

```text
document_asset(
  op="foam_notes",
  doc_id="doc_abc",
  asset_type="all",
  asset_id="all",
  wiki_root="/path/to/wiki",
  output_dir="assets",
  citation_key="trial-2026"
)
```

這會輸出 `type: table_evidence` 或 `type: figure_evidence` note，保留 `asset_id`、
page、line range、source block、section context、source PDF hash 與 locator hash。

## Topic Note 範例

Topic note 是人類整理層，可以引用 evidence note 的 block anchor。範例：

```md
---
type: topic
status: draft
sources:
  - "[[evidence/trial-2026-primary-outcome]]"
---

# Primary Outcome

- The intervention improved the primary outcome in the analyzed cohort.
  Evidence: ![[evidence/trial-2026-primary-outcome#^spn-actual-returned-span-id]]

## Open Questions

- TODO: compare subgroup outcomes after another verified bundle is available.
```

規則：

- 一個 note 只放一個 `# H1`。
- 新檔名用 stable lowercase kebab-case。
- `[[wikilink]]` 只連到已存在或本次會建立的 note。
- Evidence anchor 不要手寫；從 `citation_bundle(...)` 回傳的 `embed` 或 `wikilink` 複製。
- 具體 claim 附近要有 evidence link 或 source marker，不只放在 bibliography。

## KG 與 LLM Wiki 如何分工

KG 可以先找主題和關係：

```text
ingest_documents(
  file_paths=["/papers/trial.pdf"],
  async_mode=true,
  index_knowledge_graph=true
)
get_job_status(job_id="...")
export_knowledge_graph(format="summary", limit=20)
```

確認 graph 有內容後再查：

```text
consult_knowledge_graph(
  query="Which documents mention primary outcome and adverse events?",
  response_mode="structured",
  include_references=true,
  verify_references=true,
  doc_ids=["doc_abc"],
  evidence_limit=5
)
```

若 response 帶 `verified_evidence`，可以直接把 evidence links 放進 topic note；若 KG 只回
candidate，請回到：

```text
KG candidate -> evidence(op="bundle") -> verify -> Foam note
```

不要把 KG answer 本身當成最終引用來源。

## Health Check

更新文件、搬動 note 或重建 citation index 後，掃 wiki：

```text
evidence(
  op="health",
  wiki_root="/path/to/wiki",
  output_format="json"
)
```

Health check 會檢查 Foam evidence note 裡的 embedded AssetRef JSON、span/table/figure
locator、asset note 與 `[[note#^anchor]]` link 是否還能回到原始文件。
若出現 drift，先回原始文件重建 bundle，再更新 topic note。
