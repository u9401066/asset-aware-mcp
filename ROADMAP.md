# Roadmap

Asset-Aware MCP 的核心方向是把 PDF、DOCX/DFM、表格與圖片轉成可重用、
可驗證、可攜式的 agent assets，並以穩定 locator、hash、citation 與 Foam notes
支援 LLM wiki、知識圖譜和跨文件工作流。

正式版本、相依套件與安全狀態以 [CHANGELOG.md](CHANGELOG.md)、
[README.md](README.md) 和 release artifacts 為準；本頁只保留仍有效的方向，
不再把已完成的舊版工作列為「進行中」。

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
