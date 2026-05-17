# Docs IA And UX Spec

這是給維護者與開發者使用的文件站規格，不是一般使用者流程頁。它定義
GitHub Pages 站台的資訊架構、頁面節奏、完整性規則與上線檢查，避免首頁再次變成
過長的功能清單，或把 PDF、DOCX、citation、KG、release 流程混在同一條敘事裡。

## 目標讀者

| 讀者 | 主要問題 | 對應設計 |
|---|---|---|
| 第一次安裝的人 | 我要怎麼跑起來？ | `Start Here` 分組、首頁任務卡、VSIX/MCP setup 頁 |
| 使用者 / Agent operator | 我要用哪個工具完成 PDF、DOCX、表格或 KG 任務？ | `Workflows` 分組、每頁用「何時使用 / 主要入口 / 輸出」描述 |
| 證據審查者 | claim、wiki note、KG answer 是否可回查來源？ | `Evidence & Knowledge` 分組，先看 citation，再看 LLM wiki，最後才看 KG discovery |
| 維運 / 上線者 | 長任務、ETL、release gate 怎麼跑？ | `Operations` 分組，集中 background jobs、ETL profiles、Release And Testing |
| 查 API surface 的人 | 目前到底有哪些 tools/resources？ | `Reference` 分組、完整工具表與 resource URI contract |
| 維護者 | 功能在哪裡、測什麼、怎麼擴充？ | `Maintainers` 分組、Architecture、Code Map、Docs IA/UX spec |

## 資訊架構

左側導覽分成六層：

1. `Start Here`：總覽、安裝、VS Code extension、流程章節地圖。
2. `Document Workflows`：PDF、document sections、DOCX/DFM、A2T table。
3. `Evidence & Knowledge`：Citation Provenance、LLM Wiki Knowledge Base、Knowledge Graph。
4. `Operations`：Background Jobs、ETL Profiles、Release And Testing。
5. `Reference`：Tool Chooser、完整 MCP tools/resources。
6. `Maintainers`：架構、git harness hygiene、developer guide、tool consolidation、code map、docs IA/UX spec。

這個排序刻意把「任務」、「證據」、「維運」放在「完整 API 表」之前，因為網站主要給人讀，不是讓人從 balanced 30 個 tool name 開始猜。LLM wiki 是 presentation/synthesis layer，應排在 evidence 之後、KG discovery 之前；KG 不應被描述成唯一引用來源。

## 頁面節奏

每個主要頁面應維持同一種閱讀節奏：

- 先說這頁解決什麼問題。
- 再列出何時使用、主要工具、輸入與輸出。
- 再補流程、注意事項、驗證方式。
- 最後才放完整表格或程式碼位置。

Reference 頁可以 dense；workflow 頁不要一開始就把所有參數攤開。

## UI 取捨

| 元件 | 用途 | 原因 |
|---|---|---|
| Sticky 左側導覽 | 穩定跨頁定位 | 文件頁多，讀者需要持續知道自己在哪個區塊 |
| 搜尋/篩選輸入 | 快速縮小頁面 | 比展開多層樹更適合目前文件站規模 |
| 語言切換 | 中英文入口 | 目前繁中為主要閱讀模式，英文保留給外部使用者 |
| 首頁任務卡 | 把技術 surface 轉成使用者任務 | 讓讀者先選情境，而不是先看工具名稱 |
| 頁內 outline | 長頁快速跳轉 | MCP tools、code map、workflow 頁都會偏長 |
| 8px radius / restrained borders | 工具型文件感 | 避免 marketing landing page 感，保留掃描效率 |

## 視覺方向

這個站採用清爽的文件產品風格：

- 淺灰藍底色搭配白色內容區，避免整站被單一米色或單一綠色支配。
- Teal 作為主要 action / active state，slate-blue 作為次要強調色。
- 文字密度偏高，但用任務卡、表格 wrapper、outline 降低掃描成本。
- 所有卡片維持 8px radius，避免過度裝飾化。

## 完整性定義

「完整」在這個站不是每頁都塞滿細節，而是：

- 所有公開 MCP tools/resources 有完整 reference。
- 每條主要人類任務都有 workflow 頁。
- 每個 workflow 都能連回 Tool Chooser、tool/resource reference、code map 或 release check。
- Citation、LLM wiki、KG 的分工必須明確：verified evidence 先行，wiki 負責呈現，KG 只做 opt-in discovery。
- public tool 數字由 `src/presentation/tool_surface.py` 的 balanced surface 產生；resource 數字由 `scripts/build_docs_site.py` 解析 `src/presentation/resources/**` 的註冊 decorator 產生。
- 網站 payload 由 `scripts/build_docs_site.py` 從 `docs/wiki/**` 生成，CI 用 `--check` 防止漂移。

## 品質檢查

文件站每次更新都要通過這些檢查：

| 面向 | 上線標準 |
|---|---|
| Code alignment | 版本、工具數、resource 數、預設模型與 feature flag 必須和 `pyproject.toml`、`src/infrastructure/config.py`、`vscode-extension/src/defaults.ts` 一致 |
| Content coverage | 首頁、安裝、VSIX、PDF、document sections、DOCX/DFM、citation、LLM wiki、KG、background jobs、ETL、developer、release、Tool Chooser、MCP reference 都要有入口 |
| Task clarity | 每個 workflow 頁要先回答「何時用、主要工具、輸出是什麼」，再進入細節 |
| Safety defaults | Marker security hold、LightRAG opt-in、CPU-only Ollama fallback、citation evidence layer 都不能被隱藏 |
| UX/UI | 第一屏要能直接選任務；左側導覽可篩選；長頁要有 outline；mobile 不應需要橫向捲動才能找到主內容 |
| Regression | `scripts/build_docs_site.py --check`、docs reference sync test、mojibake/舊 metrics 檢查都要通過 |

## 產品化 Shell 規格

- 首屏必須在不閱讀長文的情況下回答三件事：這是什麼、現在有哪些 endpoint、下一步去哪裡。
- Quick actions 只放高頻入口：安裝、文件工作流、KG/RAG、上線檢查；詳細章節不在每個葉面重複露出。
- Status strip 固定顯示 runtime safety posture：版本、PDF backend、RAG default、KG opt-in、release gates。
- Sidebar 是主要導覽，mobile 透過選單開合；內容區保留 sticky outline，讓長 reference 頁可掃描。
- Shell 文字由 `site.js` 統一語系化；內容頁由 `docs/wiki/**` 生成，避免一頁一套翻譯。
- 靜態 HTML 需要具備 SEO/分享基本資料、skip link、明確 viewport、穩定 cache bust query。

## 後續可深化

- MCP Tools 頁可再加 task-oriented quick lookup，讓人不用在完整表格中找入口。
- 若之後圖更多，可加圖片索引頁，集中說明每張圖對應哪條 workflow。
- 可以加入「上線前文件檢查」頁，把本頁品質標準變成 release checklist 的人類版。
