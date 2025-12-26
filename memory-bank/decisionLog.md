# Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-12-15 | 採用憲法-子法層級架構 | 類似 speckit 的規則層級，可擴展且清晰 |
| 2025-12-15 | DDD + DAL 獨立架構 | 業務邏輯與資料存取分離，提高可測試性 |
| 2025-12-15 | Skills 模組化拆分 | 單一職責，可組合使用，易於維護 |
| 2025-12-15 | Memory Bank 與操作綁定 | 確保專案記憶即時更新，不遺漏 |

---

## [2025-12-15] 採用憲法-子法層級架構

### 背景
需要一個清晰的規則層級系統，類似 speckit 但可擴展。

### 選項
1. 單一 copilot-instructions.md - 簡單但不夠靈活
2. 憲法 + 子法層級 - 清晰層級，可擴展
3. 全部放在 Skills 內 - 分散，難以管理

### 決定
採用選項 2：憲法-子法層級

### 理由
- 最高原則集中在 CONSTITUTION.md
- 細則可在 bylaws/ 擴展
- Skills 專注於操作程序
- 符合現實法律體系，易理解

### 影響
- 新增 CONSTITUTION.md
- 新增 .github/bylaws/ 目錄
- Skills 需引用相關法規
| 2025-12-26 | 使用 Ollama 作為預設 LLM 後端 | 1. 本地運行，無需 API Key 成本
2. 支援 qwen2.5:7b (LLM) 和 nomic-embed-text (Embedding)
3. 隱私保護，資料不離開本機
4. 仍保留 OpenAI 作為備選後端 |
| 2025-12-26 | Figure caption mapping 需要實作 - 目前 fig_{page}_{index} 命名未對應實際圖說 | 測試 Nobel Prize PDF 時發現 fig_2_1 實際對應 "Figure 1. Regulation of cell-type specific functions"，系統缺乏 caption 解析功能。未來版本應在 ETL 階段提取圖說文字，建立 asset_id 到 caption 的映射。 |
| 2025-12-26 | mcp-operator skill 必須明確警告：純文字 AI 無法分析 base64 圖片 | 測試時發現純文字 AI 會根據「標準知識」猜測圖片內容而非實際分析，導致錯誤答案。必須在 skill 中明確禁止這種行為，要求 agent 誠實告知使用者其視覺能力限制。 |
