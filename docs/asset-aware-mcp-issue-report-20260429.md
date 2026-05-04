# Asset-Aware MCP 問題報告

**日期**: 2026-04-29
**報告人**: GitHub Copilot
**相關系統**: asset-aware-mcp (本地 git clone)、anesthesia-exam 主專案

---

## 摘要

在嘗試使用 asset-aware-mcp 重新解析 Miller 麻醉學第 79 章（Critical Care Anesthesiology）時，遭遇多重環境與執行問題。主要問題集中在：**依賴套件版本混淆**、**MCP Server 與主專案虛擬環境隔離**、**Marker 記憶體不足 (OOM)**，以及 **PyProject 配置註解導致依賴未安裝**。

---

## 問題清單

### 1. PyProject.toml 可選依賴被註解

**現象**: `pyproject.toml` 中 `[project.optional-dependencies]` 的 `pdf` 區塊被整段註解，導致 `uv sync --all-extras` 不會安裝 `marker-pdf` 與 `pymupdf`。

**影響**:
- 執行 `scripts/ingest_miller_chapters.py --high-fidelity-marker` 時，因缺少 `marker-pdf` 而失敗。
- 執行 MCP Tool `mcp_asset-aware_m_parse_pdf_structure` 時回傳 `❌ Marker parsing failed: No module named 'marker'`。

**建議修正**:
- 取消註解 `pdf` extras，或將 `marker-pdf` 與 `pymupdf` 移至主依賴（若為核心功能）。
- 移除 `unstructured[pdf]`（註解已說明與 Python 3.12 不相容）。

---

### 2. 虛擬環境隔離導致 MCP Server 找不到 marker

**現象**:
- 主專案虛擬環境（`anesthesia-exam/.venv`）已安裝 `marker-pdf==1.10.2`。
- 但 MCP Server 實際執行時使用 `libs/asset-aware-mcp/.venv` 的 Python，該環境缺少 `marker-pdf`。
- `crush.json` 中 `asset-aware` MCP 的啟動指令為 `uv --directory libs/asset-aware-mcp run python -m src.presentation.server`，這會使用 asset-aware-mcp 子目錄的虛擬環境。

**影響**:
- 即使主專案已安裝 `marker-pdf`，MCP Tool 呼叫仍回報 `No module named 'marker'`。

**建議修正**:
- 統一虛擬環境：讓 MCP Server 使用主專案的 `.venv`，或在 `libs/asset-aware-mcp` 內也執行 `uv sync --extra marker`。
- 或修改 `crush.json` 的啟動指令，明確指定使用主專案的虛擬環境。

---

### 3. LightRAG 套件名稱混淆

**現象**:
- `asset-aware-mcp` 的 `pyproject.toml` 依賴 `lightrag-hku>=1.4.11`。
- 主專案執行時報錯 `No module named 'lightrag'`，因為 `lightrag-hku` 的 import 名稱是 `lightrag`，但安裝名稱不同。
- 後來手動安裝了 `lightrag==0.1.0b6`（另一個套件），這可能與 `lightrag-hku` 衝突。

**影響**:
- 兩個不同的 `lightrag` 套件同時存在，可能導致 API 不相容或行為異常。

**建議修正**:
- 確認 `asset-aware-mcp` 需要的是 `lightrag-hku` 還是 `lightrag`。
- 統一使用 `lightrag-hku`，並確認 import 路徑正確（`from lightrag.base import EmbeddingFunc`）。
- 若不需要 LightRAG（`ENABLE_LIGHTRAG=false`），應讓程式碼在缺少 `lightrag` 時優雅降級，而非直接拋出 `ModuleNotFoundError`。

---

### 4. Marker 解析記憶體不足 (OOM Kill)

**現象**:
- 執行 `ingest_miller_chapters.py --high-fidelity-marker` 時，Marker 在 `Recognizing Text` 階段被系統 Kill（Exit Code 137）。
- 已嘗試設定環境變數 `INFERENCE_RAM=4`、`PDFTEXT_CPU_WORKERS=1`，以及 `--chunk-size 2`，仍無法避免 OOM。
- 該 PDF 僅 12 頁，但 Marker 的 torch/surya OCR 模型記憶體需求極高。

**影響**:
- 無法完成高品質的 Marker 解析，只能退回 PyMuPDF fallback，導致 blocks.json 與 wiki link 不完整。

**建議修正**:
- 在文件或腳本中標註 Marker 的最低記憶體需求（建議 8GB+ VRAM 或 16GB+ RAM）。
- 提供 `--text-only` 或 `--fallback-blocks` 作為預設路徑，避免使用者因 OOM 而中斷。
- 考慮使用 `marker-pdf` 的 CPU-only 模式，或降低 `marker_max_pages_per_chunk` 至 1。

---

### 5. 腳本路徑與 uv run 行為不一致

**現象**:
- `uv run python scripts/ingest_miller_chapters.py` 有時會嘗試在 `libs/asset-aware-mcp/.venv` 中尋找腳本，導致 `can't open file` 錯誤。
- 這與 `uv` 的 workspace 行為有關，當目錄下有多個 `pyproject.toml` 時，`uv run` 可能會切換到子專案的虛擬環境。

**影響**:
- 使用者需要額外注意執行時的 CWD 與虛擬環境對應關係。

**建議修正**:
- 在腳本開頭明確檢查 `sys.executable` 與虛擬環境路徑，並在 README 中說明執行方式。
- 或將 `ingest_miller_chapters.py` 包裝成 `uv run --package anesthesia-exam ...` 的形式。

---

## 建議優先處理順序

| 優先級 | 問題 | 影響範圍 |
|--------|------|----------|
| P0 | 統一虛擬環境或確保子專案依賴完整 | MCP Tool 無法使用 |
| P1 | 取消註解 `pdf` extras 並修正 TOML 語法 | 新環境安裝失敗 |
| P1 | 釐清 `lightrag-hku` vs `lightrag` 依賴 | 執行時 ImportError |
| P2 | 文件化 Marker 記憶體需求與降級策略 | 使用者體驗 |
| P2 | 統一腳本執行路徑說明 | 開發者體驗 |

---

## 附錄：相關錯誤訊息

```
ModuleNotFoundError: No module named 'xlsxwriter'
ModuleNotFoundError: No module named 'lightrag'
ModuleNotFoundError: No module named 'marker'
Killed (Exit Code 137) — OOM during Marker text recognition
can't open file '.../ingest_miller_chapters.py': [Errno 2] No such file or directory
```

---

## 相關檔案

- `pyproject.toml`（根專案）
- `libs/asset-aware-mcp/pyproject.toml`
- `crush.json`
- `scripts/ingest_miller_chapters.py`
- `configs/asset-aware/miller_marker_hq.json`
