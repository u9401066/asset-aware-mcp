# Copilot 自定義指令

## 開發哲學 💡

> **「想要寫文件的時候，就更新 Memory Bank 吧！」**
> 
> **「想要零散測試的時候，就寫測試檔案進 tests/ 資料夾吧！」**

---

## 法規遵循

你必須遵守以下法規層級：

1. **憲法**：`CONSTITUTION.md` - 最高原則，不可違反
2. **子法**：`.github/bylaws/*.md` - 細則規範
3. **技能**：`.claude/skills/*/SKILL.md` - 操作程序

---

## 架構原則

- 採用 **DDD (Domain-Driven Design)**
- **DAL (Data Access Layer) 必須獨立**
- 依賴方向：`Presentation → Application → Domain ← Infrastructure`
- 參見子法：`.github/bylaws/ddd-architecture.md`

---

## Python 環境（uv 優先）

- 新專案必須使用 uv 管理套件
- 必須建立虛擬環境（禁止全域安裝）
- 參見子法：`.github/bylaws/python-environment.md`

```bash
# 初始化環境
uv venv
uv sync --all-extras

# 安裝依賴
uv add package-name
uv add --dev pytest ruff
```

---

## Memory Bank 同步

每次重要操作必須更新 Memory Bank：

| 操作 | 更新文件 |
|------|----------|
| 完成任務 | `progress.md` (Done) |
| 開始任務 | `progress.md` (Doing), `activeContext.md` |
| 重大決策 | `decisionLog.md` |
| 架構變更 | `architect.md` |

參見子法：`.github/bylaws/memory-bank.md`

---

## Git 工作流

提交前必須執行檢查清單：

1. ✅ Memory Bank 同步（必要）
2. 📖 README 更新（如需要）
3. 📋 CHANGELOG 更新（如需要）
4. 🗺️ ROADMAP 標記（如需要）

參見子法：`.github/bylaws/git-workflow.md`

---

## 可用 Skills

位於 `.claude/skills/` 目錄：

| Skill | 功能 | 觸發詞 |
|-------|------|--------|
| git-precommit | Git 提交前編排器 | `GIT`, `commit`, `push` |
| ddd-architect | DDD 架構輔助 | `DDD`, `arch`, `新功能` |
| code-refactor | 主動重構與模組化 | `RF`, `refactor`, `重構` |
| memory-updater | Memory Bank 同步 | `MB`, `memory`, `記憶` |
| memory-checkpoint | 記憶檢查點 | `CP`, `checkpoint`, `存檔` |
| readme-updater | README 智能更新 | `readme`, `說明` |
| changelog-updater | CHANGELOG 自動更新 | `CL`, `changelog` |
| roadmap-updater | ROADMAP 狀態追蹤 | `RM`, `roadmap` |
| code-reviewer | 程式碼審查 | `CR`, `review`, `審查` |
| test-generator | 測試生成 | `TG`, `test`, `測試` |
| project-init | 專案初始化 | `init`, `new`, `新專案` |
| **pdf-asset-extractor** | **PDF→圖文分解+知識圖譜** | `PDF`, `ingest`, `figure`, `table`, `知識圖譜` |

> ⚠️ **pdf-asset-extractor 注意**：圖片 base64 非常大，一次只處理一張！

---

## 💸 Memory Checkpoint 規則

為避免對話被 Summarize 壓縮時遺失重要上下文：

### 主動觸發時機

1. 對話超過 **10 輪**
2. 累積修改超過 **5 個檔案**
3. 完成一個 **重要功能/修復**
4. 使用者說要 **離開/等等**

### 執行指令

- 「記憶檢查點」「checkpoint」「存檔」
- 「保存記憶」「sync memory」

### 必須記錄

- 當前工作焦點
- 變更的檔案列表（完整路徑）
- 待解決事項
- 下一步計畫

---

## 回應風格

- 使用**繁體中文**
- 提供清晰的步驟說明
- 引用相關法規條文
- 執行操作後更新 Memory Bank
