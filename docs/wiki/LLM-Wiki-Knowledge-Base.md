# LLM Wiki Knowledge Base

LLM wiki 把 verified evidence、table/figure asset notes、KG discovery candidates
和人工 topic note 放進同一個 Foam-compatible Markdown workspace。KG 是 discovery
layer；LLM wiki 是 presentation/synthesis layer；citation bundle 才是 evidence
layer。

## When To Use

| 需求 | 入口 |
|---|---|
| 從單一 PDF 產 evidence note | `citation_bundle(output_format="foam")` |
| 產 table/figure asset note | `document_asset(op="foam_notes")` |
| 從 KG 找跨文件主題 | `knowledge(op="consult", verify_references=true)` 後再回到 evidence bundle |
| 檢查 wiki 引用是否 drift | `evidence(op="health")` |

## Wiki Root

```text
wiki/
  index.md
  evidence/
  assets/
  claims/
```

所有會寫入 wiki 的工具都需要 `wiki_root`。預設不覆蓋既有 note；需要重建時再傳
`overwrite=true`。

## Evidence Pack

```text
ingest_documents(file_paths=["/papers/trial.pdf"], async_mode=true)
get_job_status(job_id="...")
citation_bundle(
  doc_id="doc_abc",
  query="primary outcome",
  output_format="foam",
  citation_key="trial-2026-primary-outcome",
  wiki_root="/path/to/wiki"
)
```

產物可以在 topic note 中用 Foam link 引用：

```text
[[evidence/trial-2026-primary-outcome]]
![[evidence/trial-2026-primary-outcome#^assetref-primary-outcome]]
```

## Asset Notes

```text
document_asset(
  op="foam_notes",
  doc_id="doc_abc",
  asset_type="table",
  asset_id="table_1",
  wiki_root="/path/to/wiki",
  citation_key="trial-2026"
)
```

## KG Candidates

```text
knowledge(
  op="consult",
  query="remimazolam dosing in ICU sedation",
  response_mode="structured",
  include_references=true,
  verify_references=true,
  doc_ids=["doc_abc"],
  evidence_limit=5
)
```

將 KG candidate 提升為 wiki note 前，回到 evidence layer：

```text
KG candidate -> evidence(op="bundle") -> evidence(op="verify") -> Foam note
```

## Health Check

```text
evidence(
  op="health",
  wiki_root="/path/to/wiki",
  output_format="json"
)
```

Health check 會回查 embedded AssetRef JSON、span/table/figure locator、asset note
和 `[[note#^anchor]]` link 是否 drift。若 drift，重新匯出 bundle，再更新 topic note。
