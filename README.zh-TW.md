# asset-aware-mcp

Unreleased 的 `read_pdf_region` 把掃描表格中的明確區域，連到轉錄後的儲存格：
回傳實際 PNG、完整頁面／區域引用，並由驗證、轉製帳本與 Wiki 保留精確來源。
MCP 檢查版本與座標，Agent 核對轉錄及語意。詳見
[PDF 區域證據](docs/wiki/Native-File-Assets.md#pdf-region-evidence-unreleased)。
公開版維持 **1.4.0**，累積 **Unreleased／1.4.x**。


Unreleased 的工作表尺寸操作讓 Agent 讀取原生欄寬／列高，依實際 PDF 畫面調整後
重新預覽，保留儲存格內容與格式、歷史 PDF 及證據。詳見
[工作表版面修正](docs/wiki/Native-File-Assets.md#worksheet-layout-correction-unreleased)。
公開版維持 **1.4.0**，功能累積於 **Unreleased／1.4.x**。


Unreleased 新增 `add_workbook_table`：在既有或獨立建立的 XLSX 指定範圍建立
原生 Excel Table，包含標題、計算欄、合計列與表格樣式，保留既有資料及儲存格格式。
讀回完整建立紀錄後，Agent 核對語意、公式結果與實際畫面。詳見
[原生 Table 建立](docs/wiki/A2T-Tables.md#native-table-creation-unreleased)。
公開版仍 **1.4.0**，持續累積 **1.4.x**。

Unreleased 新增 `update_workbook_table`：同步修改原生 Table 欄名、富文字標題、
計算欄與既有總計列，保留欄位 ID／樣式並更新結構化引用。Agent 可完整讀回標題
XML；計算欄的例外值需明確指定覆寫，公式結果與畫面仍由 Agent 核對。
公開版維持 **1.4.0**，後續沿用 **1.4.x**。

> 給 AI Agent 使用的 citation-ready 文件基礎設施：把 PDF、DOCX、表格、
> 圖片與 evidence span 轉成可重用資產，並組成 Foam／LightRAG wiki。

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

🌐 [English](README.md) · [文件網站](https://u9401066.github.io/asset-aware-mcp/#/overview-zh) · [GitHub Wiki](https://github.com/u9401066/asset-aware-mcp/wiki)

原生 Excel Table 可明確擴大範圍，保留欄位 ID 並同步篩選與計算欄；A2T 以 native_generated 指定沿用新生成的標題／公式，完整讀回區分輸入意圖與實際結果。詳見 [Table 擴展流程](docs/wiki/A2T-Tables.md#native-table-expansion-unreleased)。

Unreleased 的原生 Excel／A2T 工作區保留資料型別與精確來源引用；在 A2T 修改後，
可核對表格與檔案版本再套回原工作簿，並保留實際套用的不可變快照。
`table_grid_apply_enabled` 啟用時，可用明確計畫將 A2T 列欄增刪一次套回原檔；
欄位改名保留 ID，刪除後重建不重用舊身分。操作搬移整張工作表的列欄，原生 Table
邊界與尚未支援的表格編輯另有檢查。詳見 [原生表格工作區](docs/wiki/A2T-Tables.md#native-workbook-workspaces-unreleased)。
公開版仍為 **1.4.0**，後續沿用 **1.4.x**。

Unreleased 的工作表操作可完整讀取引用清單、新增、改名、重排及刪除工作表；
`update_worksheet_grid` 可插入／刪除列欄，保留原生內容與樣式，並搬移已支援的
引用、表格、圖片和註解。請完整讀回操作紀錄；公式結果與版面由 Agent 核對。
詳見 [列欄操作](docs/wiki/Native-File-Assets.md#worksheet-grid-operations-unreleased)。
公開版仍為 **1.4.0**，這些變更規劃於 **1.4.x** 發布。

Unreleased 的 `read_selection` 可將原生值或文字範圍綁定到來源版本，驗證、
轉製帳本與 Wiki 附件均保留完整選取證據；更新文件不會自動遷移舊主張。
詳見 [精確選取引用](docs/wiki/Native-File-Assets.md#native-selections-unreleased)。
公開版維持 **1.4.0**，後續沿用 **1.4.x**。

Unreleased 新增 DOCX 整頁預覽：另裝 LibreOffice Writer 後，可將固定版本的原始
文件轉為實際 MCP PNG，讓 Agent 逐頁核對並比較歷史版本。頁碼以每次轉換為準，
不等於 Microsoft Word 保真驗證。詳見 [DOCX 頁面預覽](docs/wiki/Native-File-Assets.md#docx-page-previews-unreleased)。
獨立 Linux 字型環境已重現並修正中文字缺字，保留 DOCX 原始位元組；Codex 實際
看圖與獨立像素比對涵蓋此修正。詳見 [中文字型核對](docs/wiki/Release-And-Testing.md#cjk-font-correction-evaluation-unreleased)。

## v1.4.0 原生簡報協作與規格查詢遷移

Unreleased 新增整張投影片預覽：使用另行安裝的 LibreOffice Impress，回傳固定版本與
slide ID／part 的實際 MCP 圖片，供 Agent 比較版面、重疊與文字溢出。靜態預覽不代表
PowerPoint 保真驗證通過。詳見[投影片預覽](docs/wiki/Native-File-Assets.md#pptx-whole-slide-previews-unreleased)。

`main` 開發版新增 `table_cite(operation="read")`，可分頁讀回完整引用並核對
固定 hash；尚未包含在已發布套件。詳見 [完整引用讀回](docs/wiki/A2T-Tables.md)。
未發布項目也包含有檢查保護的 PPTX 文字框新增／形狀刪除，以及 A2T 操作結果的
實際列 ID。詳見 [形狀操作](docs/wiki/Native-File-Assets.md#pptx-shape-operations-unreleased)。
公開版維持 **1.4.0**，後續開發沿用 **1.4.x**，不因單次功能提交跳版號。
未發布的圖片操作可將 PNG／JPEG 資產插入、替換到 PPTX，透過 MCP 顯示內嵌
圖片，再拆出為獨立版本資產。共用圖片不被覆寫，來源引用保留在歷程。
詳見 [圖片資產操作](docs/wiki/Native-File-Assets.md#pptx-picture-assets-unreleased)。

未發布的投影片操作可探索各母片版型、新增空白繼承預留位置與格式化文字框、
依固定 ID 重排及檢查相依後刪頁；既有套件內容持續保留。詳見
[投影片結構操作](docs/wiki/Native-File-Assets.md#pptx-slide-structure-unreleased)。

未發布的表格格網已支援固定版本的列欄插刪與尺寸調整，並檢查合併區擴縮與起點移動。
合併儲存格須明確選擇「其他格為空」或「依序搬移段落」；拆分保留左上角
已搬移的內容，文字格式、欄位與連結的段落 XML 持續保留。
未發布的原生表格可指定列欄尺寸、合併格與文字格式，再沿用讀取／修改／刪除。
引用顯示的預設／模板也有 typed 規格可查。詳見
[原生表格](docs/wiki/Native-File-Assets.md#native-pptx-tables-unreleased)。

未發布的轉製來源帳本可連結原生來源與產物的完整版本引用，保留修訂／撤回
紀錄，並將來源附件帶入證據 Wiki；機械檢查與 Agent 核對聲明各自保存。
詳見 [跨資產來源關係](docs/wiki/Native-File-Assets.md#native-derivations-unreleased)。

原生 PDF 頁面協作也列於 **Unreleased**：讀取／顯示頁面、建立新 PDF、
插入／複製／刪除／重排頁面及調整旋轉／裁切，先建立受管理版本。
頁面證據與 Wiki 預覽保留完整來源附件。詳見
[PDF 操作與限制](docs/wiki/Native-File-Assets.md#native-pdf-pages-unreleased)。
MCP 檢查物件圖、來源版本及有限解析度的獨立渲染讀回；
語意、完整解析度版面與檢視器行為由 Agent 核對。

1.4.0 提供 `contract.for_op` 與 `native-contract-v2`。先查看
`schema_delivery`，需要分段時沿用 `schema_request` 與 `schema_sha256`，
客戶端須遷移原本假設完整 schema 永遠內嵌的讀法。詳見
[查詢與遷移說明](docs/wiki/Native-File-Assets.md#contract-v2-140)。
原生 PPTX 已可建立、讀取投影片／備註形狀、精確修改文字 run、核對版本引用及
匯出證據 Wiki。完整形狀 XML 與套件附件會保留；版面、文字溢出與繼承格式
由 Agent 核對。詳見 [PPTX 操作說明](docs/wiki/Native-File-Assets.md#native-pptx-140)。

PDF 已加入 Codex 實際呼叫 MCP 的掃描／混合頁測試，獨立核對轉錄、引用、
CRUD、Excel 與資產包，並修正實測發現的旋轉圖片裁切問題。詳見
[重現驗證流程](docs/wiki/Release-And-Testing.md#codex-pdf-evaluation)；
合成測資通過不代表通用 OCR 正確率或 PDF 回寫保真。

## v1.3.0 原生 DOCX 版本與元件證據

**1.4.x 未發布工作**新增 `create_docx`，以及主本文段落／可編輯表格的
`add_docx_blocks`／`delete_docx_blocks`。富文字、合併格與明確欄寬會在儲存後
讀回檢查；結構操作綁定目前版本的完整區塊引用，分頁與版面由 Agent 核對。
詳見 [DOCX 建立與結構操作](docs/wiki/Native-File-Assets.md#docx-creation-and-body-structure-unreleased)。

- 讀取固定版本的 DOCX/DFM，檢查編輯後先建立受管理版本，再明確回寫來源。
- 驗證完整解析區塊的引用；文字分段仍保留完整證據 hash。
- 匯出區塊筆記、原始 DOCX 與各套件檔案的原始位元組；保留舊快照及連結。
- MCP 檢查來源與格式，Agent 核對語意、Word 版面、欄位及抽取完整性。
  結構插刪與完整 CSL 引用仍待實作。

## v1.2.0 原生證據 Wiki 與筆記保護

- 原生儲存格引用可對不可變來源版本驗證，舊版本引用仍可核對。
- XLSX/XLSM 可匯出為固定版本的 Foam 筆記、原始附件及完整 JSONL 證據；
  自訂引用顯示與 canonical reference 保持獨立。
- 保留既有原生快照，PDF bundle 遇到人工修改會拒絕替換；通過核對的更新保留備份，
  相同內容直接重用。
- 延續固定資產 ID、XLSX 建立、局部儲存格編輯與 MCP SDK 2.2.0。
  語意、畫面、公式結果仍由 Agent 核對；完整 CSL 仍待實作。

## v1.0.1 可靠性翻新

- 大型 PDF 文字、表格與圖片結果改用 private、atomic、具大小上限的
  MessagePack 檔案交接，不再透過 multiprocessing pipe，也不反序列化可執行的
  pickle。多 MB raster 不會再因 pipe backpressure 卡死；partial、oversized、
  malformed 或 worker crash 一律 fail closed。
  Worker timeout 環境值必須是有限數；`NaN`／無限值會回退到安全預設值。
  有限的 `<=0` 值僅保留為歷史 direct mode 相容開關，managed production
  launcher 不應使用。
- Codex managed MCP 設定現在用真實 TOML parser 驗證，會保留 custom 與 unrelated
  tables，設定 180／900 秒啟動與工具 timeout，且不把 credential value 寫入檔案。
  隔離的 working directory 加上 `ASSET_AWARE_DISABLE_DOTENV=true`，也避免 server
  在啟動後又偷偷讀取無關 workspace 的 `.env`。
- Codex／Cline／Copilot 的全域設定寫入現在受 workspace trust 保護，且只使用
  extension 精確版本與隔離的 global storage；偽造同名 repository 不能把本地
  Python 或 `.env` 值持久化進全域 agent launcher。
- MCP SDK 2 operational log 固定走 stderr；空白或空 ingest request 會在建立 job
  前拒絕。true-stdio 回歸則實際驗證大型圖片、表格、citation-ready evidence、
  完整 bundle hash、Foam notes、deterministic re-export，以及來源 PDF 完全不變。
- GitHub Pages 已換成雙語 responsive Evidence Rail、精確 30-tool explorer、安裝／
  開發注意事項、生成式文件 reader 與 GitHub／Release／Issue 入口，不再公開過時的
  raster 架構截圖。

## 🎯 為什麼需要資產感知 MCP？

Agent 需要操作原生文件、可編輯元件與可重用證據，包含獨立建立表格。
目標是跨格式 CRUD 與格式保留。MCP 提供來源／版本、格式保護及操作結果的必要檢查；
Agent 負責完整的語意與視覺核對，依據可檢查的結果協調修正。

目前覆蓋 PDF 讀取／拆解／可攜資產匯出、DOCX/DFM 局部編修與獨立 A2T 表格。
v1.1.0 新增原生檔案登錄、不可變版本、獨立 XLSX 建立、XLSX/XLSM 局部儲存格編輯、
明確來源回寫與外部修改同步。詳見[原生文件用法與限制](docs/wiki/Native-File-Assets.md)。
更廣泛的原生 CRUD、各格式必要檢查與 Agent 核對流程仍在開發；有轉檔工具不代表保真回寫。
詳見[規格與 contract](docs/spec.md)及[路線圖](ROADMAP.md)。

Asset 包含身分、版本、原生定位、表示、關係、操作能力與驗證狀態。Wiki 筆記是
連回資產的文本投影；人類引用格式可擴充，底層證據引用保持獨立。

v1.1.0 已加入引用格式 contract：支援來源標籤、作者／年份、指定編號與自訂範本，
套用到證據與 Foam 匯出時保留原始來源資訊；完整 APA/CSL 渲染仍待實作。
詳見[用法與限制](docs/wiki/LLM-Wiki-Knowledge-Base.md#citation-format-contracts)。

1.2.0 新增原生引用驗證與 `native/export_wiki`：版本固定的筆記、
原始附件、完整儲存格證據及自訂引用格式。新版本保留舊快照，遇到人工修改會拒絕覆蓋。
詳見原生文件操作指南。1.2.0 也補上既有 PDF bundle 的清單／hash 核對；人工修改會拒絕替換，通過核對的
產生內容若需更新則保留舊目錄備份。

## ✨ 特色

1.3.0 新增原生 DOCX 橋接：`read_docx`／`update_docx` 綁定來源版本，
沿用 DFM 檢查後建立受管理版本，保留未修改的 package parts，並支援明確指定的
文字修訂追蹤。DOCX 區塊引用支援分段讀取及原生驗證；Wiki 快照包含完整區塊
紀錄、原始 DOCX 與逐一保留的套件附件，既有 1.2.0 快照身分與內容保持不變。
來源回寫與 Agent 版面核對仍是後續步驟；詳見[DOCX 橋接指南](docs/wiki/Native-File-Assets.md#130-native-docx-bridge)。

- 📄 **資產感知 ETL** - PDF → Markdown，採可插拔多引擎解析架構（`ETL_ENGINE`）：
  - **PyMuPDF**（預設）- 快速提取（~50MB），免模型
  - **PyMuPDF4LLM**（`[pdf-plus]`）- 同生態 drop-in 升級，具版面感知，免 GPU
  - **Docling**（`[docling]`）- MIT 授權，layout+table+formula+chart 引擎；主環境無法直接安裝時會透過獨立 `.venv-docling` 直譯器橋接（見 [docs/docling-setup.md](docs/docling-setup.md)）
  - **MinerU** - adapter 保留；因上游仍鎖住有漏洞的 `transformers<5` 鏈，套件 extra 暫停安裝
  - **Marker** - adapter 僅保留供評估；upstream `marker-pdf` 與 patched Pillow 安全底線衝突期間，production selection 一律 fail closed。歷史參數 `use_marker` 現在只代表「偏好目前設定的 structured extractor」，不能繞過 security hold。
- 🧩 **統一 Segmentation 匯出** - 產生正規化 `segmentation.json`，整合 manifest、blocks、reading order 與持久化 line span。
- 🩺 **安全 PDF Preflight Router** - `document(op="preflight")` 逐頁分類 native、sparse、image、scanned、hybrid，輸出 1-based/top-left locator、來源 SHA-256、OCR 理由與引擎建議；檢查在具 timeout／資源上限的隔離 process 執行。
- 📦 **可重用 Agent Asset Bundle** - `document(op="export_assets")` 產生 deterministic `manifest.json`、`assets.jsonl`、媒體副本，以及可攜式 Foam `index.md`／`notes/**` 子樹，完整保留 stable ID、hash、locator 與 citation ref。
- 🛡️ **PDF 安全、結構、覆蓋率與可及性稽核** - 受 OpenDataloader 啟發的 artifact-only 報告會標示隱藏／超出頁面／prompt-injection 文字、原生結構訊號、segmentation 覆蓋缺口，以及可及性／可讀性就緒度；它們透過既有 `document` facade 提供，不增加公開工具數。`document(op="prepare_ai")` 與 `document(op="auto")` 會回傳 agent-ready 狀態與下一步。
- 🧭 **結構指標檢索（Structural Pointer Retrieval）** - 受 Proxy-Pointer 啟發的 `document(op="pointer_index")`、`document(op="structural_retrieve")` 與 `document(op="compare")` 會保留章節 breadcrumb、line/char/byte locator、來源 hash、asset ID 與 evidence-span provenance，不需新增 MCP 工具。
- 🖼️ **版面 Overlay 偵錯** - 可從 `original.pdf` 產生 page overlay，直接檢查 bbox、區塊類型與 reading order。
- 🔤 **按需 OCR 前處理** - 針對掃描型 PDF 提供可選 `ocrmypdf` 前處理流程，再進行 ETL。
- 🧭 **章節導航** - 透過 `section` facade 提供動態層級章節樹：瀏覽、搜尋、詳情、內容讀取、區塊提取，支援任意深度的標題層級。
- 🔄 **非同步任務流水線** - 支援大型 PDF ingest、目前設定的 structured parse、OCR 與 conversion 的非同步處理與進度追蹤。
- 🔀 **混合格式批次攝入** - `document(op="auto", file_paths=[...])` 會自動偵測 PDF 與 DOCX/DOC/ODT/ODS 混合的批次，於單一 background job 內以各自正確的引擎攝入每個檔案，隔離單檔失敗不中斷其餘檔案，並回報逐檔進度——不需新增公開工具。
- 🗺️ **文件清單 (Manifest)** - 為 Agent 提供結構化的文件「地圖」，實現精確數據存取。
- 🧠 **LightRAG 整合** - 知識圖譜 + 向量索引，支援跨文件對比與推理。
- 🧾 **Verified Citation Bundles** - `citation_bundle`、Foam evidence pack、citation health check、table/figure evidence notes 與 claim promotion 可輸出含 locator、quote/hash、context、CRAAP scaffold 與 verification 的 evidence bundle。
- 📝 **Docx 即時編輯 (DFM)** - 以 Markdown 格式編輯 .docx 檔案，透過 **Docx-Flavored Markdown** 格式。支援 `.docx` / `.docm`，也支援 `.doc`、`.odt`、`.ods` 經 LibreOffice 自動轉換後攝入。balanced surface 保留 6 個 DOCX/DFM 公開入口，涵蓋匯入、讀取、儲存、驗證、轉換、表格結構編輯計畫，以及 Docx ↔ A2T 表格橋接。
- 🛡️ **DFM 完整性檢查器** - 在 post-ingest、pre-save 與 post-save 各階段自動驗證並修復可安全修復的問題，捕捉 orphan marker、欄位數不一致與格式矛盾。
- 📊 **A2T (Anything to Table)** - 7 個 operation-based 工具，從**任意來源**（PDF 資產、知識圖譜、URL、使用者輸入）建立專業表格。支援：穩定 row ID、row search/filter/paging、citation coverage、artifact-only 大表輸出、跳過大型表格時的可操作 UX、**引用管理** (AssetRef)、**變更審計**、**Schema 演進**、**模板**、**草稿機制**與**節省 Token 的續作模式**。
- 🖥️ **VS Code 管理擴充功能** - 提供圖形化介面監控伺服器狀態、已匯入文件、document artifacts、citation spans，以及 **A2T 表格與草稿**，支援一鍵開啟 Excel。
- 🔌 **MCP SDK 2 伺服器** - 使用官方 Python SDK `MCPServer`、runtime context injection 與 v2 client；刻意不支援 MCP SDK v1。
- 🔬 **研究級、領域中立資產** - 可處理學術、技術、政策與營運文件；具大小上限的圖片 bytes 能讓相容的 multimodal client 分析圖像，而不是依賴 server-local 路徑。

## 🏗️ 架構

```
┌─────────────────────────────────────────────────────────┐
│                    AI Agent (Copilot)                   │
└─────────────────────┬───────────────────────────────────┘
                      │ MCP 協定 (工具與資源)
┌─────────────────────▼───────────────────────────────────┐
│            MCP 伺服器 (模組化 Presentation 層)          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ tools/: 30 個公開工具（balanced surface）       │   │
│  │   17 個 facade tools + 13 個高頻 shortcuts      │   │
│  │   compact=17 │ legacy/direct 相容模式=63        │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │ resources/: 13 資源，2 個模組                   │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                  ETL 流水線 (DDD)                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ PyMuPDF  │  │  資產    │  │ LightRAG │              │
│  │ 轉接器   │→ │  解析器  │→ │  索引    │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                      本地儲存                           │
│  ./data/                                                │
│  ├── {doc_id}/        # PDF 文件 artifacts             │
│  ├── docx_{id}/       # Docx IR + DFM + 資產            │
│  ├── tables/          # A2T 表格 (JSON/MD/XLSX)         │
│  │   └── drafts/      # 表格草稿 (持久化)               │
│  └── lightrag_db/     # 知識圖譜資料庫                  │
└─────────────────────────────────────────────────────────┘
```

## 📁 專案結構 (DDD)

```
asset-aware-mcp/
├── src/
│   ├── domain/              # 🔵 領域層：實體、數值物件、介面定義
│   ├── application/         # 🟢 應用層：文件服務、表格服務 (A2T)、資產服務
│   ├── infrastructure/      # 🟠 基礎設施層：PyMuPDF、LightRAG、Excel 渲染器
│   └── presentation/        # 🔴 展現層：MCP SDK 2 MCPServer
├── data/                    # 文件與資產儲存目錄
├── docs/
│   └── spec.md              # 技術規格書
├── tests/                   # 單元測試與整合測試
├── vscode-extension/        # VS Code 管理擴充套件
└── pyproject.toml           # uv 專案配置
```

## 📐 架構與流程

持續維護且會跟實作一起驗證的入口是[文件網站](https://u9401066.github.io/asset-aware-mcp/)、
[架構說明](docs/wiki/Architecture.md)、[PDF 流程](docs/wiki/PDF-Document-Workflow.md)、
[MCP 工具目錄](docs/wiki/MCP-Tools.md)與[發布檢核](docs/wiki/Release-And-Testing.md)。
這些文字與網站資料會由 gate 檢查，避免工具數、引擎 security hold 或發布流程藏在已過時的截圖裡。

## 🚀 快速開始

```bash
# 安裝依賴 (使用 uv) — 預設維持快速 PyMuPDF backend
uv sync

# 可選高精度 PDF→資產引擎：
# uv sync --extra pdf-plus   # PyMuPDF4LLM：同生態 drop-in 版面感知升級
# uv sync --extra docling    # Docling：MIT 授權 layout+table+formula+chart
# MinerU 與 Marker packaged extras 目前皆為安全暫停。
# 安裝後設定 ETL_ENGINE=pymupdf4llm|docling。

# 啟動 MCP 伺服器
uv run python -m src.presentation.server

# 或使用 VS Code 擴充套件進行圖形化管理
```

Runtime 說明：
VS Code 擴充套件在透過 version-pinned `uv tool run` 啟動 MCP server 時，會優先使用受管理的 Python 3.11 runtime，並在舊機器上 fallback 到 Python 3.10。這可避免終端使用者機器上發生原生套件編譯，特別是未安裝 Xcode Command Line Tools 的 macOS；但專案本身仍保留對較新 Python 版本的相容性。

安裝範圍說明：
- VSIX 以使用者範圍安裝。trusted workspace 中的 VS Code 原生 MCP provider 可使用
  workspace-scoped `DATA_DIR`、cache、settings 與 `.env`；local source 只在 extension
  Development/Test mode（或未來明示 opt-in）使用。
- Codex 與 Cline 的全域 entry 永遠從 extension global storage 啟動
  `asset-aware-mcp==<extension-version>`，不繼承 workspace local source、workspace
  setting 或 repository `.env`。Restricted Mode 完全跳過 external config 寫入與
  assistant asset sync。

引擎選擇說明：
`ETL_ENGINE` 選擇拆解後端（預設 `pymupdf`）。目前 packaged structured engines 是 `pymupdf4llm` 與 `docling`，皆採懶加載，extra 未安裝時安全降級至 PyMuPDF。Marker 因 `marker-pdf` 仍要求 `Pillow<11` 而暫停；MinerU 3.4.4 又鎖定 `transformers<5`，但安全修補需要 `transformers>=5.5`，因此兩者 adapter 留在程式庫中、packaged extra 則不安裝已知有漏洞的 dependency chain。攝入前可先用 `document(op="preflight", pdf_path="...")` 決定走原生快速抽取、OCR 或 Docling。

Agent asset／Foam handoff：

```text
document(op="preflight", pdf_path="/papers/source.pdf")
document(op="auto", file_paths=["/papers/source.pdf"])
document(op="export_assets", doc_id="doc_...", output_dir="agent-assets")
```

匯出目錄是 deterministic 且可攜的：`manifest.json` 是 bundle contract，
`assets.jsonl` 是 agent-readable inventory，`index.md` 與 `notes/**` 可直接掛入或複製到 Foam workspace。

## 🔌 MCP 工具

預設 runtime surface 是 **balanced**：30 個公開工具，保留完整文件工作流，但避免 agent 一開始就面對過多 direct tools。它由 17 個 operation-based facade tools 加上 13 個高頻 shortcuts 組成。若需要更嚴格 allow-list，可設定 `ASSET_AWARE_MCP_TOOL_SURFACE=compact` 只公開 17 個 facade；若舊 client 仍依賴 direct tool 名稱，可設定 `ASSET_AWARE_MCP_TOOL_SURFACE=legacy` 或 `ASSET_AWARE_MCP_ENABLE_LEGACY_TOOLS=true` 開啟 63-tool 相容庫存。

| 範圍 | Balanced 公開工具 |
|------|-------------------|
| 文件、資產、證據、轉換 | `document`, `document_asset`, `evidence`, `convert_document`, `ingest_documents`, `list_documents`, `parse_pdf_structure`, `fetch_document_asset`, `find_evidence_spans`, `verify_citation_ref`, `citation_bundle` |
| DOCX / DFM | `docx`, `docx_table`, `ingest_docx`, `get_docx_content`, `save_docx`, `docx_table_edit_plan` |
| 章節、工作、KG、ETL Profile | `section`, `job`, `get_job_status`, `list_jobs`, `knowledge`, `etl_profile` |
| A2T 表格 | `plan_table`, `table_manage`, `table_data`, `table_cite`, `table_history`, `table_draft`, `discover_sources` |

完整 operation、shortcut rationale 與 legacy direct-tool mapping 請見 [MCP Tools](docs/wiki/MCP-Tools.md) 與 [Tool Consolidation](docs/wiki/MCP-Tool-Consolidation.md)。

Agent 接力建議：
新 PDF 用 `document(op="auto", file_paths=[...])`，既有文件用 `document(op="auto", doc_id="...")` 或 `document(op="prepare_ai", doc_id="...")`。`document(op="prepare_ai", output_format="json")` 會回傳 v2 readiness contract：`status`、`blockers`、`warnings`、`capabilities`、`artifacts`、`missing_audits`、`invalid_audits`、`audit_artifacts`、`next_actions`。`document(op="audit", doc_id="...")` 只會在現有稽核 artifacts 存在且有效時重用；需要全部重建時傳 `refresh=true`。readiness 與 job status 的 artifact discovery 是 read-only，不會因查狀態建立新的文件資料夾。

`document(op="audit")` 會一次處理 safety、native structure、coverage 與 accessibility 報告；當 agent 需要章節層級的結構檢索或比較時，使用 `document(op="pointer_index")`、`document(op="structural_retrieve", query="...")` 與 `document(op="compare", doc_b_id="...", criteria="...")`。這些 operation 共用現有 `document` facade，不增加公開 tool inventory。

PDF 稽核注意：
這些報告是受 OpenDataloader 類 artifact 工作流啟發，但不是 sanitizer、PDF/UA 認證，也不是 OpenDataloader 相容層；它們會保留來源 artifact，並以保守診斷供人工或 agent 後續檢查。

## 🔧 技術棧

| 類別 | 技術 |
|----------|------------|
| 語言 | Python 3.10+ |
| ETL | **PyMuPDF**（預設）+ 安全可選 **PyMuPDF4LLM**／**Docling**；MinerU、Marker adapter 暫時 dependency security hold |
| RAG | LightRAG (lightrag-hku) |
| MCP | 官方 Python MCP SDK 2（`MCPServer`）；不支援 SDK v1 |
| 儲存 | 本地檔案系統 (JSON/Markdown/PNG) |

## 📋 相關文件

安裝建議：
- 預設安裝：`uv sync`（精簡約 227 MB；不含 LightRAG/KG 相依套件）。
- LightRAG／Knowledge Graph backend（選用，v0.6.34 起）：已發布套件／uvx 使用者執行 `uv tool install --upgrade --python 3.11 'asset-aware-mcp[lightrag]'`，local source checkout 執行 `uv sync --extra lightrag`；設定 `ENABLE_LIGHTRAG=true` 前必須先安裝。
- VS Code 擴充套件：從 Command Palette 執行 `Asset-Aware MCP: Install LightRAG Backend`；它會自動判斷 source 或 published mode，並顯示對應安裝指令。
- OpenRouter optional preset（v0.6.35 起）：在 VS Code extension Settings 選 `openrouter`，填入 `OPENROUTER_API_KEY`；預設 `OPENROUTER_MODEL=liquid/lfm-2.5-1.2b-instruct:free`，適合低成本快速摘要與 RAG 草稿查詢。
- 高精度 PDF 引擎：`uv sync --extra pdf-plus`（PyMuPDF4LLM）或 `uv sync --extra docling`（Docling），再設定對應 `ETL_ENGINE`。Docling 附跨平台隔離安裝腳本，見 [docs/docling-setup.md](docs/docling-setup.md)。
- MinerU／Marker：adapter 保留供追蹤上游；packaged extras 暫為空，直到 dependency cap 可解析到已修補的 transformers／Pillow。
- VS Code extension：`assetAwareMcp.enableMarkerBackend` 設定仍保留，但 security hold 期間 launcher 不會安裝 `marker-pdf`。

- [技術規格書](docs/spec.md) - 詳細技術定義
- [系統架構](ARCHITECTURE.md) - 架構設計說明
- [專案憲法](CONSTITUTION.md) - 開發原則與規範

## 📄 授權

[Apache License 2.0](LICENSE)
