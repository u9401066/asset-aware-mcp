# PDF Parser 與 Preflight 評估報告（2026）

**原始評估日期**：2026-07-08

**本次更新日期**：2026-08-13

**範圍**：PDF inspection、routing、extraction engines、security holds 與 citation-ready asset workflow

---

## 0. 執行摘要

- Core PDF backend 仍是 `PyMuPDF>=1.24.0`；它提供不需模型的可靠 baseline、圖片 bytes、rendering 與 geometry。
- 新增的 `document(op="preflight", pdf_path=...)` 先以內建 PyMuPDF 做 process-isolated inspection，回傳穩定 `pdf-preflight-v1` schema、原始來源 SHA-256、逐頁 classification、OCR reasons 與建議 route。
- Active high-fidelity PDF extras **只有** `pdf-plus`（PyMuPDF4LLM）與 `docling`。`mineru`、`marker` 都是空 extra 的 **security hold**，不得透過降低 dependency security floors 重新啟用。
- `firecrawl/pdf-inspector` 是設計參考，不是 runtime dependency。研究固定在 commit [`076183e2e40a2ea71f9e04def182ea9984a1e50e`](https://github.com/firecrawl/pdf-inspector/commit/076183e2e40a2ea71f9e04def182ea9984a1e50e)。PyPI 1.14.1 尚未包含該 commit 的 content-stream pre-decode DoS hardening，因此目前不導入。
- Preflight 是 router，不是 parser correctness claim、PDF sanitizer、malware scanner、OCR engine 或 citation source；正式 evidence 仍由 manifest、blocks、segmentation 與 citation index 建立。

---

## 1. 問題與設計邊界

只用單一 PDF parser 處理所有頁面，容易在下列文件失敗：

- 原生文字與掃描頁混合。
- 大幅 raster image 上疊少量或品質不佳的 OCR text layer。
- 多欄、表格、圖說、向量圖與複雜 reading order。
- 損壞、加密或刻意消耗 parser 資源的 PDF。

本 repo 的核心不是產出一次性 Markdown，而是把文字、tables、figures、sections 與精準 locators 轉成 agent 可重用 assets。因此 preflight 的責任只包含：

1. 固定原始來源 identity。
2. 在任何正式 extraction 前提供 bounded、逐頁 signals。
3. 將所有頁碼與座標正規化成單一 contract。
4. 建議下一個 extractor/OCR route。
5. 以 typed failure 結束不安全或超出 budget 的工作。

它不負責修改來源、清理 active content、宣稱 PDF 安全，或把 heuristic classification 當作 citation evidence。

---

## 2. `pdf-preflight-v1` contract

呼叫入口：

```text
document(op="preflight", pdf_path="/absolute/path/to/source.pdf")
```

成功 payload：

| 欄位 | Contract |
|---|---|
| `schema_version` | 固定 `pdf-preflight-v1` |
| `status` | 固定 `ok` |
| `source` | `filename`、`size_bytes`、原始 source bytes 的 64-char lowercase `sha256` |
| `inspector` | `asset-aware-pymupdf-preflight`、`pymupdf` 與 backend version |
| `coordinate_system` | 明確宣告頁碼 base、origin、units、bbox format、axes 與 rotation basis |
| `page_count` | 大於零且等於 `pages[]` 數量 |
| `classification_counts` | `native/sparse/image/scanned/hybrid` 的完整 histogram |
| `ocr_recommended` | 是否至少一頁有 OCR reason |
| `ocr_pages` | 依頁面順序排列的 1-based OCR pages |
| `recommended_engine` | 文件層 `pymupdf`、`pymupdf+ocr` 或 `docling` |
| `pages[]` | locator、metrics、classification、OCR decision/reasons 與 page route |

失敗 payload 維持相同 `schema_version`，並回傳 `status=error`、`error_code`、`message`。目前 error codes 為：

```text
file_not_found, not_a_file, invalid_pdf, file_too_large,
encrypted_pdf, page_limit_exceeded, source_changed, timeout,
parse_failed, worker_failed
```

Domain models 採 frozen、`extra=forbid`，並驗證：

- 頁碼必須連續且從 1 開始。
- `classification_counts` 必須能由 `pages[]` 重建。
- `ocr_pages` 與文件/逐頁 OCR flags 必須一致。
- bbox 必須 finite、正向且位於 page bbox 內。

### 2.1 Locator contract

- Page number：**1-based**。
- Origin：**top-left**。
- Units：PDF points。
- Bbox：`[x0, y0, x1, y1]`。
- Axes：x 向右、y 向下。
- Basis：**unrotated crop box**；`page_bbox` 從 `(0, 0)` 開始。
- Rotation：另存為 `rotation_degrees`（0/90/180/270），不得先旋轉 locator 再省略 basis metadata。

這個正規化層是必要的，因為 upstream libraries 常混用 0/1-based pages、bottom-left/top-left origins 或 rotated/unrotated coordinates。Infrastructure objects 不應直接洩漏至 citation domain。

---

## 3. Classification 與 route policy

### 3.1 Signals

每頁收集：

- non-whitespace text characters、words、text blocks。
- raster image count、累計 coverage、最大 image coverage。
- vector drawing count。
- content union bbox 與 rotation。

目前 `pdf-preflight-v1` 的 threshold：

- Reliable native text：非疑似亂碼，且至少 60 個非空白字元；或至少 30 個非空白字元加 5 words。
- Significant visual：最大 raster image coverage 至少 18%，或至少 4 個 vector drawings。
- Image dominant：最大 raster image coverage 至少 45%。
- Suspected scanned：缺少 reliable native text，且最大 raster image coverage 至少 72%。
- Suspected garbled：至少 8 個非空白 characters，其中 replacement/control/private-use/surrogate 類別達 20%。

Threshold 是 versioned routing policy，不是 precision/recall 或內容可信度分數。

### 3.2 Page classes

| Class | 語意 |
|---|---|
| `native` | 有 reliable native text，無 significant visual |
| `sparse` | 沒有 reliable native text，也沒有 significant visual；包含真正空白頁 |
| `image` | 有 significant visual、缺少 reliable native text，但不符合 scanned threshold |
| `scanned` | 缺少 reliable native text，最大 raster image 覆蓋至少 72% |
| `hybrid` | 同頁同時有文字與 significant visual |

### 3.3 OCR reasons

固定 enum：

- `no_text`
- `sparse_text`
- `image_dominant`
- `suspected_scanned_page`
- `suspected_garbled_text`
- `vector_only`

`ocr_recommended` 嚴格等於 reasons 是否非空。空白 `sparse` page 沒有 OCR reason，不會浪費 OCR；有少量文字的 `sparse` page 才標記 `sparse_text`。`vector_only` 表示無 raster image、缺少 reliable native text，但 vector drawings 已達 visual threshold。

### 3.4 Route

Page route：

1. `hybrid` 或 `vector_only` → `docling`。
2. 其他有 OCR reason 的 page → `pymupdf+ocr`。
3. 其餘 → `pymupdf`。

Document route 依需求優先序聚合：`docling` > `pymupdf+ocr` > `pymupdf`。Preflight 只回傳建議，不會自動下載模型、啟動 OCR 或進行 ingest。

---

## 4. Process isolation 與 resource caps

預設 inspector 使用獨立 `spawn` process；application service 再以非阻塞方式等候，避免卡住 MCP event loop。

| Guard | Default |
|---|---:|
| Wall timeout | 20 seconds |
| Source file size | 256 MiB |
| Page count | 2,000 |
| Words per page | 100,000 |
| Raster image records per page | 100,000 |
| Vector drawing records per page | 100,000 |
| Linux worker address space | best-effort 1.5 GiB |

其他 fail-closed checks：

- 檔案必須從 byte 0 開始具有 `%PDF-` signature。
- 未解密 PDF 回傳 `encrypted_pdf`。
- Parse 前後重新 stat 與 SHA-256；identity 或 bytes 改變時回傳 `source_changed`。
- Worker payload 回到 parent 後重新經 Pydantic schema validation。
- Timeout 後 terminate，必要時 kill worker。

### 非 sanitizer 聲明

這些 guard 只限制此 inspection operation 的工作量與 failure blast radius。Preflight 不會偵測或移除 JavaScript、launch actions、embedded files、malicious URLs、prompt injection、polyglot payload 或其他 active content；也不會修復、重新封裝、解密或保證 PDF 規格完整。處理不可信輸入仍應使用 OS/container sandbox、最小權限與獨立 security scanning。`document(op="safety_audit")` 也是 artifact-level AI safety signal，不是 malware certification。

---

## 5. Extraction engine status

### 5.1 Active paths

| Path | Packaging | Status | Role |
|---|---|---|---|
| PyMuPDF | core dependency | Active | Fast baseline、geometry、rendering、image bytes、fallback |
| PyMuPDF4LLM | `pdf-plus` extra | Active | 輕量 layout-aware text/Markdown upgrade |
| Docling | `docling` extra | Active | Structured layout、reading order、tables、formula/figure path |

因此 active high-fidelity PDF extras **只有 `pdf-plus` 與 `docling`**。空的 `pdf` extra 是相容 placeholder，不代表另一個 engine。

### 5.2 Security holds

| Adapter | Extra | Hold reason | Re-enable gate |
|---|---|---|---|
| MinerU | `mineru = []` | MinerU 3.4.4 限制 `transformers<5`，而目前 security fixes 要求 `transformers>=5.5` | Upstream 解除 cap；安全 floor 可正常 resolve；isolated smoke/adversarial tests 通過 |
| Marker | `marker = []` | Marker PDF 1.10.2 限制 `Pillow<11`，而 runtime 要求 `Pillow>=12.2.0` | Upstream 支援 patched Pillow range；artifact、OOM 與 citation regression gates 通過 |

Adapters 可以保留，方便未來重啟或提供明確診斷；但不得把它們寫成 active、recommended install，也不得降級 security floors 來換取 resolver success。

---

## 6. `firecrawl/pdf-inspector` pinned 評估

### 6.1 研究快照

評估固定在 2026-08-12 的 commit [`076183e2e40a2ea71f9e04def182ea9984a1e50e`](https://github.com/firecrawl/pdf-inspector/commit/076183e2e40a2ea71f9e04def182ea9984a1e50e)，避免以變動中的 `main` 作為不可重現依據。

Primary sources：

- [Pinned README / architecture and public APIs](https://github.com/firecrawl/pdf-inspector/blob/076183e2e40a2ea71f9e04def182ea9984a1e50e/README.md)
- [Core load → classify → extract → structure/table → Markdown flow](https://github.com/firecrawl/pdf-inspector/blob/076183e2e40a2ea71f9e04def182ea9984a1e50e/src/lib.rs#L3882)
- [Detector limits and OCR routing signals](https://github.com/firecrawl/pdf-inspector/blob/076183e2e40a2ea71f9e04def182ea9984a1e50e/src/detector.rs#L14)
- [Positioned text/item types](https://github.com/firecrawl/pdf-inspector/blob/076183e2e40a2ea71f9e04def182ea9984a1e50e/src/types.rs#L98)
- [Tagged structure-tree / MCID extraction](https://github.com/firecrawl/pdf-inspector/blob/076183e2e40a2ea71f9e04def182ea9984a1e50e/src/structure_tree.rs#L18)
- [Python binding surface](https://github.com/firecrawl/pdf-inspector/blob/076183e2e40a2ea71f9e04def182ea9984a1e50e/src/python.rs#L484)
- [NAPI async/table surface](https://github.com/firecrawl/pdf-inspector/blob/076183e2e40a2ea71f9e04def182ea9984a1e50e/napi/src/lib.rs#L379)
- [Integration/adversarial tests](https://github.com/firecrawl/pdf-inspector/blob/076183e2e40a2ea71f9e04def182ea9984a1e50e/tests/integration_tests.rs)
- [Pinned CI workflow](https://github.com/firecrawl/pdf-inspector/blob/076183e2e40a2ea71f9e04def182ea9984a1e50e/.github/workflows/ci.yml)
- [Single-source version sync script](https://github.com/firecrawl/pdf-inspector/blob/076183e2e40a2ea71f9e04def182ea9984a1e50e/scripts/version.py)

### 6.2 值得借鑑

- Parse/load 後分成 detect-only、analyze、full 的 staged work。
- 逐頁 OCR reasons，而不是只有 document-level scanned boolean。
- Positioned items 與 tagged `(page, MCID)` semantic join。
- Tagged、ruled-line、alignment/heuristic 多層 table detection。
- Fidelity 與 compact projections 分離。
- 對 content operations、nested XObjects、structure trees、forms 與 table candidates 設明確 budgets。
- Hostile/synthetic fixtures、golden output、cross-API invariants 與 paired benchmark gates。
- Version locations 的 preflight/sync check、pinned Actions 與 idempotent registry publication。

### 6.3 不應複製

- 混合 0-based/1-based page conventions 與不同 coordinate origins。
- 把轉換後 Markdown 當作 canonical citation evidence。
- Image placeholder/bbox 當成完整 figure asset；本 repo 仍須保存實際 image bytes/hash。
- Python/NAPI/WASM 能力不對稱或兩套語意不同的 CLI。
- 將 backend confidence 當作 evidence quality 或 citation truth。
- 只以 Markdown benchmark 決定完整 asset engine。
- Publish workflow 與 full CI gate 解耦。

本 repo 已有更完整的 source hashes、manifest、segmentation、EvidenceSpan、figures/tables、Foam 與 MCP domain，因此 pdf-inspector 最適合提供 preflight ideas，而不是替換 aggregate/schema。

### 6.4 1.14.1 supply-chain caveat

官方 [PyPI 1.14.1](https://pypi.org/project/pdf-inspector/1.14.1/) 的 source distribution 發布時間早於 pinned main 的後續 hardening。特別是 commit [`076183e`](https://github.com/firecrawl/pdf-inspector/commit/076183e2e40a2ea71f9e04def182ea9984a1e50e) 才把 content-stream operation cap 放到 operator allocation/decode 之前；1.14.1 sdist 仍是先 decode，再檢查 operation count。

因此目前決策是：

- 不把 `pdf-inspector==1.14.1` 加入 core 或 optional dependencies。
- 不以未發布的 Git commit 取代正式 wheels，避免 VSIX/跨平台 supply-chain 與 reproducibility 問題。
- 不把這項差異描述成未獲 upstream 認定的 CVE；準確說法是「發布包尚未包含 main 已合併的 DoS hardening」。
- 等待包含 `076183e` 及當時其他必要 bounding fixes 的正式 release/sdist，再以 hostile PDFs、timeout/RSS、cross-platform wheel 與 citation invariants 重新驗證。

---

## 7. 建議驗證 gate

每個 PDF routing/extraction backend 變更至少驗證：

1. 五種 page classes 與每個 OCR reason 的 synthetic fixtures。
2. 旋轉/crop box 的 1-based top-left locator invariants。
3. 同一 source 重跑時 SHA-256、asset IDs、segment hashes 穩定。
4. Native、OCR、structured engines 的 page count 與 source-page mapping 一致。
5. Tables、figures、reading order、formula、OCR routing 與 exact citation locator 品質。
6. Content streams、nested XObjects/structure/forms、巨大座標與 decompression/resource attacks。
7. Timeout 後 worker 被回收，下一次 request 仍能成功。
8. Baseline/candidate benchmark 不得遺失 predictions，並同時 gate aggregate 與 per-document regression。

Markdown quality 只是其中一項；完整評估還必須包含 asset completeness、locator integrity、wall time 與 peak RSS。

---

## 8. 現行決策

1. 預設使用 PyMuPDF core。
2. 先執行 `document(op="preflight")` 取得可重現 routing signals。
3. 低複雜 native pages 使用 PyMuPDF；需要輕量 layout-aware text 時可安裝 `pdf-plus`。
4. Hybrid/vector/complex layout 使用 active `docling` extra。
5. OCR reasons 明確的頁面才啟動 OCR；真正空白頁不做 OCR。
6. MinerU、Marker 維持 security hold。
7. pdf-inspector 只作 pinned design reference，直到正式 release 包含必要 hardening 並通過本 repo gates。
