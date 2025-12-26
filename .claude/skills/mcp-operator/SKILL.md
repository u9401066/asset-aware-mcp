```markdown
---
name: mcp-operator
description: Operate Asset-Aware MCP tools for document ingestion, asset retrieval, and knowledge graph queries. Triggers: MCP, ingest, manifest, fetch, 文獻, 圖片, 表格, knowledge graph, 知識圖譜.
---

# MCP 操作技能

## 描述
操作 Asset-Aware MCP 的各項工具，包含文件匯入、資產提取、知識圖譜查詢。

## 觸發條件
- 「ingest PDF」、「匯入文獻」、「新增文件」
- 「看 manifest」、「文件結構」、「有什麼圖表」
- 「取得圖片」、「fetch figure」、「拿表格」
- 「知識圖譜」、「cross-document」、「比較文獻」

---

## ⚠️ 重要警告

### � 視覺能力限制（最重要！）

> **純文字 AI 無法真正「看到」圖片內容！**
>
> 當 fetch 圖片返回 base64 時：
>
> | Agent 類型 | 能力 | 正確做法 |
> |-----------|------|----------|
> | **純文字 AI** | ❌ 無法分析圖片 | 誠實告知使用者，不要猜測 |
> | **Vision AI** | ✅ 可以分析圖片 | 直接描述圖片內容 |
>
> ⛔ **絕對禁止**：
> - 根據「標準知識」或「常識」猜測圖片內容
> - 假裝能看到圖片並編造細節
> - 用文件其他部分的文字推測圖片
>
> ✅ **正確做法（無視覺能力時）**：
> ```
> 「我已成功取得圖片 (fig_5_1)，但作為純文字 AI，
> 我無法分析 base64 圖片內容。
> 
> 建議方案：
> 1. 使用支援視覺的 AI（如 GPT-4V、Claude Vision）
> 2. 將圖片儲存後用圖片檢視器開啟
> 3. 參考文件中該圖的文字描述」
> ```

### �🖼️ 圖片 Context 限制

> **Base64 圖片非常大，一次只處理一張！**
>
> - 一張 1378×737 的圖片 ≈ 200KB base64 ≈ **~270K tokens**
> - 對話 context 有限，多張圖片會快速耗盡
> - **建議流程**：先 inspect manifest → 選定目標圖 → 一次 fetch 一張

### 📸 圖說對應問題（Known Issue）

> **目前圖片 ID 與實際圖說不對應**
>
> | 系統 ID | 實際圖說 |
> |---------|----------|
> | `fig_2_1` | Figure 1. Regulation of cell-type specific functions |
> | `fig_2_2` | Figure 2. Heterochronic worm mutants |
> | `fig_3_1` | Figure 3. Identification of two short lin-4 transcripts |
> | `fig_4_1` | Figure 4. Complementary sequence elements |
> | `fig_5_1` | Figure 5. Evolutionary conservation of let-7 |
>
> **原因**：系統以 `fig_{page}_{index}` 命名，而非解析圖說文字
>
> **TODO**：未來版本應解析圖說，建立 caption mapping

---

## 🔧 可用 MCP Tools

| Tool | 用途 | 參數 |
|------|------|------|
| `ingest_documents` | 匯入 PDF | `file_paths: list[str]` |
| `list_documents` | 列出所有文件 | 無 |
| `inspect_document_manifest` | 查看文件結構 | `doc_id: str` |
| `fetch_document_asset` | 取得資產 | `doc_id`, `asset_type`, `asset_id` |
| `consult_knowledge_graph` | 知識圖譜查詢 | `query`, `mode` |

---

## 📋 標準操作流程

### 1️⃣ 文件匯入

```
使用者：「幫我匯入這份 PDF」

步驟：
1. 取得 PDF 絕對路徑
2. 呼叫 ingest_documents
3. 確認處理結果（頁數、圖片數、表格數）
4. 提供 doc_id 供後續使用
```

**範例呼叫**：
```python
ingest_documents(file_paths=["C:/papers/study.pdf"])
```

**預期輸出**：
```
Successfully ingested: study.pdf
- doc_id: doc_study_abc123
- Pages: 10
- Figures: 5
- Tables: 3
- Processing time: 25.3s
```

### 2️⃣ 查看文件結構

```
使用者：「這份文件有什麼圖表？」

步驟：
1. 呼叫 inspect_document_manifest
2. 列出所有 figures/tables/sections
3. 說明每個資產的 ID、位置、尺寸
```

**範例呼叫**：
```python
inspect_document_manifest(doc_id="doc_study_abc123")
```

**應回報**：
- 文件標題
- 頁數
- 圖片清單（ID、頁碼、尺寸）
- 表格清單（ID、描述）
- 章節清單（ID、標題）

### 3️⃣ 取得特定資產

#### 取得圖片（⚠️ 一次一張）

```
使用者：「給我 Figure 3」

