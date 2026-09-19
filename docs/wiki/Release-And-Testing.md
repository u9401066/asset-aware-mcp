# Release And Testing

## Focused Checks

依變更範圍先跑 focused tests：

```bash
uv run pytest tests/unit/test_count_tools_script.py -q
uv run pytest tests/test_mcp_tools.py tests/unit/test_mcp_docx_tools.py tests/unit/test_mcp_job_tools.py tests/unit/test_mcp_document_tools.py tests/unit/test_mcp_table_tools.py tests/unit/test_mcp_profile_tools.py tests/unit/test_mcp_knowledge_tools.py tests/unit/test_mcp_server_startup.py tests/unit/test_job_service_concurrency.py tests/unit/test_pdf_validation.py -q
uv run pytest tests/unit/test_pdf_preflight.py tests/unit/test_agent_asset_bundle_service.py -q
uv run pytest tests/unit/test_docx_service.py -q
```

MCP tests target official SDK 2 `MCPServer` registration and real client/stdio
transports. They also assert that runtime-injected `Context` parameters never
appear in public tool input schemas. `mcp>=2,<3` is the supported contract；SDK
v1 and FastMCP/v1 fallback are intentionally unsupported。Balanced / compact /
legacy matrix 僅驗證 tool UX，不代表 protocol-version compatibility。

## Codex PDF evaluation

這是模型實際使用 MCP 的 opt-in 測試，與一般 SDK stdio 測試分開。需要已登入的
Codex CLI，會使用模型額度；一般 `pytest` 不會啟動 Codex。來源只有產生的合成
PDF，執行器不更改使用者 MCP 設定，也不讀取登入憑證。

```bash
uv run pytest tests/unit/test_pdf_rotated_crops.py tests/unit/test_codex_pdf_evaluation.py tests/integration/test_pdf_crud_stdio_matrix.py -q
uv run python -m tests.codex_pdf.run --mode mixed --output /tmp/pdf-codex-mixed
uv run python -m tests.codex_pdf.run --mode scanned --output /tmp/pdf-codex-scanned
# Codex 未在 PATH 時加 --codex /absolute/path/to/codex；output 必須是新目錄。
# 重做獨立稽核，不再呼叫模型：
uv run python -m tests.codex_pdf.audit /tmp/pdf-codex-scanned
```

