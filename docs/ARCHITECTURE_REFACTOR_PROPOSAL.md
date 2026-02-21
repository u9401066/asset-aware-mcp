# 🏗️ 架構重構提案：三大功能獨立化

> **問題**：做表、拆解文本、重送資料三個功能目前存在不必要的耦合
>
> **目標**：讓這三個功能完全獨立，互不影響

---

## 🔴 當前問題分析

### 問題 1：做表功能被迫依賴 PDF 拆解

```
現況：
┌─────────┐     ┌──────────────┐     ┌─────────────┐
│  User   │ ──► │ ingest_pdf() │ ──► │ create_table│
│ 想做表  │     │ （被迫執行）   │     │  （才能開始）│
└─────────┘     └──────────────┘     └─────────────┘

問題：
- 用戶已經有 MD 檔案，但無法直接使用
- TableService 只能從「已拆解的文檔」中抽取
- 沒有「直接讀取 MD/TXT 內容」的入口
```

### 問題 2：圖片需要重複拆解

```
現況：
Session 1: PDF → 拆解 → images/fig_3_1.png ✅ 已存在
Session 2: 想用 fig_3_1.png → ❌ 要重新拆解 PDF？

問題：
- 圖片已經持久化在 data/doc_XXX/images/
- 但 AssetService 只能從「當前 session 的 manifest」讀取
- 缺少「資產索引層」來追蹤所有已存在的資產
```

### 問題 3：重送資料需要完整上下文

```
現況：
- resume_table() 返回結構 + 最後 2 行
- 但無法「只送特定圖片」或「只送特定章節」
- 沒有「資產快取層」讓 Agent 按需獲取
```

---

## 🟢 重構方案：Asset-Centric Architecture

### 核心理念：**資產優先，流程解耦**

```
┌─────────────────────────────────────────────────────────────────┐
│                     Asset Index Layer (NEW)                     │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│   │  MD Files   │  │   Images    │  │   Tables    │            │
│   │  (已存在)    │  │  (已存在)    │  │  (已存在)    │            │
│   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘            │
│          │                │                │                    │
│          ▼                ▼                ▼                    │
│   ┌──────────────────────────────────────────────┐             │
│   │           Asset Registry (NEW)               │             │
│   │  - 掃描 data/ 目錄建立索引                     │             │
│   │  - 追蹤所有已存在的資產                        │             │
│   │  - 不需要重新拆解就能使用                      │             │
│   └──────────────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
    │   Table     │    │   ETL       │    │   Asset     │
    │   Service   │    │   Service   │    │   Delivery  │
    │  (做表)      │    │  (拆解)     │    │   (重送)    │
    └─────────────┘    └─────────────┘    └─────────────┘
          │                    │                    │
          └────────────────────┴────────────────────┘
                               │
                         獨立運作，互不干擾
```

---

## 📋 具體改動

### 1. 新增 Asset Registry（資產註冊中心）

```python
# src/domain/asset_registry.py (NEW)

class AssetRegistry:
    """
    掃描並索引所有已存在的資產。
    啟動時自動載入，不需要重新拆解 PDF。
    """

    def scan_all_assets(self) -> dict[str, Asset]:
        """掃描 data/ 目錄，建立資產索引"""
        pass

    def get_image(self, asset_id: str) -> bytes:
        """直接讀取已存在的圖片"""
        pass

    def get_markdown(self, doc_id: str) -> str:
        """直接讀取已存在的 MD 文件"""
        pass

    def list_available_assets(self) -> list[AssetSummary]:
        """列出所有可用資產（不需要重新拆解）"""
        pass
```

### 2. 改造 TableService：支援直接輸入

```python
# src/application/table_service.py (MODIFY)

class TableService:
    def create_table_from_text(
        self,
        text_content: str,  # 直接接受文字內容！
        intent: str,
        title: str,
        columns: list[dict],
    ) -> str:
        """
        直接從文字內容建立表格。
        不需要先拆解 PDF！
        """
        pass

    def create_table_from_files(
        self,
        file_paths: list[str],  # 接受任意 MD/TXT 檔案路徑
        ...
    ) -> str:
        """
        從現有的 MD 檔案建立表格。
        支援多檔案合併彙整！
        """
        pass
```