步驟：
1. 從 manifest 找對應 asset_id
2. 呼叫 fetch_document_asset
3. 圖片以 base64 返回
4. ⚠️ 提醒使用者 context 限制
```

**範例呼叫**：
```python
fetch_document_asset(
    doc_id="doc_study_abc123",
    asset_type="figure",
    asset_id="fig_3_1"
)
```

**回報格式**：
```
📷 Figure: fig_3_1
- Page: 3
- Size: 811×451
- Format: PNG (base64)
- ⚠️ 圖片已載入，context 使用量較大
```

#### 取得表格

```python
fetch_document_asset(
    doc_id="doc_study_abc123",
    asset_type="table",
    asset_id="tab_1"
)
```

#### 取得章節

```python
fetch_document_asset(
    doc_id="doc_study_abc123",
    asset_type="section",
    asset_id="sec_methods"
)
```

#### 取得全文

```python
fetch_document_asset(
    doc_id="doc_study_abc123",
    asset_type="full_text",
    asset_id="full"
)
```

### 4️⃣ 知識圖譜查詢

```
使用者：「比較這兩篇文獻的發現」

步驟：
1. 確認文件已 ingest 且已建立索引
2. 選擇查詢模式
3. 呼叫 consult_knowledge_graph
```

**查詢模式**：

| Mode | 用途 | 適合場景 |
|------|------|----------|
| `local` | 細節查詢 | 特定藥物劑量、具體數據 |
| `global` | 全局模式 | 跨文獻趨勢、主題歸納 |
| `hybrid` | 混合模式（推薦） | 一般問答 |

**範例呼叫**：
```python
consult_knowledge_graph(
    query="What are the main findings about microRNA regulation?",
    mode="hybrid"
)
```

---

## 🎯 情境範例

### 情境 A：分析新論文

```
使用者：「幫我分析這份 PDF」

執行流程：
1. ingest_documents → 取得 doc_id
2. inspect_document_manifest → 了解結構
3. fetch section (Introduction/Methods) → 快速瀏覽
4. 根據需要 fetch 特定圖表
5. consult_knowledge_graph → 整合分析
```

### 情境 B：跨文獻比較

```
使用者：「比較 A 和 B 論文的結論」

執行流程：
1. 確認兩份文件都已 ingest
2. consult_knowledge_graph(mode="global")
3. 必要時 fetch 關鍵圖表佐證
```

### 情境 C：精準資料提取

```
使用者：「給我 Table 2 的數據」

執行流程：
1. inspect_manifest → 找到 tab_2 的 ID
2. fetch_document_asset(asset_type="table", asset_id="tab_2")
3. 返回 Markdown 格式表格
```

---

## ⚡ 效能考量

### Context 預算

| 資產類型 | 大約 Token 數 |
|----------|--------------|
| Section (1頁) | ~500-1000 |
| Table | ~200-500 |
| Figure (base64) | ~200K-500K ⚠️ |
| Full text (10頁) | ~10K-20K |

### 建議策略

1. **先 manifest，後 fetch** - 不要盲目抓所有資產
2. **Section 優先** - 文字比圖片省 context
3. **一次一張圖** - 避免 context 爆炸
4. **善用 knowledge graph** - 跨文獻資訊整合

---

## 🐛 已知限制

### 1. 圖說映射缺失
- 系統用 `fig_{page}_{index}` 命名
- 未解析實際 Figure X 標題
- **Workaround**：手動對照 manifest 頁碼

### 2. Knowledge Graph 延遲
- LightRAG 索引需要時間
- 首次查詢可能返回空結果
- **Workaround**：等待幾分鐘後重試

### 3. 複雜表格解析
- 合併儲存格可能解析錯誤
- 多層表頭支援有限
- **Workaround**：取得原始圖片輔助

---

## 📊 輸出格式

操作 MCP 後，應以清晰格式回報：

```markdown
## MCP 操作結果

### 📄 文件資訊
- **doc_id**: doc_xxx_yyy
- **標題**: [文件標題]
- **頁數**: X 頁

### 📊 資產清單
| 類型 | ID | 位置 | 說明 |
|------|-----|------|------|
| Figure | fig_2_1 | P.2 | (需手動對照圖說) |
| Table | tab_1 | P.5 | Comparison results |

### ⚠️ 注意事項
- 圖片取得會消耗大量 context
- 建議一次處理一張圖片
```
```
