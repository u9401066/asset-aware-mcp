# Citation Provenance

<a id="captured-etl-evidence-unreleased"></a>

## Captured ETL evidence (1.4.1)

PDF 擷取後的文字、表格與圖片原本指向可變動的 ETL 目錄。需要長期保存或加入
CSL 文稿時，先明確建立不可變的證據快照；原始 PDF、擷取文字、blocks、manifest
及所選圖片都會保留。刪除或重新擷取 ETL 資料後，已保存的證據仍可讀取與檢視。

先讀完 `evidence(op="csl_contract")` 的分頁契約，再依序操作：

| 操作 | `ref` 內容 | 結果 |
| --- | --- | --- |
| `inspect_etl_source` | `doc_id`、`source_type`、`source_id` | 完整 `asset_ref` 與證據紀錄，不建立快照 |
| `capture_etl_source` | 上一步完整 `asset_ref` | 不可變 `etl-citation-ref-v1` 及完整證據 |
| `read_etl_source` | 完整快照引用 | 重新核對所有附件並讀回原證據 |
| `view_etl_source` | 完整快照引用 | 來源 PDF 整頁的實際 MCP PNG |

`source_type` 為 `span`／`table`／`figure`；`source_id` 使用工具回傳的 span 或
asset ID。文字可用 `evidence(op="find")` 探索，表格與圖片可用 `document(op="inspect")`
探索。即使探索結果只有長文字預覽，也能透過 `inspect_etl_source` 取得完整引用：

```json
{
  "op": "inspect_etl_source",
  "ref": {"doc_id": "doc_...", "source_type": "span", "source_id": "spn_..."},
  "text_limit": 4000
}
```

前三種操作都要以同一個 `text_sha256`，透過 `text_offset` 與
`expected_text_sha256` 讀到 `next_text_offset=null`，串接並核對 UTF-8 hash 後
才解析 JSON。擷取拒絕部分引用、舊引用、錯誤定位或預覽；expected hash 不符時
不建立快照。`view_etl_source` 使用 `render_size=64..2048`（最長邊像素），不使用
文字分頁參數；沒有已知頁碼時會明確失敗，不猜測頁面。

將回傳的完整快照引用放進 CSL 文稿 `sources`，再用 cite 的 `source_keys`
連結。可混用既有原生 cell／DOCX block／PPTX shape／PDF 等引用；不要直接把
仍指向 ETL 目錄的舊 AssetRef 放入 CSL。指定 `wiki_root` 後，Wiki 會帶走原始
來源、完整證據 JSON 與所有快照附件，引用 note 提供證據連結。原始 manifest
可能保留歷史路徑作紀錄，但讀取快照不依賴那些路徑。

快照核對 bytes、hash 與 locator 一致性，**不代表擷取內容或引用主張正確**。
Agent 必須比較全文、表格、實際來源頁影像及書目資料，再決定是否引用與如何
修正。原始文字位元組與正規化文字 hash 分開保留；引用文字沿用既有 BOM／編碼
解碼及 LF 換行規則。單份快照最多 128 MiB，單個 metadata／圖片最多 20 MiB，
完整證據紀錄最多 2 MiB。DOCX DFM 是另一條管線，CSL 使用既有原生 DOCX 引用。

<a id="csl-citation-documents-unreleased"></a>

## CSL citation documents (1.4.1)

學術引用以整份文稿為單位處理：同作者同年份消歧、群組排序、編號與重複註解
會影響其他引用，不能逐筆套模板。`evidence(op="csl_contract")` 提供固定 hash 的
分頁契約；`evidence(op="render_citations", citation_document=...)` 回傳完整引用與
參考文獻。既有 `citation-format-v1` 自訂模板與 source／author-year／numeric
顯示預設保持原本用途；author-year 模板不能當作 APA 認證。

