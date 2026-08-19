<!-- Generated from LLM-Wiki-Knowledge-Base.md by scripts/build_docs_site.py -->

# LLM Wiki Knowledge Base

LLM wiki 把 verified evidence、table/figure asset notes、KG discovery candidates
和人工 topic note 放進同一個 Foam-compatible Markdown workspace。KG 是 discovery
layer；LLM wiki 是 presentation/synthesis layer；citation bundle 才是 evidence
layer。

## When To Use

| 需求 | 入口 |
|---|---|
| 把單一已 ingest 文件匯出為可重用 agent asset + Foam 子樹 | `document(op="export_assets")` |
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

例外是 `document(op="export_assets")`：它不是直接改寫上述人工維護的 wiki root，
而是在該文件的資料目錄內建立一個自包含、可攜式 Foam 子樹。這個限制是刻意的，
可避免 MCP 參數把產物寫到任意外部路徑。

## Reusable Agent Asset Bundle

先完成 PDF ingest 並取得 `doc_id`，再匯出 bundle：

```text
document(
  op="export_assets",
  doc_id="doc_abc",
  output_dir="agent-assets"
)
```

`output_dir` 是相對於該文件資料目錄的路徑；省略時也是 `agent-assets`。成功結果會
回傳 `manifest_path`、`assets_path`、`foam_index_path`，以及明示
`index.md + notes/**` 為 portable Foam subtree 的 `foam_subtree` 描述。

```text
<document-data>/<doc_id>/agent-assets/
  manifest.json        # bundle/source identity、counts、artifact hashes
  assets.jsonl         # 一行一個 text/table/figure agent asset
  index.md             # Foam hub；連到每一個實際存在的 note anchor
  notes/
    <stable-note>.md   # YAML、單一 H1、內容、citation provenance
  media/
    <stable-media>     # 可用的 figure 複本；notes 使用相對連結
```

每筆 `assets.jsonl` record 的核心契約如下：

- `asset_key` 是 `<asset_type>:<asset_id>`；`asset_id` 沿用來源 manifest 或
  segmentation 的穩定識別。
- `source_identity` 使用格式中立的 `source_sha256`、`source_kind`、
  `source_media_type`，並保留 `doc_id`、來源檔名、引擎與 canonical Markdown /
  locator hashes。
- `locator` 可包含 page、bbox、line/char/byte ranges、section hierarchy、
  reading order、`source_revision_id`、`locator_version` 與
  `locator_source_sha256`；缺失值不會被捏造成精確定位。
- `citation` 保留可用的 primary AssetRef 與 EvidenceSpan refs，狀態會區分
  `citation_ready`、`asset_locator_only`、`unavailable`。
- 每筆 record 的 `content_sha256`、`record_sha256` 可驗證內容與完整 record；
  manifest 層的 `bundle_sha256` 與 artifact inventory hashes 可驗證整包產物。
- `foam.path`、`foam.anchor`、`foam.wikilink` 都由穩定 identity 推導；hub 只連到
  本次實際建立的 notes。

相同來源 revision、manifest、citation index 與媒體輸入會得到固定排序及
byte-stable JSON/Markdown/hash 產物；bundle 內容不嵌入匯出目錄的絕對路徑或執行
時間。搬移時應整包保留 `index.md`、`notes/**`、`media/**`、JSONL 與 manifest，
以維持 wikilink、圖片相對連結與完整性驗證。

### Safe Output Policy

- 輸出必須是文件資料目錄的嚴格子目錄；`..`、外部絕對路徑與文件根目錄會被拒絕。
- 不覆寫來源 PDF、canonical Markdown、manifest、citation index 或原始圖片。
- 既有目標只有在 `manifest.json` 證明它是同一 `doc_id`、同一 bundle schema 的
  bundle 時才可更新；任意目錄、來源 `images/` 或不相符 bundle 都會 fail closed。
- 先在同一文件目錄建立 staging bundle，再以 rename-based replacement 發布；
  失敗時清理 staging，替換失敗時會嘗試還原原本的 bundle。
- Figure 只會從該文件資料目錄內的既有、允許圖片格式複製；不跟隨路徑逃逸去讀取
  或發布外部檔案。複製與 SHA-256 使用同一個來源串流，來源在匯出途中改變時整次
  匯出會失敗，不會發布 hash 與 media bytes 不一致的 record。
- Evidence join 先建立 block/asset index，不會對每筆 record 重掃全部 spans。預設
  hard limits 為 50,000 evidence spans、25,000 records 與 256 MiB staged output；
  任一上限超出時回傳 bounded failure 並清理 staging。這些上限是資源安全契約，
  不是靜默截斷。

### Current Scope

這個垂直切片目前接在 PDF ingest 使用的 `DocumentRepository`、PDF manifest、
segmentation 與 citation index 上，已涵蓋可用的 text segments、tables、figures。
格式中立的 source 欄位是未來擴充契約，不代表 DOCX/DFM 或任意格式已自動接入。
DOCX/general document 要使用同一 bundle schema，仍需各自 adapter 將來源 identity、
segments、assets 與 locators 正規化後再交給 exporter。

這個 bundle 也不是完整的專案 wiki 管理器：它不選 citation key、不建立跨文件 topic
map、不合併既有人工 notes，也不取代任何下游產品的 dashboards、graph curation 或
publish 流程。它提供的是可驗證、可搬移、可被上述流程重用的單文件基礎資產。

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