執行器以 `--ignore-user-config`／`--ephemeral` 和單一必要 MCP server 連到目前
checkout；停用 shell／其他 apps／子 Agent，只允許測試用工具操作隔離資料。
這依據 [Codex 非互動模式](https://learn.chatgpt.com/docs/non-interactive-mode) 與
[MCP 設定](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)。實際通過範例使用
CLI `0.154.0-alpha.6.1`；模型沿用 Codex 預設，不宣稱不同模型版本結果相同。

每份三頁 PDF 有七列、五欄，涵蓋純文字／無文字層掃描／混合頁、90 度旋轉、
非零 cropbox、前導零、負號、小數、百分比、比較符號與 µ 單位。期望值保留在
Agent 工作目錄之外，禁止用 shell 或讀取 fixture 程式取得答案。

`events.jsonl` 保留真實 MCP 呼叫及影像回應；`audit.json` 獨立核對來源 hash/mtime、
35 個欄位值、實際影像傳遞、掃描像素、各列引用、修改／刪除／還原歷史、Excel
重新開啟與 Wiki 資產包 hash。`run.json` 記錄程序結果，`expected.json` 記錄測資與
伺服器程式／lock hash。程序 exit 0 或 Agent 宣告成功，均不足以通過稽核。
main 開發版新增 `citation_readback_required`：最後一次修正後，Agent 必須透過
`table_cite read` 讀回所有 Reading cells 的完整引用。新增稽核逐頁核對範圍／hash、
穩定 cell 身分及完整定位與最終保存內容；只看摘要或未讀完分頁會失敗。
`citation_paging_required` 另要求至少一列使用 200 字元頁，實際完成帶 hash 的續讀。
舊測試紀錄維持原有八項檢查，不會被回溯描述為已測過這項新增能力。
可修復的工具錯誤保留在報告，完成後標示 `passed_with_recoveries`。
`first_transcription_exact` 另記初次轉錄是否完全正確，不把 Agent 事後修正
當成第一次就讀對；第二輪純掃描實測曾有兩個前導零缺漏，重新看圖後修正。

這些結果驗證限定測資與工具工作流程。掃描文字由 Agent 視覺轉錄，不冒充既有
文字 span；影像無法證明原始字元的 Unicode 編碼。模糊／手寫／合併儲存格／
複雜多欄與真實文件基準仍須擴充。表格 CRUD 操作衍生資料，並不改寫 PDF 版面。

## Full Python Gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src --ignore-missing-imports
uv run bandit -q -r src -x tests --severity-level medium
uv run pytest
python3 scripts/build_docs_site.py --check
uv lock --check
uvx --from uv==0.12.3 uv audit --preview-features audit-command --frozen --python-version 3.10
```

## Extension Gates

```bash
cd vscode-extension
npm run test:ci
npm run sync-assets:check
npm run test:install-smoke
npm audit --package-lock-only --audit-level=low
```

`test:install-smoke` 需要可執行的 VS Code CLI；Linux headless activation 另需 `xvfb-run`，下載版 VS Code 也需要系統圖形 runtime libraries（例如 `libgbm.so.1`）。

Before PyPI publish, runtime is verified from the built wheel with
`scripts/smoke_built_wheel.py`. After PyPI publish, the workflow verifies
`uvx --from asset-aware-mcp==$VERSION` diagnostics and MCP stdio handshake.

## Release Harness

`scripts/release.sh` 的預設模式是 pre-tag verification（安全的
dry-run）：它會執行完整 gates、重建 wheel/sdist 與 VSIX、執行 install /
stdio / Docker smoke，但不會建立 tag，也不會發布到 registry。執行前必須
先將 release 變更 commit 並 push 到 `main`；script 會 fail closed，要求 clean
worktree、local `main` 與 `origin/main` 完全相同、Python/VSIX 版本一致，
且預定的 annotated tag 尚未存在。

```bash
python scripts/audit_release_artifacts.py
python scripts/smoke_built_wheel.py
python scripts/build_docs_site.py --check
python scripts/audit_release_harness.py

# 預設：只驗證與建置，不建 tag、不發布
./scripts/release.sh

# 確認上述結果、main push 與 CI 後，再建立並 push annotated tag
./scripts/release.sh --push-tag
```

`--push-tag` 會重跑相同 gates，通過後建立 `v<version>` annotated
tag 並只 push 該 tag。推送 tag 會觸發 `.github/workflows/release.yml`；
GitHub Actions 之後擁有發布流程，local script 不會直接上傳 PyPI、
Marketplace 或 GitHub Release。`workflow_dispatch` 是 recovery／重跑入口，
仍要求已存在的 remote annotated tag、對應 commit 在 `main` 歷史中，
且 tag commit 與 workflow SHA 一致。

Actions 的發布順序是：

1. `test`：版本／tag identity、Python checks、完整 pytest、docs、security、
   harness 與 VSIX CI／install activation smoke。
2. `cross-platform-smoke`：Ubuntu、macOS、Windows 三平台 VSIX 安裝測試。
3. `release-preflight`：預先驗 Marketplace 權限，建置並稽核
   wheel/sdist 與 VSIX，執行 built-wheel 與 Docker stdio smoke。
4. `publish-pypi`：透過 trusted publishing 發布（已有同版本時驗證後重用）。
5. `publish-vscode`：先從 PyPI 安裝精確版本並完成 CLI／stdio
   smoke，再發布 VSIX、等待 Marketplace 可見，並上傳 workflow artifact。
6. `github-release`：用同一個 tag 建立 GitHub Release，並附上上一階段的
   VSIX。

Release workflow 會檢查：

- Python package version consistency。
- generated docs site 與 canonical wiki source exact sync。
- wheel/sdist required runtime files。
- VSIX package contents。
- retired external harness 是否被誤打包。
- Node/GitHub Actions release path。
- Marketplace publish visibility/retry。

The release harness now treats built-wheel console script execution and MCP
stdio handshake as first-class gates, not just import or `--help` checks.

## Post-Publish Verification

不以 workflow 單純顯示綠燈當作結案。等待所有 jobs 完成後，至少驗證
Actions、PyPI runtime、Marketplace 可見性與 GitHub Release 四個邊界：

```bash
VERSION="$(python3 scripts/get_version.py --strict-semver)"

gh run list --workflow release.yml --limit 5
gh run watch <run-id> --exit-status

uvx --refresh --python 3.11 \
  --from "asset-aware-mcp==$VERSION" \
  asset-aware-mcp doctor --json
uv run --no-project --python 3.11 \
  --with "asset-aware-mcp==$VERSION" \
  python scripts/smoke_mcp_stdio.py -- asset-aware-mcp

(cd vscode-extension && npx --no-install vsce show u9401066.asset-aware-mcp --json)
gh release view "v$VERSION" --json tagName,targetCommitish,isDraft,isPrerelease,assets
```

同時開啟 `https://pypi.org/project/asset-aware-mcp/$VERSION/` 與
`https://marketplace.visualstudio.com/items?itemName=u9401066.asset-aware-mcp`，
確認兩個 registry 都顯示精確版本；GitHub Release 必須不是 draft／
prerelease（除非本次本來就是 prerelease）、tag/target commit 正確，且
VSIX asset 存在。任一邊界未可見時，先保留 tag 與 workflow 證據並修復，
不要重用版本號。

## Dependency And Security Gate

`.github/workflows/dependency-security.yml` 是唯讀 gate：dependency manifests、
lockfiles 或 workflows 的 PR 會觸發，也可手動執行，並在每週一 05:17 UTC
排程執行。它不會自動寫回 repository：

- `uv lock --check` 防止 `pyproject.toml` 與 `uv.lock` drift。
- pinned uv 0.12.3 的 `uv audit --frozen --python-version 3.10` 稽核 universal lock，包含所有可解析
  runtime、dev 與 optional extras；不使用 vulnerability allowlist。
- `npm audit --package-lock-only --audit-level=low` 稽核 VSIX lockfile。
- Bandit 阻擋 Python source 的 medium/high security findings。
- CI 與 release preflight 也執行 Python lock check/audit，避免安全檢查只存在於
  排程。

`.github/dependabot.yml` 每週分流更新 uv/PyPI、npm 與 GitHub Actions，minor/patch
合併成 ecosystem group，major 保持獨立 PR，並設合理 open-PR limits。Python
專案使用 GitHub 官方 `uv` ecosystem，確保 `pyproject.toml` 與 `uv.lock` 一起更新。

## Scheduled Project Hygiene

`.github/workflows/project-hygiene.yml` 會在每週三 06:43 UTC 執行，也可用
`workflow_dispatch` 手動啟動。它刻意不 commit、不 push，也不繞過受保護的
`main`：

- 以 `scripts/build_docs_site.py --check`、public docs regressions、release
  metadata audit 與 VSIX `sync-assets:check` 驗證 website、Wiki source、README
  和 bundled assistant assets 都仍由 canonical source 可重建。
- 只對這個專案管理的 labels 執行 idempotent apply + exact check；workflow
  只提升該 job 的 `issues: write`，不刪除使用者或 GitHub 建立的其他 labels。
- repository description、homepage 與 canonical topics 預設只做 exact
  read-only drift check。若 repository owner 配置具有 Administration write
  的 repo-scoped `PROJECT_HYGIENE_TOKEN`，排程才會 apply 後再次驗證；手動要求
  apply 但缺 token 時會 fail closed。

本機可先執行同一份契約：

```bash
./scripts/gh_sync_labels.sh --check
./scripts/gh_update_repo_metadata.sh --check

# 只有在明確要寫入且 token 權限足夠時
./scripts/gh_sync_labels.sh --apply
./scripts/gh_update_repo_metadata.sh --apply
```

這個排程負責 deterministic 同步與 drift 告警；需要人類撰寫的新功能說明
仍應走一般 branch／review／CI，再由 Pages 部署與 Wiki sync 發布，避免 bot
自行改寫技術主張。

目前兩個重型 PDF backend 採 fail-closed security hold：

- MinerU adapter 保留，但 `[mineru]` extra 為空；MinerU 3.4.4 pin
  `transformers<5`，而相關 fixes 需要 `transformers>=5.5`。
- Marker adapter 保留，但 `[marker]` extra 為空；marker-pdf 1.10.2 pin
  `Pillow<11`，與 `Pillow>=12.2.0` 安全底線衝突。

等待上游解除限制後才恢復 extras，不用 audit ignore 把不可解 graph 假裝成綠燈。

## Tool Count

工具數量不可手算：

```bash
./scripts/count_tools.sh
```

目前輸出：

```text
Default public tools:       30 tools (balanced surface)
Decorator inventory:        63 tools in 7 modules
Total resources:            13 resources in 2 modules
Public MCP endpoints:       43 endpoints
Legacy decorator endpoints: 76 endpoints
```

## Docker Smoke

```bash
docker build -t asset-aware-mcp:smoke .
docker run --rm asset-aware-mcp:smoke doctor --json
docker run --rm asset-aware-mcp:smoke list-tools --json
uv run python scripts/smoke_mcp_stdio.py -- docker run --rm -i asset-aware-mcp:smoke
```

Docker build context 已忽略 local uv/runtime caches、assistant harness folders 與 document processing artifacts，避免 release smoke 被本機輸出拖慢或污染。
目前 Dockerfile 刻意不使用 BuildKit cache mount，以保留 legacy builder
相容性；這個 build 不會單因 Dockerfile 而要求 `docker buildx`。

## Codex native PDF evaluation (Unreleased)

原生頁面路徑另有 opt-in 實測，普通 pytest 不會呼叫模型：

```bash
uv run pytest tests/unit/test_native_pdf*.py tests/unit/test_codex_native_pdf_audit.py tests/integration/test_native_pdf_stdio.py
uv run python -m tests.codex_native_pdf.run --codex /absolute/path/to/codex --output /tmp/native-pdf-run
uv run python -m tests.codex_native_pdf.audit /tmp/native-pdf-run
```

output 必須是新目錄。Runner 使用現有 Codex 登入，不讀取憑證；隔離使用者
設定，只開放本 checkout 的 document MCP tool，關閉 shell／其他 server／
subagents。三頁純掃描測資需真正收到 PNG，完整讀回頁面引用，建立新 PDF、
插入兩張空白頁、旋轉、刪除空白、重排、核對舊引用，再 publish 與 export_wiki。
原始來源不可回寫。預期轉錄保留字串、前導零及 Unicode，µ／μ 不會正規化。

獨立稽核讀取實際事件、受管理版本與檔案；分別檢查圖片交付、完整分段引用、
複製來源歷程、來源 hash／mtime、最終頁序／幾何／像素、Wiki hash 與精確轉錄。
模型宣稱成功不算證據。保留 audit.json、events.jsonl、expected.json 與完整
artifacts；失敗或修正不能改成首次全對。此測資與固定 renderer 的像素比對
不代表通用 OCR 準確率、任意 PDF 保真或所有檢視器行為。

2026-09-18 的 native scanned run 02（最終 worker 實作）完成 49 次 MCP
呼叫、零工具錯誤，七項獨立檢查全部通過：十份完整頁面表示、六張實際
原始／最終 PNG、七列 35 格最終精確轉錄，以及來源、歷程、最終 PDF 與
Wiki 核對。MCP 圖片另外比對其固定版本的獨立渲染像素。較早 run 01 的
171 次呼叫與通過結果另行保留；呼叫數受模型分段讀取策略影響。

## Codex PPTX picture evaluation (Unreleased)

```bash
uv run pytest tests/unit/test_native_pptx_picture*.py tests/integration/test_native_pptx_picture_stdio.py
uv run python -m tests.codex_pptx_pictures.run --codex /absolute/path/to/codex --output /tmp/pptx-picture-run
uv run python -m tests.codex_pptx_pictures.audit /tmp/pptx-picture-run
```

Runner 使用新的輸出目錄與既有登入，僅開放本 checkout 的 native document
MCP 工具。模型須登錄圖片／簡報、插入兩張共用圖片、完整讀回形狀、顯示 PNG、
拆出並驗證圖片資產、只替換其中一張、確認另一張仍為原圖、刪除第二張、核對
舊引用，最後 publish／export_wiki。原始檔案不可回寫。預期值不交給模型。
獨立稽核比對實際圖片像素、版本歷程、圖片位元組、拆出來源與 Wiki；轉錄
保留前導零。嵌入圖片預覽通過不代表投影片渲染已驗證。普通 pytest 不啟動模型。

2026-09-18 的兩次實測各完成 38 次 MCP 呼叫、零工具錯誤、3 次實際圖片
顯示與 2 份完整形狀讀回。獨立稽核確認原始形狀／備註與未修改 parts 保留，
來源 A101／007 與替換 C301／001 的辨讀相符；此為合成案例，不能外推一般
OCR 正確率或完整簡報版面。執行紀錄保留來源與 lock hash，可比對實測版本。

## Codex scanned PDF to PPTX table evaluation (Unreleased)

```bash
uv run python -m tests.codex_pptx_tables.run \
  --codex /absolute/path/to/codex --output /tmp/pptx-table-run
```

實際 Codex CLI 只使用 `document(op="native")`：看掃描頁的真正 MCP PNG，
建立含合併標題的可編輯表格、完整讀回、改值／還原、刪除副本、驗證原始頁面
與舊表格引用，再輸出 PPTX／Wiki。獨立稽核比對頁面像素、完整引用使用順序、
前導零等原樣文字、每個受管理版本的表格尺寸與合併、歷史證據及附件位元組。

2026-09-18 run 01：67 次嘗試、66 次成功呼叫、1 次已恢復的格式輸入錯誤；
初次轉錄完全正確。模型曾把來源證據塞入 `citation_contract`，MCP 拒絕後修正。
此紀錄保留為 `passed_with_recoveries`；新的 typed citation display schema
直接公開預設／模板欄位，後續重跑驗證。模型實測不在一般 pytest 自動啟動。
這是合成掃描頁，不代表一般 OCR 準確率、真實文件 corpus 或投影片完整渲染。

同日 run 02 使用完成型別規格修正的 runtime：66 次呼叫、零工具錯誤，
初次轉錄完全正確；1 張實際掃描 PNG、4 份不同版本／定位的完整證據紀錄
（重複讀取另計）。兩次的最終 PPTX／Wiki 與歷史還原稽核都通過。

## Codex native derivation evaluation (Unreleased)

在已登入的 Codex CLI 執行：

```bash
uv run python -m tests.codex_pptx_tables.run --codex /absolute/path/to/codex --output /tmp/native-derivation-run --derivations
```

Agent 先完成掃描頁到可編輯表格的工作，再完整讀取最終形狀與來源頁，新增
轉製紀錄、修訂核對說明、建立並撤回暫存主張，查驗歷史及匯出含來源附件的
Wiki。稽核以實際 MCP 回應和原生產物判斷：引用需先完整讀回，帳本須先
完整讀取再以同一 hash 修改，最終歷史／活躍狀態／附件與快照 hash 必須一致。
來源 PDF 不能被改寫；一般 pytest 不會啟動模型。初次辨讀、工具錯誤與恢復
仍分開記錄。機械查驗不代表語意正確、一般 OCR 準確率或完整投影片畫面保真。

2026-09-18 derivations run 02：93 次 MCP 呼叫、零 MCP 工具錯誤，初次轉錄
完全正確；1 張實際掃描 PNG、5 份不同版本／定位的完整紀錄、4 個帳本事件
（修訂及撤回後留下 1 個活躍主張）與精確來源 PDF 附件均通過獨立稽核。
模型另自述修正一次本地 orchestration 語法錯誤；事件流沒有該錯誤的獨立
工具紀錄，此自述保留在 `agent_reported_limitations`，不與零 MCP 錯誤混用。

同日 run 03 重跑相同當時的 runtime：92 次 MCP 呼叫、零工具錯誤，初次轉錄
完全正確；同樣通過 1 張 PNG、5 份完整紀錄、4 個帳本事件、1 個活躍主張
與精確來源附件稽核。兩次均未宣稱完成投影片渲染核對。

保留原生附件副檔名後的最終 runtime，run 04 完成 96 次 MCP 呼叫、零 MCP
工具錯誤，初次轉錄正確，完整表格／帳本／來源附件稽核通過。初版稽核器曾
把「先取預覽，再從 offset 0 完整重讀」誤判為不連續；修正後新增三個回歸
案例，仍要求完整覆蓋與正確 hash，原始失敗報告保留。模型另自述修正過一次
過度跳脫的字型診斷；此聲明亦獨立保留，不作為伺服器或版面正確性的證明。


### Codex native table grid exercise (Unreleased)

以 `tests.codex_pptx_tables.run --grid` 啟用實際模型的列欄流程。Codex 先查看
掃描頁 PNG、建立並核對表格，接著逐次插欄、插列、調整列高／欄寬、刪列、刪欄。
每次使用完整目前引用，操作前後都完整讀回並核對 hash。獨立稽核直接開啟五個
中間 PPTX 版本，比對原始轉錄、暫存列的精確字串、合併格與尺寸，以及未修改
儲存格 XML／格式、其他 parts 與周圍 XML。最後恢復原格網並檢查來源、歷史與
Wiki。`--derivations` 可另外組合；一般 pytest 不會啟動模型。

此流程使用合成掃描頁，不宣稱完成整張投影片渲染或真實文件 corpus 覆蓋。

2026-09-19 的 grid run 01 完成 **123 次 MCP 呼叫、零工具錯誤**，首次轉錄
完全一致，交付一張實際 PNG 並完整讀取九筆不同版本的表示。五次格網變更與
五個中間 PPTX 版本均通過獨立內容／合併／尺寸／保留 XML 稽核；來源、歷史、
發布檔與 Wiki 亦通過。完整 pytest：1,971 passed、30 optional skipped；
擴充套件：199 tests。這些結果仍不代表完成投影片畫面核對。

### Codex native table merge/split exercise (Unreleased)

使用 `tests.codex_pptx_tables.run --merges`，也可組合 `--grid`／`--derivations`。
Agent 完成掃描表格後，插入帶有前導零、正負號、粗斜體的暫存列，合併其內容、
拆分、刪除暫存列，最後拆分並重合併原標題。六次操作皆須完整目前引用與
完整讀回；拆分後五段文字仍在左上角，不會自動還原原先分格。

獨立稽核開啟每個中間 PPTX，逐一核對段落 XML／格式／順序、原始掃描格子、
格網／外框／合併、周圍 XML 與未修改 parts。額外回歸測試刻意破壞前導零、
格式、合併及拆分內容，確認稽核會拒絕。一般 pytest 不啟動模型，實際執行
保留事件流、初次辨讀、工具錯誤與恢復紀錄；完整畫面仍須另行核對。

2026-09-19 merge run 01（`--grid --merges`）完成 **180 次 MCP 呼叫、零工具錯誤**，
首次轉錄完全一致，1 張實際 PNG、13 份完整紀錄。五個格網與六個合併／拆分
中間版本全部通過獨立稽核，段落 XML、原字串與格式、來源、發布檔及 Wiki
均符合預期；未執行完整投影片渲染。完整 pytest 為 2,015 passed／30 optional
skipped，之後新增「起點缺少可選文字框」案例並通過含該案例的 18 項測試；
production source 未變更。VSIX 199 tests 通過。

### Codex native slide structure exercise (Unreleased)

使用 `tests.codex_pptx_tables.run --slides`，可與格網、合併／拆分及轉製帳本流程
組合。Agent 查看掃描頁並完成可編輯表格後，探索目前版型、插入兩頁帶格式文字框、
重排全部頁面，再刪除兩頁暫存內容。每一步前後完整讀取目前頁序，完整讀回新增
文字框及重排後的原表格，刪頁後仍驗證暫存文字框的歷史證據。

獨立稽核讀取每個中間 PPTX 的原始 ZIP 關聯與 XML，檢查頁面身分、頁序、精確
字串／前導零／格式／位置、原始 parts、content types、關聯及數量屬性。不能用
python-pptx 在記憶體中重新命名後的 part 路徑取代原始檔案身分；此差異已由
重排回歸測試揭露並修正稽核器。合成掃描頁通過不代表通用 OCR 或完整投影片渲染。

2026-09-19 slides run 01 完成 **96 次 MCP 呼叫、零工具錯誤**，首次轉錄完全
一致，1 張實際 PNG、8 份完整形狀／頁面紀錄。三個中間投影片版本的頁序／身分、
新增文字格式與原始 parts 均通過獨立稽核，刪頁後歷史證據及最終發布檔／Wiki
也通過。完整 pytest：2,068 passed、30 optional skipped；VSIX：199 tests。
沒有執行完整投影片檢視器渲染，因此不宣稱完整畫面保真。