可選樣式為 `apa`（APA 7）、`chicago-author-date`、
`chicago-notes-bibliography`（Chicago 18）與 `vancouver`（官方 Vancouver/NLM
的 `nlm-citation-sequence`）。樣式決定群組內是否排序；Chicago 18 的官方
作者年份樣式保留輸入順序。語系可指定 `en-US`／`zh-TW`，另附 CSL 所需的
`zh-CN` 基礎詞彙回退。所有 XML、schema、處理器都有固定來源及雜湊。

需要 PATH 上的本機 Node.js（最低 20，建議使用受支援的 Node.js 24 LTS）。
不在 runtime 下載樣式、安裝套件或連線找文獻。未配置 Node 時會明確回報，
其他文件及自訂模板功能照常運作。內附 citeproc npm 2.4.63，處理器內部版號
1.4.61；兩者分別記錄。上游授權與完整出處保留於套件的 `csl_resources`。

最小文稿例子：

```json
{
  "style": "apa",
  "locale": "en-US",
  "items": [{
    "id": "report",
    "type": "report",
    "title": "Example report",
    "author": [{"literal": "Example Institute"}],
    "issued": {"date-parts": [[2020]]}
  }],
  "clusters": [{"id": "claim-1", "cites": [{"id": "report"}]}]
}
```

以 CSL-JSON 結構提供作者、日期及出版資料，不從任意字串猜測。`clusters` 順序
就是文稿順序；Chicago 註腳需正數且依序的 `note_index`，其他樣式使用 0。
`uncited_ids` 可明確加入未於文中引用的文獻。缺少 author／issued／title 會列入
`missing_metadata`，引擎可能依樣式產生無日期等顯示，但不補造來源資料。

若需證據，先取得原生完整引用，放入文稿的 `sources` 字典，再在各 cite 的
`source_keys` 指定對應鍵。支援既有原生 cell／DOCX block／PPTX shape／PDF
page、region／CSV field／selection／whole-file 引用。每一筆固定 revision
引用都重新驗證；CSL `locator` 是另行提供的印刷頁碼或節號，不會覆寫原生
定位，也不會自動證明它對應 PDF 的實際頁面。語意及書目真實性由 Agent 核對。

回應包含 `text_excerpt`、`text_sha256` 與 `next_text_offset`。每次以相同文稿
和 hash 讀完所有頁，串接後核對 UTF-8 SHA-256 再解析；文字片段不是完整結果。
`text_limit` 為 1–8,000 字元，實際切頁另考量 JSON 跳脫後大小。
`expected_text_sha256` 不符時拒絕操作，且不建立 Wiki。

指定 `wiki_root` 後，每種文稿／樣式會建立不可變快照：完整 `citations.json`、
各引用的 wikilink note、精確來源附件、manifest，以及 `references.html`
排版預覽（斜體、懸掛縮排、行距）。已有相同快照必須逐檔核對才可重用；人工
改動不會被覆蓋。來源更新後舊引用仍固定原版本，不能自動把新內容當成舊證據。
來源本身與 native `export_wiki` 的既有投影不改寫；此操作建立文稿引用快照。

目前上限為 500 筆書目、1,000 個引用群組、2 MiB 輸入、8 MiB 結果；來源附件
與其他 Wiki 檔案合計最多 128 MiB。Node 子程序有記憶體及時間限制，超限明確
失敗，不回傳部分參考文獻。正式文稿仍應由 Agent 核對書目、印刷定位及排版。

參考實作：[citeproc-js](https://github.com/Juris-M/citeproc-js)、
[CSL 規格](https://docs.citationstyles.org/en/stable/specification.html)、
[官方樣式](https://github.com/citation-style-language/styles)。

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
locator／range，也不能拿去 verify。公開版的完整 exact quote、hash 與 locator 保存於
寫入磁碟的 citation／agent-asset bundle；亦可用上述
`inspect_etl_source` 分頁讀取完整引用，不必先匯出。若要給人類文件、KG answer 或外部審查使用，
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
