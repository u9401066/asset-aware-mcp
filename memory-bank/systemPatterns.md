# System Patterns

> 📌 此檔案記錄專案中使用的模式和慣例，新模式出現時更新。

## 🏗️ 架構模式

### DDD 分層架構
```
Presentation → Application → Domain ← Infrastructure
```
- Domain 層不依賴任何外層
- Repository Pattern 為唯一資料存取方式

### 憲法-子法層級
```
CONSTITUTION.md (最高原則)
  └── .github/bylaws/ (子法)
        └── .claude/skills/ (實施細則)
```

## 🛠️ 設計模式

### Repository Pattern
- 介面在 Domain 層定義
- 實作在 Infrastructure 層

### Strategy Pattern
- 用於取代複雜條件判斷
- 實例：ShippingStrategy, PaymentStrategy

### Command Pattern (CQRS)
- Commands: 寫入操作
- Queries: 讀取操作

### DFM Bridge Pattern (Docx ↔ A2T)
- **DfmTableBridge** 橋接 Docx 子系統與 A2T 子系統
- `docx_table_to_context` — 從 DocxIR 表格提取 headers + rows → A2T context
- `docx_table_from_context` — 從 A2T TableAsset 反向寫入 DocxIR
- 兩方向都保留型別安全（不直接耦合兩個 domain）

### Template-Based Rebuild Pattern (Docx)
- `ir_to_docx()` 複製原始 .docx ZIP 為模板
- 僅修改 `word/document.xml`
- 所有 media/styles/theme/fonts 由原檔保留 → 非文字保真率極高

### Intermediate Representation Pattern (DocxIR)
- docx → DocxIR → DFM → Agent 編輯 → DFM → DocxIR → docx
- IR 保留：preserved_parts, assets, styles, runs, checksum
- DFM 是人/Agent 可讀的 Markdown 視圖

### Multi-Dimensional Validation Pattern (DocxValidator)
- 6 個獨立維度比較（結構/文字/格式/表格/媒體/樣式）
- 每維度 0–100 分 + 加權總分
- 產出 Agent 可讀 Markdown 報告（emoji 等級）

## 業務流程模式

### A2T 2.0 (Anything to Table) 工作流
1. **Plan**: `plan_table_schema` - AI 驅動的結構發想。
2. **Draft**: `create_table_draft` - 建立持久化草稿，支援斷點續作。
3. **Batch Add**: `add_rows_to_draft` - 分批寫入數據，優化 Token 使用。
4. **Commit**: `commit_draft_to_table` - 正式轉檔為 JSON/MD/XLSX。

### Asset-Aware ETL 模式
1. **Extract**: 使用 PyMuPDF 提取原始 Markdown 與圖片。
2. **Parse**: 識別表格、章節與圖片位置。
3. **Manifest**: 生成結構化清單供 Agent 導航。
4. **Index**: 注入 LightRAG 建立知識圖譜。

## 命名慣例

| 類型 | 慣例 | 範例 |
|------|------|------|
| Entity | 名詞單數 | `User`, `Order` |
| Value Object | 描述性名詞 | `Email`, `Money` |
| Repository | `I{Entity}Repository` | `IUserRepository` |
| Use Case | 動詞 + 名詞 | `CreateOrder` |
| Domain Event | 過去式 | `OrderCreated` |

## 📚 程式碼慣例

### Python
- 使用 `snake_case` 命名
- 檔案名全小寫
- 類別使用 `PascalCase`
- 優先使用 type hints

### 測試
- 測試檔案以 `test_` 開頭
- 測試類別以 `Test` 開頭
- 使用 pytest markers 分類

---
*Last updated: 2025-12-15*
