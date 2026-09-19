# Roadmap

Asset-Aware MCP 的核心方向是把 PDF、DOCX/DFM、表格與圖片轉成可重用、
可驗證、可攜式的 agent assets，並以穩定 locator、hash、citation 與 Foam notes
支援 LLM wiki、知識圖譜和跨文件工作流。

正式版本、相依套件與安全狀態以 [CHANGELOG.md](CHANGELOG.md)、
[README.md](README.md) 和 release artifacts 為準；本頁只保留仍有效的方向，
不再把已完成的舊版工作列為「進行中」。

## 2026-09-18 active goal — not complete

- [ ] 直接使用 Codex 測試 MCP 的 PDF 圖像轉結構化資料 CRUD；1.4.0 已提供
  合成數位／掃描／混合文件基線與獨立稽核，後續擴充真實複雜文件。
- [ ] Maintain MCP SDK 2.0+ compatibility, evaluate current native-format/PDF
  libraries against official repositories and regression evidence; adopt suitable
  updates without removing format features or bypassing release checks.

- [ ] Native format capability contracts and asset registry: source/components,
  revisions, locators, representations and relationships, including unknown formats.
- [ ] Native read/decompose/create/update/delete/writeback across Word,
  spreadsheets, presentations, PDF, text/web/structured documents and media.
- [ ] Necessary MCP source/version, format and operation-result checks with
  atomic writes; agent-led complete semantic/visual verification and correction,
  with explicit check coverage and unsupported features.
- [ ] Independent table creation and native/A2T round trips preserving cell
  identities, types, formulas, styles and provenance.
- [ ] Cross-format wikilink evidence library with stable targets, attachments,
  provenance and protection of curated notes.
- [x] Versioned custom citation display contracts for existing PDF evidence,
  Foam notes and portable asset exports, independent of canonical provenance.
- [ ] Standards-aware academic citation rendering (APA/Chicago/CSL) and citation
  integration with the remaining native-format evidence adapters.
- [ ] Real-file regressions, README/Pages/metadata/labels/MEM synchronization,
  reviewed staged commits/pushes and fully verified releases throughout the work.

## 1.4.x 開發中（尚未發布）

- 跨資產轉製帳本連結既有完整原生引用，保留修訂／撤回、hash 分頁與
  Agent 核對聲明；Wiki 帶走活躍關係的來源附件，舊快照仍保留。
  PDF 頁到 PPTX 表格是頁／形狀粒度；逐格語意映射與自動判讀仍是後續工作。
- 已加入原生 PDF 頁面操作、PPTX 文字框／圖片／表格新增、既有形狀刪除，
  以及圖片替換／拆出與來源歷程；使用不可變版本與明確回寫。
- 原生表格可指定尺寸、合併與直接文字格式，沿用完整形狀引用與 Wiki；
  既有格網已可列欄插刪／調整尺寸與合併區擴縮；A2T 自動橋接和完整渲染核對仍未完成。
- 實際 Codex 掃描頁到 PPTX 表格的實測與獨立稽核已加入，初次辨讀及恢復
  分開記錄；citation display 預設／模板有 typed schema，來源證據另行保存。

- `table_cite read` 已提供完整 cell/value/citation 的固定 hash 分頁讀取；Agent
  可檢查保存的來源定位，`get` 維持摘要。內容一致不等於來源或語意正確。
- SDK2 與實際 Codex PDF 測試已加入最後修正後的完整引用讀回稽核；真實複雜
  文件 corpus、格式結構 CRUD 與學術引用引擎仍在進行。

## v1.4.0 已發布階段成果

- 原生 PPTX 建立、投影片／備註形狀讀取、既有文字 run 更新、版本引用與
  完整 package Wiki 已發布；後續結構操作見上方尚未發布的 1.4.x 內容。
- `native-contract-v2` 提供按操作查詢與 hash 固定的完整 schema 分頁；
  已說明舊版 inline response 的遷移方式，專案後續小幅更新沿用 1.4.x。
- Codex 實際 MCP 測試涵蓋圖像讀取、35 cells 轉錄、引用、更新／刪除／還原，
  以及 Excel／Wiki 匯出；SDK2 三種 PDF 模式納入回歸測試。
- 修正旋轉／裁切 PDF 的 figure 渲染座標，16 組獨立像素比對通過。
  Agent 初次轉錄錯誤與修正分開記錄；保留 µ／μ 嚴格比對失敗，沒有宣稱
  任意掃描文件皆能無損轉錄。結構化表格 CRUD 不會改寫原 PDF 版面。
