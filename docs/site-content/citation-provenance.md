<!-- Generated from Citation-Provenance.md by scripts/build_docs_site.py -->

# Citation Provenance

## 目標

Citation-ready 在此專案中表示：每個引用都能追溯到具體文件、block/span、locator、hash 與周邊 context。不能只保存一段文字，因為文件轉換、OCR、DFM 編輯或 table persistence 都可能讓 locator 漂移。

來源：`src/domain/citation.py`、`src/application/citation_artifacts.py`、`src/application/citation_index_service.py`、`src/presentation/tools/citation_support.py`、`src/presentation/tools/document_tools.py`、`src/domain/table_entities.py`。

## EvidenceSpan

EvidenceSpan 是引用候選片段，通常由 PDF ingest、segmentation 或 citation index rebuild 產生。它保存：

- document id
- span id
- block id
- page
- line range
- char/byte range
- bbox
- section
- quote/text hash
- locator version
- source revision
- locator source hash

## AssetRef

AssetRef 是工具間傳遞引用的 compact object。`verify_citation_ref(ref)` 目前驗證的是 span-level AssetRef，會檢查 ref 是否仍符合現有 citation index，包含：

- block identity 是否存在。
- page/line/char/byte/bbox locator 是否一致。
- ref 有提供 `locator_source_sha256` 時，檢查 locator source hash 是否一致。
- quote/text hash 是否匹配。
- source revision 是否 stale。

`0.6.27` 已修正 AssetRef serialization/reload 會掉 `locator_source_sha256` 的問題。`0.6.28` 進一步加入 `citation_bundle(...)`，可一次匯出多個 verified EvidenceSpan，包含 AssetRef、quote/hash、locator、context、CRAAP scaffold 與 verification 結果。`0.6.29` 把 Foam 工作流補成閉環：可安全寫入 evidence pack、更新 index note、掃 wiki health、產生 table/figure evidence notes，並用 claim promotion workflow 在寫入前強制 verify。

若要交給 Foam/LLM wiki，使用 `citation_bundle(output_format="foam", citation_key="...")` 可直接取得含 YAML frontmatter、`^spn-...` block anchor、wikilink/embed 與 AssetRef JSON 的 evidence pack。

## Citation Index

`CitationIndexService` 負責建立或重建 `citation_index.jsonl`，並用 `citation_index.status.json` 記錄 build/rebuild 狀態。當 canonical Markdown revision hash 或 locator version 改變時，cache 會被視為 stale 並重建。

## Table Citation

A2T table cell 可掛 citation refs。當 cited cell 或 row 被更新時，舊 citation 會被移除或標示 stale，避免把修改後的數值繼續指向舊來源。

相關工具：

- `table_cite`
- `find_evidence_spans`
- `verify_citation_ref`
- `citation_bundle`
- `evidence(op="find" | "verify" | "bundle" | "locate")`

實務上可先用 `find_evidence_spans` 尋找候選。短 quote 會 inline 完整、可交給
`verify_citation_ref` 的 canonical AssetRef；超過 1,000 字元的 span 為了守住 MCP
response cap，只回 `asset-ref-preview-v1`（`canonical_asset_ref=false`），沒有 canonical
locator／range，也不能拿去 verify。長 span 的完整 exact quote、hash 與 locator 只保存於
寫入磁碟的 citation／agent-asset bundle。若要給人類文件、KG answer 或外部審查使用，
建議用 `citation_bundle(output_format="json")` 或 `evidence(op="bundle")` 取得有界回應，
需要完整引用則指定 `wiki_root`／`output_path` 寫入 persisted bundle 後再驗證其中 AssetRef。
若要 promotion 到 Foam note，使用 `citation_bundle(output_format="foam", citation_key="paper-key")`
或 `evidence(op="bundle", output_format="foam", citation_key="paper-key")`。`discover_sources`
適合先找表格可抽取來源，但它的 span ref 較偏 discovery payload，正式引用仍應回到
persisted bundle 與 `verify_citation_ref`。

## Foam Evidence Pack

`output_format="foam"` 會輸出 Foam-compatible Markdown：

