# Design And UX Notes

這個文件站的目標不是展示技術名詞，而是讓人類在複雜功能裡快速找到下一步。完整性放在 reference 頁，首頁與工作流頁負責降低進入成本。

## 目標讀者

| 讀者 | 主要問題 | 對應設計 |
|---|---|---|
| 第一次安裝的人 | 我要怎麼跑起來？ | `Start Here` 分組、首頁任務卡、VSIX/MCP setup 頁 |
| 使用者 / Agent operator | 我要用哪個工具完成 PDF、DOCX、表格或 KG 任務？ | `Workflows` 分組、每頁用「何時使用 / 主要入口 / 輸出」描述 |
| 維護者 | 功能在哪裡、測什麼、怎麼發布？ | `For Developers` 分組、Code Map、Release And Testing |
| 查 API surface 的人 | 目前到底有哪些 tools/resources？ | `Reference` 分組、完整工具表與 resource URI contract |

## 資訊架構

左側導覽分成四層：

1. `Start Here`：總覽、安裝、VS Code extension、設計說明。
2. `Workflows`：PDF、DOCX/DFM、citation、A2T、knowledge graph、background jobs、ETL profile。
3. `For Developers`：架構、git harness hygiene、developer guide、release/testing、code map。
4. `Reference`：完整 MCP tools/resources。

這個排序刻意把「任務」放在「完整 API 表」之前，因為網站主要給人讀，不是讓人從 59 個 tool name 開始猜。

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
| 搜尋/篩選輸入 | 快速縮小頁面 | 比展開多層樹更適合目前 18 頁規模 |
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
- 每個 workflow 都能連回 tool、resource、code map 或 release check。
- tool/resource 數字由 `./scripts/count_tools.sh` 產生。
- 網站 payload 由 `scripts/build_docs_site.py` 從 `docs/wiki/**` 生成，CI 用 `--check` 防止漂移。

## 目前仍可改進

- 各 workflow 頁可再加入更具體的「最短成功路徑」範例。
- MCP Tools 頁可再拆出 task-oriented quick lookup，讓人不用在完整表格中找入口。
- 若之後圖更多，可加圖片索引頁，集中說明每張圖對應哪條 workflow。
