# Docs IA And UX Spec

這是給維護者與開發者使用的產品網站規格，不是一般使用者流程頁。它定義
GitHub Pages 的 Evidence Rail landing、內嵌文件 reader、資訊架構、完整性規則與
上線檢查。首頁負責說清楚價值、工作流、30-tool surface、安裝與開發 guardrails；
詳細 contract 則留在由 `docs/wiki/**` 生成的 reader，兩者共用同一份 runtime stats。

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

網站分成兩個可互相導回的層次：

1. **Evidence Rail landing**：產品定位、PDF／DOCX 分流、六步證據工作流、能力圖、
   30-tool explorer、安裝路徑、開發與發布規則，以及 GitHub／Releases／Issues 導流。
2. **Documentation reader**：以 hash route 開啟 canonical wiki 內容，保留篩選、
   sticky 導覽、page outline、語系與回首頁連結。

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
| Product header | 首頁快速前往產品、流程、功能、工具、文件與 GitHub | 第一屏就能理解產品並採取下一步 |
| Evidence Rail | 具體呈現 source → extract → verify → assets → Foam | 讓 provenance 成為主視覺，不使用泛用裝飾圖 |
| 30-tool explorer | 依任務分類、搜尋與查看 operation contract | 讓使用者不必從完整 API 表猜入口 |
| Sticky reader 導覽 | 穩定跨頁定位 | 文件頁多，讀者需要持續知道自己在哪個區塊 |
| 搜尋/篩選輸入 | 快速縮小頁面 | 比展開多層樹更適合目前文件站規模 |
| 語言切換 | 中英文入口 | 目前繁中為主要閱讀模式，英文保留給外部使用者 |
| 頁內 outline | 長頁快速跳轉 | MCP tools、code map、workflow 頁都會偏長 |
| GitHub action band | 導向程式碼、release、issue 與 developer guide | 所有產品說明都能回到可稽核來源 |
| Restrained borders | 保留工程工具感 | 卡片只用於真正的群組與互動，不把每段文字包成浮動容器 |

## 視覺方向

這個站採用清爽、偏 editorial 的 developer-product 風格：

- 真白／極淺灰底、深 ink 文字、teal action 與少量 amber verify state。
- 不使用漸層；流程線、grid 與 locator console 以純色、border、SVG／CSS 建構。
- Hero 不使用獨立 eyebrow／pill 標題；產品名稱、主標、說明與 CTA 直接建立層級。
- Landing 的示意資料必須標成 demo，不能把 sample count/hash 假裝成 benchmark。
- PDF 才能走 `document(op="preflight")`；DOCX 必須明示走 DFM ingest 分支。
- 不以 JPG 截圖保存 tool count、引擎狀態、IP 或本機路徑；架構圖優先用
  machine-readable Mermaid 或 code-native HTML/CSS/SVG。

## 完整性定義

「完整」在這個站不是每頁都塞滿細節，而是：

- 所有公開 MCP tools/resources 有完整 reference。
- 每條主要人類任務都有 workflow 頁。
- 每個 workflow 都能連回 Tool Chooser、tool/resource reference、code map 或 release check。
- Citation、LLM wiki、KG 的分工必須明確：verified evidence 先行，wiki 負責呈現，KG 只做 opt-in discovery。
- public tool 數字由 `src/presentation/tool_surface.py` 的 balanced surface 產生；resource 數字由 `scripts/build_docs_site.py` 解析 `src/presentation/resources/**` 的註冊 decorator 產生。
- 網站 payload 由 `scripts/build_docs_site.py` 從 `docs/wiki/**` 生成，CI 用 `--check` 防止漂移。
- Landing 的版本、工具數與 endpoint 數必須讀取同一份生成的 `DOC_STATS`，不可
  在 HTML 或 JavaScript 另寫一份 release number。
- 所有 install／footer／產品 CTA 都要能導回 GitHub repository；另提供 Releases、
  Issues、PyPI 與 VS Marketplace 的明確外部連結。
- 大型 evidence span 的公開回應必須說明 bounded preview 與 persisted canonical
  AssetRef 的差異，不能把截斷 quote 說成可驗證 ref。

## 品質檢查

文件站每次更新都要通過這些檢查：

| 面向 | 上線標準 |
|---|---|
| Code alignment | 版本、工具數、resource 數、預設模型與 feature flag 必須和 `pyproject.toml`、`src/infrastructure/config.py`、`vscode-extension/src/defaults.ts` 一致 |
| Content coverage | Landing 的流程、功能、30 tools、安裝、開發注意事項、GitHub，以及 reader 的 VSIX、PDF、sections、DOCX/DFM、citation、LLM wiki、KG、jobs、ETL、developer、release、MCP reference 都要有入口 |
| Task clarity | 每個 workflow 頁要先回答「何時用、主要工具、輸出是什麼」，再進入細節 |
| Safety defaults | Marker security hold、LightRAG opt-in、CPU-only Ollama fallback、citation evidence layer 都不能被隱藏 |
| UX/UI | 第一屏要能直接開始或開 GitHub；tool explorer 可鍵盤操作；reader 導覽可篩選；長頁有 outline；mobile 無不必要橫向捲動 |
| Browser QA | Browser 外掛可用時優先使用；否則記錄原因並以 Playwright 驗 desktop/mobile、路由、搜尋、複製、語言、console、screenshot 與 axe-core accessibility scan |
| Visual fidelity | 對 concept 與實際 screenshot 至少比較 hero 層級、Evidence Rail、workflow、tool explorer、engineering/release 與 mobile reader 六點 |
| Regression | `scripts/build_docs_site.py --check`、docs reference sync、public docs hygiene、mojibake／舊 metrics／retired raster 檢查都要通過 |

## 產品化 Shell 規格

- 首屏必須在不閱讀長文的情況下回答：產品做什麼、source 如何成為 reusable asset、
  現在的 SDK/tool/default backend，以及下一步是開始使用或開 GitHub。
- Evidence Rail 清楚分開 PDF preflight 與 DOCX/DFM ingest，並將 demo count/hash 標示
  為示意；不能宣稱一份固定樣本代表效能或品質基準。
- Tool explorer 必須涵蓋 balanced surface 的 30 個名稱，依文件、citation、DOCX/DFM、
  A2T、jobs/conversion、knowledge/profile 分組，提供搜尋、selection 與 example。
- Sidebar 只在 reader 模式出現；mobile 透過 drawer 開合，內容區保留 sticky outline。
- `site.js` 統一 landing/reader route、語系、copy、tool explorer 與 mobile state；
  內容頁由 `docs/wiki/**` 生成，避免一頁一套文件真相。
- 靜態 HTML 具備 SEO／分享基本資料、skip link、明確 viewport、可理解的 noscript
  fallback 與穩定 cache bust query；不使用已刪除的 raster 當 Open Graph 圖。
- Reader 對 Markdown table 加上鍵盤可聚焦的水平捲動邊界；不允許 table、code
  或 sidebar 讓 390px viewport 產生整頁水平溢位。Mobile header 的選單按鈕必須以
  真實 pointer click 驗證，不能只檢查元素存在。

## 後續可深化

- MCP Tools 頁可再加 task-oriented quick lookup，讓人不用在完整表格中找入口。
- 若之後圖更多，可加圖片索引頁，集中說明每張圖對應哪條 workflow。
- 可以加入「上線前文件檢查」頁，把本頁品質標準變成 release checklist 的人類版。