- 檔案層 YAML frontmatter：`type: evidence_pack`、`source_doc_id`、`bundle_version`、returned/matched counts。
- 每個 evidence span 都有 `^spn-...` block anchor，可被 `[[paper-key#^spn-...]]` 或 `![[paper-key#^spn-...]]` 引用。
- 每個 evidence block 保留 `source_revision_id`、`locator_source_sha256`、`text_sha256`、page/line locator 與 verification status。
- 每個 evidence block 內嵌 span-level AssetRef JSON；任何 Foam／下游 wiki
  工作流都可保存它，並在 promotion 前呼叫 `verify_citation_ref`。

可寫檔的最小流程：

```text
citation_bundle(
  doc_id="doc_...",
  query="outcome",
  output_format="foam",
  citation_key="paper-key",
  wiki_root="/path/to/wiki",
  output_path="evidence/paper-key.md",
  index_path="Evidence Index.md",
  overwrite=true
)
```

完成後可跑 health check：

```text
evidence(op="health", wiki_root="/path/to/wiki", output_format="json")
```

Health check 會掃 Markdown 檔內的 span/table/figure AssetRef JSON 與 `[[note#^...]]` wikilink，回報 stale/mismatch/missing span 或 asset、quote hash mismatch、source revision drift，以及 missing target note/anchor。Table/figure AssetRef 主要靠 wiki health 回 manifest 驗證；`verify_citation_ref` 只處理 span-level ref。

## Claim Promotion Workflow

`evidence(op="claim_promotion", doc_id="...", query="...", output_format="json")`
會從 citation index 產生 claim candidates。每個 candidate 都只用 exact
evidence quote 形成 `claim_text`，不會替 LLM 發明新主張，並附上原始
AssetRef、Foam anchor、evidence wikilink 與 verification payload。Foam 輸出會同時保留原始 AssetRef JSON 與完整 Verification Payload JSON fence，讓 wiki 層可離線保存候選資料，promotion 前仍回到 `verify_citation_ref` 驗證。

若要寫入 Foam：

```text
evidence(
  op="claim_promotion",
  doc_id="doc_...",
  query="outcome",
  output_format="foam",
  citation_key="paper-key",
  wiki_root="/path/to/wiki",
  output_path="claims/paper-key-claims.md",
  overwrite=true
)
```

寫檔前會強制檢查每個 candidate 的 verification；只要有
`source_revision_id`、locator、quote hash 或 span mismatch，工具會回傳
blocked 結果，不會把 claim promotion pack 寫進 wiki。

## Table/Figure Foam Notes

Manifest 中的 table/figure asset 可以直接 promotion 成 Foam note：

```text
document_asset(
  op="foam_notes",
  doc_id="doc_...",
  asset_type="all",
  asset_id="all",
  wiki_root="/path/to/wiki",
  output_dir="assets",
  citation_key="paper-key",
  overwrite=true
)
```

輸出 note 類型會是 `type: table_evidence` 或 `type: figure_evidence`，並保留 `asset_id`、page、line range、`source_block_id`、`source_order`、section context、source PDF hash 與 asset locator hash。每個 note 內也會嵌入 table/figure AssetRef JSON，讓 `evidence(op="health")` 可回 manifest 驗證 asset 是否仍存在與 locator 是否漂移。

## DOCX Citation Safety

DOCX save path 會檢查 DFM checksum、doc id drift、pre-save integrity、post-save integrity。DFM block 現在會保存 Word 來源 locator：`source_part`、`source_story`、`source_element`、`paragraph_index` / `table_index`、`run_ranges`、table `cell_locators`、`text_sha256` 與 `locator_version=docx-dfm-locator-v1`。Track Changes sidecar `revisions.jsonl` 會把同一份 DOCX locator 放進 revision record 與 locator object，讓 Word review 和 citation audit 可以對齊。

## 實務建議

引用時優先保存 `AssetRef`，不要只貼文字。對人工文件說明，建議至少記錄：

```text
doc_id
block_id 或 span_id
page
line range
char/byte range
quote/text hash
context
```
