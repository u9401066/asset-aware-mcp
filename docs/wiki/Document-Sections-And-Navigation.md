# Document Sections And Navigation

這頁專門說明「文件章節」這一層。它介於 PDF/DOCX ingest 與 citation evidence 之間：
先用 section tree 找到人類可理解的位置，再用 evidence locator 驗證可引用 claim。

## 心智模型

| 層級 | 用途 | 主要入口 |
|---|---|---|
| Document | 文件身分、manifest、assets | `document(op="inspect")` / `inspect_document_manifest` |
| Section | 章節樹、章節 path、頁碼範圍 | `list_section_tree` / `document_asset(op="tree")` |
| Blocks | 章節內的文字、表格、圖片、bbox context | `get_section_blocks` / `document_asset(op="blocks")` |
| Source locator | 可引用文字位置、span、hash | `evidence(op="locate")` / `search_source_location` |
| Evidence bundle | 可審查引用包 | `evidence(op="bundle")` / `citation_bundle` |

Section navigation 不是 citation verification。它幫你找位置；正式 claim 仍要回到
`evidence(...)` 或 `citation_bundle(...)`。

## 最小流程

先列章節樹：

```text
document_asset(
  op="tree",
  doc_id="doc_abc",
  max_depth=3,
  response_format="flat"
)
```

從回傳結果複製 `path`，再取得某章節的詳細資訊：

```text
document_asset(
  op="detail",
  doc_id="doc_abc",
  path="Results/Primary Outcome"
)
```

列出章節 blocks，保留 page/bbox/block context：

```text
document_asset(
  op="blocks",
  doc_id="doc_abc",
  path="Results/Primary Outcome",
  include_children=true,
  block_types=["Text", "Table"],
  limit=20
)
```

如果你要找可引用 span，切到 evidence locator：

```text
evidence(
  op="locate",
  doc_id="doc_abc",
  query="primary outcome",
  block_types=["Text", "Table"],
  limit=5
)
```

## 什麼時候用哪個入口

| 你想做什麼 | 用這個 | 不要用 |
|---|---|---|
| 看文件有哪些章節 | `document_asset(op="tree")` | `evidence(op="find")` |
| 讀某章節摘要與範圍 | `document_asset(op="detail")` | `citation_bundle` |
| 拿章節內 blocks | `document_asset(op="blocks")` | `fetch_document_asset(full_text)` |
| 搜章節標題/path | `document_asset(op="search")` | `search_source_location` |
| 找文字所在 page/bbox | `evidence(op="locate")` | `document_asset(op="search")` |
| 產出可審查引用包 | `evidence(op="bundle")` | section tree |

## 和 Resources 的關係

若 MCP client 支援 resources，也可直接讀：

```text
document://{doc_id}/sections
document://{doc_id}/manifest
document://{doc_id}/blocks
```

Resource 適合瀏覽與快取；tool 適合篩選、限制深度、控制輸出格式，以及寫入 Foam/LLM wiki。

## 上線檢查

- Section path 必須可回到 manifest 或 blocks。
- Section search 只能宣稱找到章節候選，不可宣稱 citation verified。
- Evidence locator 要保留 page、bbox、block id、hash 或 surrounding context。
- 若要放進 LLM wiki，先用 section 找上下文，再用 evidence bundle 寫入 Foam note。