- 1,546 Python tests、199 VSIX tests、完整發布檢查及公開 artifacts 交叉驗證
  完成；[v1.4.0 release](https://github.com/u9401066/asset-aware-mcp/releases/tag/v1.4.0)
  是階段成果，跨格式總目標仍在進行。

## v1.3.0 已發布階段成果

- DOCX 原生版本已接到 DFM 讀寫：固定來源版本的分段讀取、完整區塊標記檢查、
  保留未修改 parts、舊版／跨文件／併發修改拒絕，以及獨立來源回寫。
- DOCX 元件引用驗證／wiki 匯出已接上：版本固定的區塊證據、完整表示與原始
  套件附件，保留舊快照；完整性檢查不等於語意或抽取完整性驗證。
- 仍未提供 DOCX 結構插刪、樣式設計；其他格式的原生編輯、學術引用引擎
  及完整 Agent 核對流程仍在範圍內。PPTX 的後續進展見 1.4.0。

## v1.2.0 已發布成果

- 原生 cell 引用可核對不可變版本、定位與完整表示 hash；舊引用在更新／封存後仍可驗證。
- 原生 wiki 快照匯出與人工修改保護已實作：固定版本的 wikilink、來源附件、完整
  cell reference 與自訂引用格式。PDF bundle 也補上人工修改偵測與保留備份。

## v1.1.0 階段成果

- 原生檔案 registry：固定 ID、不可變版本、能力與來源狀態；其他格式可先保留原始內容。
- XLSX 建立、XLSX/XLSM cells 讀取／分段讀取／typed update／清空、歷史、
  明確回寫、外部修改 refresh、保留歷史的 archive。格式限制與 Agent 核對仍明確保留。
- 尚未完成工作表／列欄結構 CRUD、A2T 橋接或視覺核對自動化；原生 wiki
  引用已於 1.2.0 提供。以上子項進展不代表跨格式總目標完成。

## 已完成

### v1.0.1 — PDF/Codex/網站 hardening

- 大型 PDF worker 使用 private、atomic、bounded MessagePack result channel，
  text、table、figure、caption 與 audit 路徑都具有限時、容量與失敗隔離。
- MCP SDK 2 public responses 有一致的 `TextContent` 上限；長 citation 只回
  non-canonical preview，完整 exact quote/hash/range 保存在 citation 或
  agent-asset bundle。
- `document(op="export_assets")` 產出 deterministic records、media、citation
  inventory 與可攜式 Foam wiki，並保護來源目錄、來源 hash 和 staging 邊界。
- VS Code extension 對 Codex/Cline/Copilot 採 trusted-workspace 與
  version-pinned production launch；Codex TOML merge 保留自訂 policy、nested
  tool tables、comments 與 recoverable concurrent snapshots，且不持久化 secret
  values。
- GitHub Pages 改為雙語 Evidence Rail 產品站，包含真實 30-tool explorer、
  PDF/DOCX 分流、安裝、開發與 release gates；移除含舊 metrics、私有路徑或
  不再支援 backend 的 raster diagrams。
- 真實 MCP SDK 2 stdio 測試涵蓋 PDF preflight、text/table/large figure、
  canonical citation、bounded preview、Foam bundle、deterministic re-export 與
  source immutability。

### v1.0.0 — MCP SDK 2 與 reusable asset foundation

- Python MCP SDK `>=2,<3` / `MCPServer` breaking migration；不保留 v1 fallback。
- PDF preflight 與 page-level native/OCR/structured route 建議。
- citation-ready agent asset bundle 與 Foam-compatible LLM wiki subtree。
- mixed-format ingest、DOCX/DFM reversible edit、A2T tables、structural retrieval、
  LightRAG adapter 與 30-tool balanced public surface。
- Python、npm、Actions、artifact、Docker、VSIX 與三平台 smoke release gates。

## 現行產品原則

1. **Evidence before prose**：每個 claim 必須能回到 source identity、locator、
   exact quote/hash 與 surrounding context；preview 不冒充 canonical reference。
2. **Persisted assets are portable**：bundle 不依賴原機絕對路徑，Foam links、
   notes、media 與 manifest 可整棵搬移。
3. **Source files are immutable by default**：PDF ingest/export 不改來源；DOCX
   write-back 必須經 stale/session guard 並保留可逆工作流。
4. **Bound every untrusted dimension**：頁數、records、spans、worker time、IPC
   bytes、MCP response、輸出 bundle 與 filesystem traversal 都要有 fail-closed
   邊界。
5. **One public contract**：balanced surface、網站 tool explorer、README、Wiki、
   VSIX bundled assets、CI 與 release artifacts 從同一份 source contract 驗證。
6. **No silent backend downgrade**：實際 `source_engine` 必須留在 provenance；
   held/unavailable backend 要有明確診斷，不能偽裝成成功的 structured parse。

## 下一階段

### Agent 證據核對

- 完整來源定位讀回已在 main 實作為 `table_cite read`，保留原有 `get` 摘要。
  下一步補齊穩定 row ID 操作的結果顯示（目前部分訊息顯示未解析的 -1 索引），
  以及跨格式表格／原生檔案橋接，讓 Agent 核對實際修改目標與輸出。
- 擴充真實掃描／複雜表格 corpus，分別記錄初次轉錄、Agent 修正及最終
  artifact 稽核結果；MCP 的機械完整性檢查與語意／視覺核對維持明確分工。

### 1. PDF preflight router 與 structured extraction

- 將 `pdf-preflight-v1` 的 page classification/OCR reasons 接到明確、可觀察的
  route policy，而不是讓 caller 猜 backend。
- 在上游 `pdf-inspector` 發布包含最新 expansion/memory hardening 的正式版本後，
  以隔離 adapter、contract tests 與 opt-in rollout 評估導入；不直接依賴目前
  registry 尚未包含 hardening 的 build。
- 擴充 mixed-layout、rotated cropbox、CID font、cross-page table、formula 和
  scanned-page golden corpus，所有 golden 都要保存 license/source hash。

### 2. Multi-document agent asset registry

- 建立跨 document 的 read-only asset index，支援按 source kind、section、table、
  figure、citation readiness 與 content hash 查詢。
- bundle composition 以既有 `agent-asset-bundle-v1` 為基礎，不另造不相容的
  locator/citation schema。
- 提供 manifest-level diff 與 incremental rebuild；任何 stale citation index
  都必須 rebuild/verify 後才能標示 citation-ready。

### 3. Foam / LLM wiki curation

- 將 deterministic per-document Foam subtree 延伸為可選的 multi-document hub，
  但保持 source notes 與人工策展 notes ownership 分離。
- 增加 broken-link、orphan-note、duplicate source、media hash 與 portable-path
  audit；不讓自動生成內容覆寫人工筆記。
- LightRAG/KG 僅消費已驗證 assets；模型生成摘要必須與 evidence refs 分層。

### 4. DOCX/DFM fidelity

- 擴充 tracked changes、nested/merged tables、hyperlinks、numbering、headers、
  footers、bookmarks 與 section properties 的真實 golden corpus。
- 將 binary/semantic/visual 3-cycle fidelity 納入可重現 gate，並清楚標示尚未
  支援的 Word feature，而不是默默正規化。

### 5. Operations and ecosystem

- 持續 weekly `uv`、npm 與 GitHub Actions dependency updates；任何 optional
  extra 若卡住安全修補版本，維持 security hold 而非放寬 gate。
- 補上 release artifact SBOM/provenance 消費端驗證與 published-package 真實
  PDF smoke，維持 tag-first、PyPI → Marketplace → GitHub Release 順序。
- 評估 MCP registry/awesome-list 登錄、使用案例與短篇 demo；對外宣稱必須由
  當期 release artifact 與可重跑測試支持。

## Backend 狀態

| Engine | 狀態 | 用途 |
|---|---|---|
| PyMuPDF | active/default | 快速 native text、figure、table baseline |
| PyMuPDF4LLM | active optional | 輕量 layout-aware Markdown |
| Docling | active optional | 隔離 structured layout/table/formula pipeline |
| MinerU | security hold | 上游 `transformers<5` cap 尚不能滿足安全 floor |
| Marker | security hold | 上游 `Pillow<11` cap 尚不能滿足安全 floor |

## Release definition of done

- focused regressions 與完整 Python/VSIX suites 全綠；Ruff、format、MyPy、
  Bandit、uv/npm audit、actionlint、zizmor 與 docs exact-build gate 全綠。
- MCP SDK 2 true-stdio、真實 PDF asset/Foam、built-wheel、Docker、三平台 VSIX
  install/activation smoke 全綠。
- `main` 與 `origin/main` 一致、worktree clean、annotated tag 指向受保護 main
  commit；PyPI、Marketplace、GitHub Release checksums 可交叉驗證。
- README、GitHub Pages、Wiki、repository description/topics、labels、bundled
  assistant assets 與 Memory Bank 同步；任何過時或含私有資訊的公開素材已移除。

完整設計決策見 [memory-bank/decisionLog.md](memory-bank/decisionLog.md)，操作與
gate 詳見 [docs/wiki/Release-And-Testing.md](docs/wiki/Release-And-Testing.md)。