### 3. 新增 MCP Tools

```python
# 新工具 1: 直接使用已存在的資產
@mcp.tool()
async def list_available_assets() -> str:
    """
    列出所有已存在的資產（圖片、MD、表格）。
    不需要重新拆解 PDF！
    """
    pass

# 新工具 2: 直接讀取圖片
@mcp.tool()
async def get_existing_image(asset_path: str) -> ImageContent:
    """
    直接讀取已存在的圖片檔案。
    支援絕對路徑或 data/ 相對路徑。
    """
    pass

# 新工具 3: 從任意 MD 建表
@mcp.tool()
async def create_table_from_markdown(
    markdown_paths: list[str],  # 直接指定 MD 檔案
    intent: str,
    title: str,
    columns: list[dict],
) -> str:
    """
    從現有的 Markdown 檔案建立表格。
    不需要先拆解 PDF！支援多檔案彙整。
    """
    pass

# 新工具 4: 直接輸入文字做表
@mcp.tool()
async def create_table_from_text(
    text_content: str,  # 直接貼上文字內容
    intent: str,
    title: str,
    columns: list[dict],
) -> str:
    """
    直接從文字內容建立表格。
    適合從聊天中貼上內容直接做表。
    """
    pass
```

---

## 🔄 新工作流程

### 做表流程（獨立）

```
方式 A: 從已拆解的文檔
list_documents() → get_section_content() → add_rows()

方式 B: 從現有 MD 檔案 (NEW!)
list_available_assets() → create_table_from_markdown([paths])

方式 C: 直接輸入文字 (NEW!)
create_table_from_text(text_content, ...)
```

### 拆解流程（獨立）

```
ingest_documents([pdf_paths])
  → 非同步 Job
  → 產生 manifest + images + markdown
  → 自動註冊到 Asset Registry
```

### 重送資料流程（獨立）

```
方式 A: 送表格
resume_table(table_id) → 結構 + 最後 2 行

方式 B: 送圖片 (NEW!)
get_existing_image("data/doc_XXX/images/fig_3_1.png")

方式 C: 送章節
get_section_content(doc_id, section_id)

方式 D: 送多資產組合 (NEW!)
get_asset_bundle([
    {"type": "image", "path": "..."},
    {"type": "section", "id": "..."},
    {"type": "table", "id": "..."},
])
```

---

## 📊 改動範圍

| 層級 | 檔案 | 改動 |
|------|------|------|
| **Domain** | `asset_registry.py` (NEW) | 資產索引核心邏輯 |
| **Domain** | `entities.py` | 新增 `AssetSummary` 實體 |
| **Application** | `table_service.py` | 新增 `create_table_from_*` 方法 |
| **Application** | `asset_service.py` | 整合 AssetRegistry |
| **Infrastructure** | `file_storage.py` | 新增資產掃描功能 |
| **Presentation** | `server.py` | 新增 4 個 MCP Tools |

---

## ⏱️ 實施順序

### Phase 1: Asset Registry（核心）
1. 建立 `AssetRegistry` 類別
2. 實作資產掃描功能
3. 啟動時自動載入索引

### Phase 2: Table Service 擴展
1. 新增 `create_table_from_text()`
2. 新增 `create_table_from_files()`
3. 更新測試

### Phase 3: MCP Tools
1. 新增 `list_available_assets`
2. 新增 `get_existing_image`
3. 新增 `create_table_from_markdown`
4. 新增 `create_table_from_text`

### Phase 4: Asset Bundle（進階）
1. 實作 `get_asset_bundle` 批次獲取
2. 優化 Token 消耗

---

## ✅ 預期成果

| 功能 | 現狀 | 重構後 |
|------|------|--------|
| **做表** | 必須先拆解 PDF | 可直接從 MD/TXT 建表 |
| **用圖** | 每次重新拆解 | 直接讀取已存在圖片 |
| **彙整** | 只能單文檔 | 支援多 MD 檔案合併 |
| **重送** | 需要完整流程 | 按需獲取任意資產 |

---

*提案日期: 2026-01-12*
*狀態: 待討論*
