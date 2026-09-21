# Release And Testing

## Native PDF annotation evaluation (Unreleased)

批註工作流分別測試原生物件、完整 MCP 傳輸、實際 Agent 圖片核對與可攜證據。
合成測試涵蓋 12 種外觀、旋轉／CropBox／UserUnit、原生批註陣列、回覆相依、
既有外觀 bytes、簽章／鎖定與 stale 引用；SDK 2.0 的 balanced／compact 設定
均實際跑過建立、metadata／外觀更新、刪除、歷史選取／轉製與 Wiki。

2026-09-21 的 NIST SRM 1648a 原始 17 頁 PDF 實測：Codex 預設模型完成
**399 次成功 MCP 呼叫、321.35 秒、4 個管理版本、37 份完整批註紀錄、8 張 PNG**。
它從第 5 頁表格辨讀 `Aluminum (Al)(a,b) | 3.43 ± 0.13 | %`，建立螢光標記與
FreeText，修改 FreeText 外觀並刪除標記，再驗證已刪批註的歷史引用。
獨立稽核比對全部 17 頁原文串流／正文像素、既有 8 個連結、實際傳輸 PNG、
轉製來源與兩份 Wiki。一次不適用的 `contract.text_limit` 參數由 Agent 自行恢復，
錯誤與完整呼叫紀錄保留。Agent 的視覺核對範圍是頁索引 4、5，非全份視覺審閱。

同日的 NASA Apollo 11 原始 359 頁掃描報告先被正文核對副本的寫入警告攔下，
沒有提交修改。原因是副本未沿用既有「原始 bytes 證明重複 Length 相等」流程。
修正使用相同的嚴格 package 驗證後，聚焦回歸 **58 項通過**；衝突長度仍拒絕。
原失敗執行與未完成的稽核保留。NIST 上述數字是此修正之前的執行，來源雜湊
分開記錄；不能把先前通過結果直接當成後續程式的全套驗證。

修正後 NASA 第二次實測通過：**238 次成功呼叫、1 次自行恢復的參數錯誤、
379.19 秒、4 個版本、5 份完整批註紀錄、8 張 PNG、兩份 Wiki**。
抄錄為 `Lift-off | 00:00:00.6`；所有 359 頁的原始正文串流與無批註副本像素均核對，
未受影響頁面的完整畫面也保持一致。Agent 實際看的是頁索引 17、18，其他 357 頁
未作 Agent 視覺核對。原始來源不變，管理版本明確記錄相同 Length 的正規化。
最終程式雜湊 `74e3abc3…` 的安裝版 wheel（Python 3.13）與 Docker（Python 3.12）
重播也通過，完整核對相同 4 個版本、8 張圖片、批註與 Wiki；沒有從開發目錄匯入 src。

另有混合 Highlight／FreeText 案例發現 `annots=False` 仍因透明合成產生 1 色階差異。
正文驗證改用無批註的暫存讀取副本，保留精確像素比較與原生圖反向檢查；實際輸出
仍完整保有批註。一般頁面文字擷取可能包含 FreeText，不能當作未修改正文的判據。

最終程式完整測試 **3,521 項通過、33 項選配略過（698.37 秒）**，包含 Writer／中英文
字形、真實 PDF corpus 與兩種 SDK2 批註工作流。Ruff、306 個模組的型別檢查及
Bandit 中高風險門檻皆通過；Bandit 另有 185 項低風險提示保留。
VSIX **199 項測試**、64 檔套件檢查、安裝／更新與 wheel／Docker MCP stdio 均通過。
本機缺少 xvfb-run，沒有執行 VS Code 視窗啟動驗證；該項仍由遠端 CI 驗證。
文件頁面另檢查桌面／手機與中英切換，沒有橫向溢位或瀏覽器錯誤。

一般 pytest 不啟動模型。使用已登入的預設 Codex、固定雜湊原始 corpus：

```bash
uv run python -m tests.codex_pdf_annotations.run \
  --corpus /path/to/verified-corpus --case nist-1648a --output /path/to/new-run
# 第二個原始案例：--case apollo11；output 必須是新的目錄。
```

runner 不指定模型；稽核完整 contract／schema／批註／receipt 分頁與呼叫順序，
並保存模型錯誤及限制。獨立核對不等於通用閱讀器相容性或自動語意判斷。
公開版 **1.4.0**，下次整合 **1.4.1**，不逐功能跳版。

## Native Word footnote/endnote evaluation (Unreleased)

後續 CI 在 Writer 24.2.7 揭露真實內容錯配，原本的頁面斷言正確攔下。以官方 24.2.7.2
隔離程式重播相同 DOCX，確認不是空白或文字擷取差異。八次控制實驗比較定義次序與
ID 對應：正文次序的定義加上對齊的 ID，才同時通過 7.3.7 與 24.2.7。
新增明確 `remap_ids`，保留來源、原生文字／格式及歷史引用，讓 Agent 看到錯配後
執行可核對的修正；原始失敗 PDF、PNG、CI 日誌與控制實驗皆保留。

修正後實際 Codex 預設模型在 Writer 24.2.7.2 完成 **211 次成功 MCP 呼叫、2 次自行恢復
參數錯誤、282.24 秒**。錯誤分別是 contract 不適用的 text_limit，以及 schema 結束後
傳入 text_offset:null；皆保留原始紀錄。Agent 查看初始、錯配、修正後的全部 **9 張 PNG**，
獨立重播逐像素一致，並驗證 **24 份完整註解、4 份清單、13 份 contract、4 個管理版本、
兩份歷史 Wiki**。明確映射註腳 11→1、尾註 12→1／5→2，其餘 ID、文字／格式與來源保留。
已刪註腳及修正前的註腳 11／尾註 5 引用仍可依歷史版本驗證。

以 `LIBREOFFICE_BIN` 指定隔離 24.2.7.2，執行原 runner 並加 `--repair-note-ids`；
一般 pytest 不啟動模型。控制實驗採官方封存檔，SHA-256 為
`be967ebc63cb15b831b4e8176492e83eb625dc00852eb96eda2b299b6e74bb74`。
原 7.3 流程與兩輪舊模型證據仍保留，修正流程另有四版本與錯配頁面的稽核。
Python 3.10：**79 通過、1 個選配渲染跳過（28.60 秒）**；
已安裝 wheel 在 checkout 外重現 **24 份註解、4 份清單與兩份完全相同 Wiki**，
原始碼指紋與此輪 Codex 一致。

修正後全套測試 **3,403 通過、33 個選配項目跳過（426.69 秒）**，包含原本 Writer 7.3、
中英文字形及 NIST／NASA PDF；另以 Writer 24.2.7.2 通過兩種 SDK2 設定。
Docker 的已安裝程式亦重現相同 24 份註解、4 份清單及兩份 byte-identical Wiki，
與實際 Codex／wheel 的原始碼指紋一致。標準 pip 安裝、MCP stdio、套件稽核，
以及 VSIX **199 項**測試、64 檔套件檢查與安裝／更新均通過。
首次 CI 的 npm 稽核因服務維護回傳 503；服務恢復後本機兩份 npm lock 稽核皆為零漏洞，
原始失敗紀錄保留，推送後仍要求全部遠端工作成功。

以下保留先前 Writer 7.3 的開發與驗證紀錄，並非對所有閱讀器的相容性宣稱。

實際 Codex 預設模型處理一份 **三頁**合成 Word 文件，先完整讀取七個一般／特殊註解
定義、正文參照與 contract，再查看全部初始頁面。Agent 新增原生 ID 11 的註腳與
ID 12 的尾註、刪除 ID 8 的註腳，接著修正 ID 2 的文字，保留其他段落與格式。
前一版程式實測 **153 次成功 MCP 呼叫、1 次自行恢復的參數錯誤、204.28 秒**，未覆寫模型。
錯誤是在 `contract` 帶入不適用的 `text_limit`；Agent 移除後完成操作，原始錯誤保留。

獨立稽核通過 **16 份完整註解記錄、3 份清單、12 份 contract、3 個管理版本、
2 份歷史 Wiki 及全部 6 張實際 PNG**。第一頁新增註腳顯示為 1，修正後的原註腳為 2；
第三頁新增尾註顯示為 i，原尾註為 ii。原生 ID 11／12 與畫面編號明確區分。
第二頁舊註脚消失，兩個尾註標記相鄰；正文粗體、`007 µg`、`-0.50 mg/L` 與保留段落均核對。
來源 bytes／mtime、完整 XML、其他 parts、全部操作紀錄及已刪註解的歷史引用／選取均通過。

首次 SDK2 畫面測試揭露實際內容錯配：新正文註號插在前面，但新定義附在後面時，
本機 Writer 會依錯誤順序顯示註解。保留失敗檔案，分別試驗定義順序與 ID 後，
修正為將新定義放在下一個既有參照所屬定義之前；既有 ID 與相對次序不改，新增回歸測試。
MCP 仍不宣稱能自行判斷語意或證明所有閱讀器顯示一致。

較早的實際 Codex 執行也通過（**149 次成功、1 次恢復錯誤、223.72 秒**）。之後發現
只啟用註解轉接器時會與完整頁首頁尾投影共用快照身分，新增獨立
`docx-notes-content-v1` 並保留完整投影既有 bytes 相容性；因程式有修改而重跑最終實測，
沒有為清除工具錯誤而重跑。兩輪完整紀錄均保留。

```bash
uv run pytest tests/unit/test_native_docx_notes.py tests/unit/test_native_docx_note_guards.py tests/unit/test_native_docx_note_service.py tests/unit/test_codex_docx_notes_audit.py tests/integration/test_native_docx_notes_stdio.py
uv run python -m tests.codex_docx_notes.run --output /absolute/new-word-notes-run --font-fixture /absolute/pinned-font-fixture
uv run python -m tests.codex_docx_notes.audit /absolute/new-word-notes-run
python /path/to/scripts/smoke_docx_note_runtime.py /absolute/new-word-notes-run/workspace
```

前一版程式完整測試 **3,384 通過、33 個選配項目跳過（396.74 秒）**，包含 Writer／中英文字形
與 NIST／NASA PDF。Python 3.10 **60 通過、1 個選配渲染跳過（23.43 秒）**；
首次私有測試環境漏裝鎖定的 backports-asyncio-runner，補齊後通過，原始錯誤紀錄保留。
乾淨 wheel 在 checkout 外重現 16 份完整註解、3 份清單與兩份 byte-identical Wiki，
程式雜湊與最終 Codex 相同。VSIX **199 項**測試、64 檔套件檢查及安裝／更新通過；
本地 GUI activation 交由 CI 補驗。Impress／Calc 未安裝，其選配測試跳過。
標準 pip wheel 安裝與 MCP stdio 通過；Docker 的已安裝程式也重現相同 16 份註解、
3 份清單與兩份 byte-identical Wiki，程式雜湊一致。網站八個桌面／手機、中英文狀態
通過互動與溢出檢查，無 console 錯誤；本機使用快取 CDN 腳本，不代表即時 CDN 可用性。

一般 pytest 不啟動模型。此案例使用選配 Writer、固定私有字體；未驗證 Microsoft Word、
任意真實文件、所有自訂註號／特殊設定／修訂相依。MCP 提供必要版本、來源與結構檢查，
Agent 完整核對語意、視覺與修正。公開 **1.4.0**，下次整合 **1.4.1**。

## Native Word story lifecycle evaluation (Unreleased)

實際 Codex 預設模型處理一份 **四頁、三節**的合成 Word 文件，完整讀取來源頁首頁尾、
節綁定及 contract 分頁，並查看四張初始頁面。Agent 複製頁首、建立頁尾，將中間節
綁定新定義，明確保留後續節原有綁定，刪除未使用的舊定義，再修正新頁首文字。
**98 次成功 MCP 呼叫、0 次工具錯誤、222.28 秒**；未覆寫模型設定。

獨立稽核通過 **10 份完整內容記錄、3 份完整結構記錄、2 份完整 contract、3 個管理版本、
2 份歷史 Wiki 與全部 8 張實際 PNG**。來源 bytes／mtime、原生 XML、未修改 package parts、
完整操作紀錄、分頁雜湊、已刪除定義的歷史引用／文字選取，以及全部 Wiki 附件均通過。
三個版本皆為四頁；修改前後第 1、2、4 頁逐像素一致，只有第 3 頁改變。
第 3 頁保留粗體／斜體、`007` 與 `-0.50 mg/L`，新增頁尾 `Section B verified / 007 µg`；
較長的新頁首使 `KEEP-ITALIC` 換行並將後續內容下移。Agent 明確記錄這項排版變化，
沒有把結構保存說成版面完全相同。

首次獨立稽核把等價的字級數值 `9` 與 `9.0` 當作不同請求；修正稽核器的數值比較並新增
回歸測試後，同一份 98 次呼叫紀錄通過，沒有重跑模型。原始失敗紀錄保留。
新增能力也重現了 contract 回應過長而被截斷的問題；現在完整政策經過雜湊固定的
`contract_details` 分頁提供，精簡索引保留全部能力旗標與 schema 續讀資訊。
原有 Codex 稽核流程也接受唯讀的 contract 分頁；回寫與缺漏操作仍被拒絕。

```bash
uv run pytest tests/unit/test_native_docx_story_lifecycle.py tests/unit/test_native_docx_story_structure_service.py tests/unit/test_native_contract_details.py tests/unit/test_codex_story_lifecycle_audit.py tests/integration/test_native_docx_story_lifecycle_stdio.py
uv run python -m tests.codex_story_lifecycle.run --output /absolute/new-story-lifecycle-run --font-fixture /absolute/pinned-font-fixture
uv run python -m tests.codex_story_lifecycle.audit /absolute/new-story-lifecycle-run
python /path/to/scripts/smoke_docx_story_runtime.py /absolute/new-story-lifecycle-run/workspace
```

最終完整測試 **3,315 通過、33 個選配項目跳過（357.08 秒）**，包含 Writer／中英文字形
與 NIST／NASA PDF。Python 3.10 重點群組 **36 通過、1 個選配渲染項目跳過**；
乾淨 wheel 在 checkout 外重現 10 份完整內容、3 份結構記錄及兩份 byte-identical 歷史 Wiki，
程式雜湊與實際 Codex 執行相同。一般 pip 安裝／SDK2 smoke 也通過。
VSIX **199 項**測試、64 檔套件檢查與安裝／更新通過；本地 activation 由 CI 補驗。
本機沒有 Impress／Calc，相關三項選配整合測試跳過。完整測試先前遇到過期 corpus 路徑、
舊 contract 消費端及暫存空間不足；修正接線並啟用成功案例逐案清理後通過，原始錯誤紀錄保留。

一般 pytest 不啟動模型。此案例使用選配 LibreOffice Writer，沒有測試 Microsoft Word；
未涵蓋任意真實文件、所有特殊依賴的複製或註腳／尾註。MCP 核對來源、版本與結構，
Agent 負責完整語意、視覺核對及修正。公開版 **1.4.0**，變更累積於 **Unreleased／1.4.x**，
下一次統整發布為 **1.4.1**。

## Native Word header/footer evaluation (Unreleased)

實際 Codex 預設模型處理一份 **三頁、兩節**的合成 Word 文件：首頁獨立頁首、空白頁尾，
第二、三頁共用頁首頁尾；共用頁首刻意使用非標準檔名。Agent 先完整讀取節綁定與內容，
查看初始頁面，再修改共用文字、插入段落、刪除舊段落，以及更新頁碼前綴。
**75 次成功 MCP 呼叫、0 次工具錯誤、165.22 秒**，未覆寫模型設定。

獨立稽核檢查 **8 份完整頁首頁尾記錄、3 個管理版本、2 份歷史 Wiki 與全部 6 張實際 PNG**。
完整分頁雜湊、原生 XML、其他 package parts、來源 bytes／mtime、歷史引用、文字選取與
每份 Wiki 附件均通過。初始與最終首頁 PNG 相同；第二、三頁呈現修改後的共用內容，
保留粗體／斜體、`007`、`-0.50 mg/L` 與新增的 `REVIEWED 1,234.50`。
原生 `PAGE` 欄位快取保持 `1`，Writer 實際計算並呈現 `Verified page 2` 與 `Verified page 3`。
這項差異明確區分了檔案中的文字記錄與實際計算結果。

```bash
uv run pytest tests/unit/test_native_docx_stories.py tests/unit/test_native_docx_story_service.py tests/unit/test_codex_docx_stories_audit.py tests/integration/test_native_docx_stories_stdio.py
uv run python -m tests.codex_docx_stories.run --output /absolute/new-word-stories-run --font-fixture /absolute/pinned-font-fixture
uv run python -m tests.codex_docx_stories.audit /absolute/new-word-stories-run
```

一般 pytest 不啟動模型；實測使用已登入的 Codex、選配 Writer 與固定雜湊的私有字體環境。
最終程式完整測試 **3,268 通過、33 個選配項目跳過（325.91 秒）**，包含既有 Writer／中英文字形
及 NIST／NASA PDF 案例。新單元測試 **42 通過**，SDK2 兩種渲染設定 **2 通過**；
Python 3.10 **43 通過、1 個選配渲染項目跳過**。乾淨安裝的 wheel 在 checkout 外重現
8 份完整內容、2 份清單及兩份 byte-identical 歷史 Wiki，程式雜湊與實際 Codex 執行一致。

此案例沒有測試 Microsoft Word，也沒有建立／刪除整個頁首頁尾定義、重新連結節，或處理註腳／尾註。
MCP 核對來源、版本與結構；Agent 負責完整語意和視覺核對。公開版仍為 **1.4.0**，
變更累積於 **Unreleased／1.4.x**，下一次統整發布為 **1.4.1**。

## Native Word pagination evaluation (Unreleased)

實際 Codex 預設模型接收一份列高裁字、未設定重複標題的原生 Word 表格，先查看
完整資料及一張實際頁面，再調整標題前綴、內容列自動高度與列跨頁策略。
**74 次成功 MCP 呼叫、1 次恢復的輸入錯誤、200.83 秒**；未覆寫模型設定。
錯誤為 schema 讀取要求 `text_limit=12000`，超過 4000 上限；Agent 修正後完成流程，
原始錯誤及回應保留，沒有為清除錯誤而重跑模型。

修正後為 **4 頁**，每頁都有兩列標題；14 列中的每個 `END`／`CONFIRMED`、
`007`、`-0.50 mg/L`、`1,234.50` 與 `µg` 都完整呈現。
Agent 讀取兩版本完整 DFM／格網 XML／操作紀錄、查看全部 **5 張實際 PNG**，
核對舊引用、發布 DOCX 並建立兩份歷史 Wiki。獨立檢查逐像素重繪、每列頁面歸屬、
每頁標題、原生儲存格／樣式 XML、其他 package parts、來源 bytes／mtime 及所有 Wiki 附件。

這是 14 列的合成 Word 案例，證明此案例中的跨頁修正；未涵蓋超長單列、所有繼承樣式、
任意真實文件或 Microsoft Word 顯示。MCP 設定並核對屬性；完整語意與視覺判斷仍由 Agent 負責。

```bash
uv run pytest tests/unit/test_native_docx_table_layout.py tests/unit/test_codex_docx_layout_audit.py tests/integration/test_native_docx_layout_stdio.py
uv run python -m tests.codex_docx_layout.run --output /absolute/new-word-layout-run --font-fixture /absolute/pinned-font-fixture
uv run python -m tests.codex_docx_layout.audit /absolute/new-word-layout-run
```

一般 pytest 不啟動模型；實測須已登入 Codex、選配 Writer 與固定雜湊的私有字體環境。
最終程式完整測試 **3,218 通過、33 個選配項目跳過（305.27 秒）**，包含真實
Writer 頁面、中英文字形與 NIST／NASA PDF。新分頁／稽核／SDK2 群組 **34 通過**；
Python 3.10 **33 通過、1 個選配渲染項目跳過**。VSIX **199 項**測試、64 檔套件
檢查及安裝／更新通過；本地 activation 跳過，由 CI 執行。
公開版 **1.4.0**，開發累積於 **Unreleased／1.4.x**。

## Native Word grid evaluation (Unreleased)

最終程式包含可分頁讀回的完整修改紀錄。初次模型執行的 61 次成功呼叫／174.05 秒
仍保留；之後長紀錄回歸測試重現截斷問題，修正後才重新執行下列驗證，沒有隱藏原始失敗。

2026-09-19 使用真正的 Codex 預設模型，從掃描 PDF 首頁辨讀表格，建立原生 DOCX，
完成列欄插刪、尺寸調整、搬移完整段落的合併、拆分及欄寬還原。
**70 次成功 MCP 呼叫、0 次工具錯誤、162.73 秒**；模型設定未覆寫。
三個 DOCX 版本均完整讀取 DFM 與格網 XML；來源 PDF bytes／mtime、歷史引用、
未修改 package parts、前導零／正負號／千分位、富文字及 Wiki 附件通過獨立稽核。

Agent 查看一張原始掃描 PNG，以及中間／最終版本的兩張實際 Writer 頁面 PNG。
獨立重繪比較每個 RGB 像素，並檢查中文標題字形及指定字體；Agent 檢視確認最終五欄等寬、
`007`、`-0.50`、`1,234.50` 與 `mg/L` 均可見，沒有殘留暫存列欄。
此案例為單頁合成資料，未涵蓋跨頁重複標題、任意真實 Word 文件或 Microsoft Word 渲染。

```bash
uv run pytest tests/unit/test_native_docx_grid.py tests/unit/test_native_docx_grid_service.py tests/integration/test_native_docx_grid_stdio.py
uv run python -m tests.codex_docx_grid.run --output /absolute/new-word-grid-run --font-fixture /absolute/pinned-font-fixture
uv run python -m tests.codex_docx_grid.audit /absolute/new-word-grid-run
```

最終程式完整測試 **3,184 通過、33 個選配項目跳過（290.27 秒）**，包含真實
Writer 頁面、中英文字形與 NIST／NASA PDF 案例；Python 3.10 重點群組 **59 通過**。
長操作紀錄、重複檔案 SHA 的新紀錄，以及提交前讀回大小超限均有回歸測試。

一般 pytest 不啟動模型；實測要求已登入的 Codex 與選配 LibreOffice Writer。
`--font-fixture` 沿用受固定 hash 檢查的私有中英文字體，不更改系統字體設定。
MCP 負責來源／版本／結構檢查，完整語意與視覺核對由 Agent 協調。
公開版 **1.4.0**，改動累積於 **Unreleased／1.4.x**。

## Captured ETL citation evaluation (Unreleased)

2026-09-19 真實 Codex 預設模型完成一頁虛構書目 PDF 的文字／表格／圖片擷取、
三份完整證據快照、字串 `007` 的原生 Excel 儲存格，以及混合來源 APA Wiki。
**52 次成功 MCP 呼叫、2 次恢復的輸入錯誤、223.68 秒**。錯誤是在 native
`contract` 多傳了不適用的 `text_limit`；重取契約後使用 `schema` 分頁，沒有
變更模型。原始呼叫與失敗均保留，不宣稱零錯誤。

Agent 在 ETL 刪除前後共查看 **6 張實際 MCP PNG**，辨讀圖片中的 `-0.50 mg/L`，
完整讀回三類證據與書目結果；原始 PDF 的 bytes／mtime 不變。獨立稽核比較原頁
像素、前導零與儲存格型態、hash 分頁、完整快照清單、全部 Wiki 附件及重用結果。
初始稽核誤用圖像欄位 `mime_type`，且漏列唯讀 `schema` 探索；修正為實際 wire
欄位 `mimeType` 並加入回歸測試後，同一份操作紀錄通過，不重跑模型消除失敗。

```bash
uv run pytest tests/unit/test_etl_evidence.py tests/unit/test_codex_etl_csl_audit.py tests/integration/test_etl_citations_stdio.py
uv run python -m tests.codex_etl_csl.run --output /absolute/new-etl-csl-run
uv run python -m tests.codex_etl_csl.audit /absolute/new-etl-csl-run
python /path/to/scripts/smoke_etl_snapshot_runtime.py /absolute/new-etl-csl-run/workspace
```

一般 pytest 不啟動模型。快照單元 **34 passed**、真實 SDK2 擷取／歷史影像整合
**1 passed（38.65 秒）**；完整套件含 NIST／NASA corpus 為 **3,110 passed／35
optional skipped（289.41 秒）**，後補的 **7 項稽核回歸**另行通過。此合成案例
不證明任意 PDF 擷取正確性、學術書目真實性或語意支持。MCP 做必要內容／來源
檢查，完整語意及視覺核對仍由 Agent 負責。公開版維持 **1.4.0／後續 1.4.x**。

乾淨 Python 3.10 wheel 與 Docker 的已安裝程式，在 checkout 外重播相同證據，
三張歷史來源頁及整份 Wiki 位元組一致，原始碼指紋也與 Codex 實測一致。
容器以唯讀來源掛載、對應的使用者 UID 及選配 Node 執行；未放寬原檔權限。
VSIX **199 項**測試、64 檔套件檢查及安裝／更新通過，activation 留待 CI。
中英指南與 APA 預覽在桌面及手機尺寸通過瀏覽器檢查，保留六張截圖。

首次 CI 的 Python 3.10 工作揭露新整合測試誤讀 SDK 的 structured content 清單；
本地同版本重現後，改從實際 TextContent 解析影像中繼資料，並同時檢查 PNG hash
及來源引用。回歸涵蓋有／無清單包裝及影像遭改動；production 程式與既有
Codex／wheel／Docker 原始碼指紋不變。修正後 Python 3.10 的快照／稽核／SDK2
共 **44 passed（49.37 秒）**，Python 3.13 的稽核／SDK2 **10 passed（40.13 秒）**。
首輪 CI 失敗紀錄保留。

## CSL citation document evaluation (Unreleased)

2026-09-19 的真實 **Codex 預設模型**透過 MCP 完成 APA／Vancouver 引用文件與
兩份不可變 Wiki：**38 次成功呼叫、1 次恢復的工具錯誤、192.75 秒**。Agent 查看
原始及旋轉後共四張 PDF 圖像，完整讀取 contract、頁面紀錄與引用分頁，並核對
來源、APA 同作者同年 a／b 消歧義、引文順序、參考文獻及歷史引用。錯誤是抄短
native schema 雜湊，被工具拒絕後重取；不可宣稱零錯誤。來源 PDF 的 bytes／mtime
不變，舊來源修改後，原本的 APA 快照仍可原樣重用。

首輪 **167 次成功呼叫、1 次錯誤、221.2 秒**亦保留；其中含大量重複頁面讀取，
不能算成額外覆蓋。該輪超出 CSL 分頁上限後恢復；現在 MCP schema 明示上下界，
測試提示亦要求 next_text_offset 為 null 時停止。獨立稽核檢查完整讀回內容、
圖像、原檔附件、快照清單、書目值及資源雜湊；偽造摘錄或漏讀初始分頁有回歸測試。
這是明確標示虛構的兩本書／兩頁 PDF fixture，不是實際學術文獻正確性的證明。

重現方式（一般 pytest 不啟動模型；Node.js 為此排版功能的選配執行環境）：

```bash
uv run pytest tests/unit/test_csl_processor.py tests/unit/test_csl_citation_service.py tests/unit/test_codex_csl_audit.py tests/integration/test_csl_citations_stdio.py
uv run python -m tests.codex_csl.run --output /absolute/new-csl-run
uv run python scripts/smoke_csl_runtime.py
```

完整套件 **3,075 passed／35 optional skipped（221.04 秒）**，包含真實 NIST／NASA
PDF 回歸；乾淨 Python 3.10 的 CSL 單元／稽核／SDK2 共 **31 passed（23.30 秒）**。
先前完整測試揭露三個 GitHub 描述 fixture 尚未包含 CSL 文案，已同步並重跑通過。
wheel、實際 Codex、Docker 與原始碼雜湊一致。基礎容器未包含 Node.js，明確回報
未配置；唯讀掛載 Node.js 後實際 APA 排版通過。VSIX **199 項**測試與安裝／更新
通過；本機未執行 extension activation，交由 CI 環境驗證。

瀏覽器驗證涵蓋 1440×1000／390×844、中英指南切換與 APA／Vancouver 排版預覽，
檢查非空內容、無水平溢出、斜體及 APA 懸掛縮排，留存八張截圖。
這些範例不涵蓋所有期刊規則、語言或書目欄位組合；書目真實性、來源語意支持、
印刷頁碼對應與最終版面仍由 Agent 核對。公開版 **1.4.0**，功能保留於
**Unreleased／1.4.x**，沒有新增版本標籤。

## Real PDF corpus (Unreleased)

2026-09-19 的 **Codex 預設模型**直接透過本工作樹 MCP 處理以下原始公開文件，
沒有預先提供表格答案，也沒有另指定模型：

| 原始文件與範圍 | 成功呼叫／工具錯誤 | 獨立核對的資料格 | 時間 |
| --- | --- | --- | --- |
| [NIST SRM 1648a](https://tsapps.nist.gov/srmext/certificates/1648a.pdf)，PDF index 4，Table 1 全部 25 列 | 234／0 | 75／75 | 283.58 秒 |
| [NASA Apollo 11](https://ntrs.nasa.gov/citations/19700008096)，PDF indices 17、18，Table 3-I 全部 34 列 | 232／0 | 68／68 | 251.22 秒 |

NIST 是數位 PDF；NASA 是歷史掃描且含品質不佳的 OCR 層。兩份完整來源 PDF 的
大小、SHA-256、頁數均固定在 corpus manifest；不是重新製作的合成掃描。答案先從
原始圖像核對，NIST 再交叉檢查文字；保留小數精度、±、單位、上下標方法字母、
前導零、時間標點及引擎點火的 `*`。僅將排版空白與上下標依明訂規則攤平。

Agent 查看三個整頁與三個自行選取的表格區域，建立 CSV，完整讀取所有初始及
最後欄位，依序更新／還原第二欄、插列、插欄、刪列、刪欄。獨立稽核驗證每份
CSV 的七筆歷史事件、中間精確位元組、BOM／CRLF、完整操作紀錄、歷史引用、
發布內容與 Wiki 原檔附件。來源 PDF 的位元組及 mtime 不變。

每個表格頁的第一筆數值另有來源區域轉製主張，共三筆；這是抽樣來源關係覆蓋，
不代表 143 格都有逐格主張。所有 143 個資料值均與獨立答案相符。圖像稽核逐像素
比較自行建立的原始區域渲染，另保留整頁裁切差異。NASA 兩區差異均值為
4.726／3.847（0–255），來自局部掃描取樣；既有 MuPDF 限制明確保留，兩條
渲染路徑共享引擎。字元範圍及完整答案另行檢查，不宣稱兩種取樣逐像素等同。

失敗記錄也保留：NIST 首輪 75 格轉錄正確，但 Agent 以第一欄執行原本指定的
第二欄 CRUD，獨立位元組稽核拒絕該輪（237 次呼叫、256.27 秒）。重測明確指定
CSV 座標皆由 0 起算；不能將成功重測冒稱首次流程全對。NASA SDK2 首輪則揭露
359 個重複 Length 字典；現在逐一證明直接整數、原始串流內容與邊界相符，保留
來源 bytes／parser_checks，頁面複製另記錄 canonicalization repair。相衝突值、
間接 Length、其他警告仍拒絕。詳見 [格式處理](Native-File-Assets#checked-historical-pdf-syntax-unreleased)。

重現方式（PDF 保存在 Git 外；一般 pytest 不下載、不呼叫模型）：

```bash
uv run python -m tests.real_pdf.corpus --directory /absolute/corpus --fetch
ASSET_AWARE_REAL_PDF_CORPUS=/absolute/corpus uv run pytest tests/integration/test_real_pdf_corpus_stdio.py
uv run python -m tests.real_pdf.run --corpus /absolute/corpus --case nist-1648a --output /absolute/new-nist-run
uv run python -m tests.real_pdf.run --corpus /absolute/corpus --case apollo11 --output /absolute/new-nasa-run
```

CI 明確下載並核對固定來源，執行 SDK2 真實文件回歸；Python 3.10、macOS、Windows
另納入不需網路的 parser／oracle 邊界測試。局部 parser／oracle／實際 SDK2 共
**31 passed（72.10 秒）**，包含 NASA 原始頁面複製後消除重複 Length 的檢查。
完整回歸 **3,044 passed／35 optional skipped（198.26 秒）**；乾淨 Python 3.10
環境的 parser／oracle／SDK2 **31 passed（74.86 秒）**，另通過安裝 wheel 的 CLI／SDK2 smoke。
Corpus／trace／報告均明確使用 UTF-8，另新增預設非 UTF-8 環境的子程序回歸。
VSIX 199 項測試、安裝／更新與 Docker SDK2 smoke 均通過；原始碼、wheel、
實際 Agent 與容器的來源雜湊一致。
兩份文件仍不足以證明任意 PDF 的 OCR、語意、版面或回寫忠實度；跨格式總目標
繼續進行。公開版 **1.4.0**，新增工作列於 **Unreleased／1.4.x**。

## Native CSV/TSV evaluation (Unreleased)

真實 Codex **預設模型**於 2026-09-19 完成 **103 次成功 MCP 呼叫、零工具錯誤、
210.09 秒、4 張實際區域 PNG**。它自行從合成掃描 PDF 選取 Count、Reading、Unit，
建立含 UTF-8 BOM／CRLF 的 CSV，逐格保留 `007`、`-0.50`、`mg/L`，再建立三筆
區域到欄位的轉製關係。Count 區域以兩個解析度查看，來源引用保持相同。

接著完成五次原生操作：Count 改為 `008`、插入一列、插入一欄、刪除新增列與欄。
獨立稽核核對六個歷史事件的精確位元組，包含暫存列的 LF、Unicode 單位、
BOM、其餘 CRLF、字串與欄位位置；每次完整讀回操作紀錄。最後檔案 SHA 會重現
第一次修正後的內容，但保留不同操作歷史。另核對全部原始／最後六格、來源區域
實際像素與字形範圍、完整來源帳本、歷史引用、兩份 Wiki、自訂引用及精確發布 CSV。
人類來源 PDF 的位元組與 mtime 不變，舊主張不會繼承到修改後的資料。

單元與 SDK2 回歸涵蓋 UTF-8／BOM／UTF-16／CP950／CP1252／Latin-1、混合換行、
多行／空字串／空白列、不等長列、局部位元組保留、來源更新與備份回寫、dialect
分開的 Wiki、完整長欄位分頁。刪欄後僅餘空字串會補必要引號；即使重算 hash，
錯誤欄位位移或把 `007` 轉成 `7` 仍會被獨立稽核拒絕。全功能 contract／schema
探索也驗證不受回應長度截斷。

完整套件 **3,012 passed／35 optional skipped（126.86 秒）**；乾淨 Python 3.10
環境的 SDK2 與相關單元測試 **37 passed（13.91 秒）**。重現真實 Agent 流程：

```bash
uv run python -m tests.codex_delimited.run --output /absolute/new/run-dir
```

首輪遠端 CI 發現 GitHub 描述測試仍模擬舊文案；已同步 fixture 並重新通過完整
測試。CSV 回歸也加入 Python 3.10、macOS 與 Windows 的明確測試清單。
該跨版本檢查發現 Python 3.10 的 [CSV NUL 限制](https://github.com/python/cpython/issues/97503)；
現在僅在解析器呼叫期間使用不衝突的同長度字元映射，立即還原，原始位元組、
值及定位不變。實際標記字元碰撞／不同 dialect 有回歸案例，已重跑 Codex 與封裝驗證。

一般 pytest 不會啟動模型。此測試是合成掃描／CSV fixture，不能推論任意文件 OCR
或試算表顯示保真；語意審核欄位仍是 Agent 聲明，MCP 檢查可機械驗證的部分。
公開版維持 **1.4.0**，功能累積於 **Unreleased／1.4.x**。

## PDF region evidence evaluation (Unreleased)

真實 Codex **預設模型**於 2026-09-19 完成 **82 次成功 MCP 呼叫、零工具錯誤、
218.02 秒、5 張實際區域 PNG**。它從合成掃描 PDF 第一資料列自行選取 Count、
Reading、Unit 三格，建立字串 `007`、`-0.50`、`mg/L`，保留前導零與符號，
並建立三筆區域到儲存格的轉製來源關係。

Codex 將 Count 區域放大後確認引用不變，把工作簿 A2 更新成 `008`，並把受管理
PDF 第 0 頁旋轉為 90 度；來源檔未改寫。舊區域／儲存格引用仍可重讀與驗證。
兩份 Wiki 分別保留原始主張及沒有繼承主張的新版，附精確 PDF／XLSX、區域 JSON、
PNG、渲染器資訊與自訂引用。獨立稽核核對完整頁面／六格原值及新版格／帳本、
來源位元組與 mtime、三格字形涵蓋範圍、歷史、發布檔案及所有 Wiki 區域附件。

像素驗證分兩層：16 組旋轉／偏移 MediaBox-CropBox／UserUnit 案例使用整頁
raster 再裁切，比對精確向量像素；實際 Agent 的 PNG 另以獨立直接渲染精確重播，
並與整頁裁切比對尺寸及平均色差。MuPDF 對嵌入掃描影像的局部取樣／邊界抗鋸齒
可產生差異，不能把所有像素必須相同當成幾何正確的唯一條件。初版稽核因這個
假設拒絕已完成的執行，修正稽核後重審同一原始 trace 通過；回歸測試確認即使
同步重算 PNG hash，平移一個像素仍會被獨立直接重播檢查拒絕。

SDK2 整合測試直接傳輸實際 PNG，核對來源格、轉製帳本、Wiki 及 PDF 歷史；
此固定掃描格的整頁對照最大色差限制為 2／255、平均小於 0.1／255。
語意核對欄位仍是 Agent 的聲明，MCP hash 不認證語意或通用 PDF／Excel 保真。
本次是合成掃描樣本；廣泛真實文件覆蓋仍未完成。

完整測試 **2,967 項通過、35 項選配略過**，另以真實 SDK2 驗證上述流程。

重現：`uv run python -m tests.codex_pdf_regions.run --output /absolute/new/run-dir`；
普通 pytest 不啟動模型。公開版 **1.4.0**，變更累積 **Unreleased／1.4.x**。


## Worksheet layout correction evaluation (Unreleased)

選配 Calc／SDK2 測試已核對尺寸修改前後的 PDF、實際 MCP PNG、來源版本與
歷史影像。以 `NATIVE_WORKBOOK_RENDER_TEST=1` 執行
`tests/integration/test_native_worksheet_layout_stdio.py`，需安裝 Calc 或設定
`LIBREOFFICE_BIN`。固定寬高的單元測試另涵蓋富文字、Table、合併格、欄位樣式、
圖片／註解錨點、受保護工作表及預設隱藏列。

最終程式碼的真實 Codex 預設模型完成 **125 次成功 MCP 呼叫、零工具錯誤、194.47 秒、9 張實際 MCP PNG**。
它依預覽把 First／Last 的第 1 列調為 36 點，Hidden 的 A 欄設為原始 OOXML
寬度 24。重新預覽後，兩個彩色標題上緣及 Hidden 文字右緣截斷均已改善，文字完整。
獨立稽核核對四個工作簿版本、完整尺寸紀錄、所有頁面、原始儲存格及樣式、
歷史 PNG、兩份 PDF 與 Wiki 的精確來源附件；同解析度的標題彩色像素也增加。

較早一輪完成 136 次成功呼叫、170.34 秒，另有 **14 次**把 schema 分頁
`text_limit` 設為 12000 的請求被拒絕；
允許上限為 4000，contract 提供的 schema_request 為 2000。Codex 修正參數後
完成流程，稽核保留全部失敗請求。完成大量空白列查找效率修正後，以最終程式碼
重新測試得到上述 125 次零工具錯誤結果。這些測試不是 Excel 保真認證；
此次實際畫面限於這份合成工作簿，圖片／註解位置由其他單元案例驗證。

重現：`uv run python -m tests.codex_workbook_layout.run --output /absolute/new/run-dir`。
完整測試 2,931 項通過、35 項選配略過；Calc／SDK2 測試另外啟用並通過。
普通 pytest 不啟動模型。來源檔及舊 PDF 保持不變，公開版仍 **1.4.0／Unreleased 1.4.x**。

## Workbook rendition evaluation (Unreleased)

選配真實 Calc／SDK2 測試通過：四種列印／整張工作表與快取／重算組合，
核對實際 PNG 像素、列印範圍、隱藏及空白工作表、來源位元組與 mtime、歷史
版本及 Wiki 來源附件。以 `NATIVE_WORKBOOK_RENDER_TEST=1` 執行
`tests/integration/test_native_workbook_rendition_stdio.py`；需先安裝 Calc，
或設定 `LIBREOFFICE_BIN`。

2026-09-19 真實 Codex 預設模型完成 **232 次成功 MCP 呼叫、零工具錯誤、184.70 秒**，
查看十個 PDF 頁面並重看一頁，共 **11 張實際 MCP PNG**。它建立快取列印、
重算整張工作表及公式修改後三份 PDF；確認顯示結果依序為 999／3／5，完整讀取
來源引用與分頁紀錄，核對歷史儲存格，發布三份 PDF／一份 XLSX 及包含轉換紀錄的 Wiki。
獨立稽核核對來源檔未變、兩個工作簿版本、PDF 位元組、所有頁面紀錄、影像像素與 Wiki 附件。

Agent 實際指出整張工作表的標題上緣與隱藏頁文字右緣截斷；測試沒有假稱已修正。
完整頁數不等於版面保真，Calc 結果也不是 Excel 認證。上述後續尺寸修正測試已
補上這份樣本的截斷修正；更廣語料核對仍待完成。重現：`uv run python -m tests.codex_workbook_rendition.run --output /absolute/new/run-dir`。
普通 pytest 不會啟動模型。公開版 **1.4.0**，此項為 **Unreleased／1.4.x**。

## Native Table totals lifecycle evaluation (Unreleased)

實際預設模型 Codex 完成 **201 次成功 MCP 呼叫、零工具錯誤**，耗時
**181.76 秒**。透過 MCP PNG 閱讀合成掃描 PDF，建立獨立 XLSX 與原生 Table，
依序移除並清空合計列、重用保留定義新增合計列、再次移除但保留儲存格。

獨立 openpyxl／ZIP／trace 稽核核對五次歷史紀錄、每次變更之間完整的引用與
操作讀回、10 個來源資料字串／型別、欄位 ID、篩選範圍、公式及樣式。
留下的合計公式固定到移除前的絕對資料範圍，歷史 007 引用可重讀與驗證；
原始 PDF 位元組／mtime、最終 XLSX 及兩份 Wiki 的精確附件均核對通過。

最後依 Microsoft 規則修正合計列 `#This Row`／`[@欄名]` 的處理：
這些引用沒有資料列交集，保留前明確拒絕，避免把原本錯誤轉成有效座標；
最終程式碼已重新執行完整測試及實際 Codex。

全套測試 **2,834 項通過、33 項選配略過**，包含 SDK2 流程及版本衝突／
讀回容量的提交前拒絕。字型與格式的單元案例另行驗證；此次實際 Codex 流程的
直接樣式繼承只使用預設樣式，沒有驗證 Excel 畫面或公式計算結果。

重現：`uv run python -m tests.codex_table_totals.run --output /absolute/new/run-dir`。
普通 pytest 不啟動模型。公開版維持 **1.4.0**，開發累積 **Unreleased／1.4.x**。

## Native Table creation evaluation (Unreleased)

實際 Codex CLI 從 MCP PNG 閱讀合成掃描 PDF，透過 `create` 自行建立 XLSX，
再以 `add_workbook_table` 建立原生 Inventory Table。共 **73 次成功 MCP 呼叫、
零工具錯誤**，耗時 **109.47 秒**；沒有使用預先建立的 Table 範本。

獨立 openpyxl／ZIP 稽核核對 10 個來源資料字串與型別、前導零、六個欄位 ID、
Table／filter 範圍、計算欄、合計列與樣式；另核對完整分頁及操作紀錄、歷史
007 引用、原始 PDF 位元組與 mtime、兩份 Wiki 的版本與精確附件。
全套測試 **2,764 項通過、33 項選配略過**，包含 SDK2 建立／歷史流程。

建立測試也發現並修正 openpyxl 空 workbookProtection 被誤判為啟用保護；
空值／明確 false 保留，實際鎖定、密碼及未知保護仍會拒絕。沒有停用保護檢查。
此次只驗證合成掃描第一頁及建立工作流，Excel 畫面與公式計算結果尚未驗證。
重現：`uv run python -m tests.codex_table_create.run --output /absolute/new/run-dir`。
普通 pytest 不啟動模型；runner 使用預設 Codex 模型，audit 獨立核對證據。
公開版仍為 **1.4.0**，此項累積於 **Unreleased／1.4.x**。

## Native Table column editing evaluation (Unreleased)

實際 Codex CLI 完成 **66 次成功 MCP 呼叫、零工具錯誤**，耗時 **132.75 秒**。
先以真實 MCP PNG 閱讀合成掃描，再把 10 個資料格逐字轉錄為原生 Table 字串。
Agent 讀完 Table／富文字標題／引用，以一次專用操作將 Count 改名 Quantity，
保留兩個 runs 的粗體與斜體，更新計算欄公式及既有總計列，讀回完整操作紀錄。

獨立 openpyxl／ZIP 稽核核對原始字串、型別、欄位 ID、Table／filter 範圍、
run 格式、公式與名稱範圍、未修改 parts；另核對完整分頁、歷史 Count／007
引用、來源 PDF／XLSX 位元組與 mtime，以及兩份版本 Wiki／附件雜湊。
初次稽核把合法的 `schema` 呼叫誤寫成 `read_schema`；後續加入原始版本公式檢查，
又攔下操作紀錄把中間狀態記為 before 的錯誤。修正後以最終程式重新執行，確認
before 來自原版、after 來自新版。完整公開讀回的合併容量也在提交前檢查。
最終程式通過 2,716 項測試、33 項選配略過，wheel／Docker 的來源程式雜湊一致。

這次使用既有 Table 範本，不算 MCP 建表；Excel 畫面與公式計算結果尚未驗證。
重現：`uv run python -m tests.codex_table_edit.run --output /absolute/new/run-dir`。
普通 pytest 不啟動模型；runner 使用預設 Codex 模型，audit 獨立核對證據。
公開版仍 1.4.0，功能列於 Unreleased／1.4.x。

## Native Table expansion evaluation (Unreleased)

實際 Codex CLI 以 MCP SDK2 完成 **82 次成功呼叫、零錯誤**，耗時 150.48 秒。
用 MCP PNG 讀取合成掃描 PDF 第一頁，將 10 個資料格保留為原樣字串，填入既有
Inventory Table 範本。範本另含 CountLength 計算欄；沒有把範本生成算成 MCP 建表。

Agent 完整讀取原生 Table 定義與 references，投影 A2T、改 007→008、增加資料列
與 Review 欄。兩個 insert 步驟分別指定原生 part／當步 expected_ref，使用
native_generated 保留 F4 計算公式與 G1 新標題。一次原生提交後為 A1:G4；
原欄位 ID、計算欄、Table／filter 範圍、新標題 Column7、20 個來源／手動資料字串
及型別都由獨立 openpyxl／ZIP 稽核核對。

稽核同時檢查完整分頁讀取、操作紀錄、凍結輸入、仍存在的可變 A2T、歷史 007
引用、來源 PDF／XLSX 位元組與 mtime、兩份原生版本 Wiki 及附件 hash。公式結果
與原生 Excel 畫面未驗證。另有含總計列、排序、相鄰 Table、非 UTF-8 XML、
首尾邊界、樞紐／映射保護、版本衝突與錯誤生成意圖的回歸測試。

重現：`uv run python -m tests.codex_table_expansion.run --output /absolute/new/run-dir`。
runner 使用隔離設定及目前 checkout，普通 pytest 不會啟動模型；完成後使用獨立
`tests.codex_table_expansion.audit` 稽核。測試保留 default model，不自行覆寫模型。
公開版仍為 **1.4.0**，此項累積於 **1.4.x Unreleased**。

## Structural A2T writeback evaluation (Unreleased)

`tests/unit/test_native_table_grid_apply.py` 與
`tests/integration/test_native_table_grid_stdio.py` 驗證欄位改名／重建身分、刪除後
重建相同資料列、原生公式搬移、富文字／樣式、完整範圍讀回、版本衝突與舊快照。
SDK2 實際傳入 native 欄位的 JSON default_value，並核對一次原生版本提交。

```bash
uv run python -m tests.codex_native_selection.run --table-grid --output /tmp/table-grid-codex
uv run python -m tests.codex_native_selection.audit /tmp/table-grid-codex
```

2026-09-19 run 01：**86 次工具呼叫（84 次成功、2 次錯誤後恢復）、178.67 秒**。
Codex 看掃描 PNG，保留原始 007 選取證據與 derivation，在 A2T 將 B2 改為 008，
刪除／重建資料列及欄位，加入手動資料後一次套回原 XLSX。獨立稽核檢查原來
15 格與修改後 20 格字面值、列欄 ID、修改前後完整讀取、原生操作紀錄、固定
A2T 快照、原 PDF 位元組／mtime，以及兩份歷史 Wiki。舊主張沒有遷移。

兩次查詢錯誤是把 table_data／table_manage 送入 native contract.for_op；
它只接受原生操作名稱，其他工具使用 MCP 已提供的工具 schema。CLI
0.154.0-alpha.6.1 使用預設模型。這次實際模型案例沒有原生 Excel Table 物件，
也未驗證一般 OCR、公式求值或 Excel 渲染；富文字／公式保留另由原生測試覆蓋。
公開版維持 1.4.0，變更列於 Unreleased／1.4.x。

## Native worksheet grid evaluation (Unreleased)

`tests/unit/test_native_grid_*.py`、`tests/unit/test_native_workbook_grid.py`
及 `tests/integration/test_native_grid_stdio.py` 涵蓋原生列欄插刪、公式與表格
身分、合併、註解／圖形位移、具名來源、完整分頁讀回及版本衝突。使用獨立
openpyxl 讀取檢查輸出，不透過它重新儲存來源工作簿。

```bash
uv run python -m tests.codex_native_selection.run --grid --output /tmp/grid-codex
uv run python -m tests.codex_native_selection.audit /tmp/grid-codex
```

2026-09-19 run 01：**126 次 MCP 呼叫全部成功、175.95 秒**。Codex 看實際掃描
PNG，建立 15 個字面值儲存格，將 B2 的 007 改成 008，插入再刪除列欄。
獨立稽核核對每一步完整版本讀取、所有儲存格／空白位置、操作歷史、原 PDF
位元組／mtime、舊引用與 derivation，以及兩份歷史 Wiki。刪除新增的空白列欄後，
內容 SHA 恰好回到先前版本，因此仍須核對當次操作紀錄。

初版稽核誤拒先前的探索讀取；修正後允許探索，但每次修改前仍必須完整讀取
固定版本。回歸測試會拒絕漏讀當次紀錄、缺少修改前讀取或沿用舊的同 SHA 證明。
CLI 0.154.0-alpha.6.1 使用預設模型；此合成案例不代表一般 OCR、Excel 渲染、
公式求值或 A2T 結構回寫已驗證。公開版仍為 1.4.0，開發列於 Unreleased／1.4.x。

## Native A2T correspondence evaluation (Unreleased)

`tests/unit/test_native_table_*.py` 與 `tests/integration/test_native_table_stdio.py`
涵蓋 typed cells、原生格式／未修改 parts、合併與富文字保護、過期版本、獨立新建、
分頁 hash、保存／重載及可變表格刪除後的不可變快照。SDK2 透過實際 `table_data`
傳入 JSON 物件，確認工具不會把帶型別資料壓成字串。

```bash
uv run python -m tests.codex_native_selection.run --tables --output /tmp/a2t-codex
uv run python -m tests.codex_native_selection.audit /tmp/a2t-codex
```

2026-09-19 run 01：**90 次 MCP 呼叫（89 次成功、1 次錯誤後恢復）、145.14 秒**。
Codex 看實際掃描 PNG、建立 15 個字面值儲存格、投影為 A2T、將 B2 的字串 007
改成 008，再套回原工作簿並從固定快照另建 XLSX。原 PDF 位元組／mtime、完整
修改前後讀回、原生來源引用、A2T 快照、工作簿歷程、發布檔及兩份歷史 Wiki
均通過獨立稽核。一次錯誤是 schema 的 text_limit=20000 超過 4000 上限；
Codex 改用合法分頁後完成。稽核測試會拒絕事後補讀、漏讀快照或偽造 hash。

CLI 0.154.0-alpha.6.1 使用預設模型；此合成案例不代表一般 OCR、公式求值或
Excel 渲染已驗證。舊的 007 主張不會遷移到 008；新工作簿版面另行核對。
公開版仍為 1.4.0，開發列於 Unreleased／1.4.x。

## Native workbook structure evaluation (Unreleased)

執行 `tests/unit/test_native_workbook_*.py`、`tests/unit/test_codex_workbook_audit.py`
及 `tests/integration/test_native_workbook_stdio.py`，涵蓋真實 XLSX 的公式、樣式、
註解、合併格、圖表、樞紐／合併計算引用、3D 範圍、版本與來源保護。SDK2 測試
讀完分頁清單，執行工作表 CRUD，再以獨立讀取器核對輸出與歷史選取引用。

實際模型測試需明確執行：

```bash
uv run python -m tests.codex_native_selection.run --worksheets --output /tmp/workbook-codex
uv run python -m tests.codex_native_selection.audit /tmp/workbook-codex
```

2026-09-19 的 run 01 完成 **115 次 MCP 呼叫、0 次工具錯誤、160.49 秒**。
Codex 看掃描頁 PNG、轉出 15 個保留字面值的 XLSX 儲存格，保留原始 007 選取引用，
更新為 008，再新增 Review／Temporary、加入跨表公式、將來源表改名為
`資料 O'Brien`、重排並刪除 Temporary。七個受管理版本的原表格內容、穩定身分、
公式引用、未改 parts、完整修改前後讀回、原 PDF 位元組／mtime、發布檔及兩份
Wiki 都由獨立稽核核對。稽核另有拒絕事後補讀、偽造版本轉移或 hash 的回歸測試。
Codex CLI 0.154.0-alpha.6.1 使用預設模型，沒有固定模型版本。

這是合成掃描案例，不代表一般 OCR、Excel 渲染或公式求值已驗證。來源為整頁引用，
產物為精確文字選取；舊主張不遷移到新版。公開版保持 1.4.0，功能列於 Unreleased／1.4.x。


## Native selection evaluation (Unreleased)

```bash
uv run pytest tests/unit/test_native_selection.py tests/unit/test_native_selection_service.py tests/unit/test_codex_selection_audit.py tests/integration/test_native_selection_stdio.py -q
uv run python -m tests.codex_native_selection.run --output /tmp/selection-codex
uv run python -m tests.codex_native_selection.audit /tmp/selection-codex
```

2026-09-19 實際 Codex run 01：**58 次 MCP 呼叫、零工具錯誤、130.45 秒**。
Codex 看見真實掃描 PNG，轉錄完整 15 格 XLSX 表格，保留字串型別與前導零；
建立 B2 的精確文字引用，再改為 008。舊引用仍保留 007 並驗證為歷史資料，
歷史 Wiki 帶有選取 JSON、完整來源 PDF 與帳本；新版 Wiki 不繼承舊主張。
獨立稽核比對完整像素、每格值、來源 bytes／mtime、分頁讀回雜湊、版本與附件。
另以重算雜湊的偽造位置／上下文／值測試稽核器，確保不只相信 Agent 的結語。

SDK2 測試以合併標題的 PPTX 表格核對精確 run 選取、修改後歷史引用與來源不變。
四種父格式、Unicode codepoint／UTF-8 範圍、空值型別、錯誤位置、分頁大小、
帳本與不可變 Wiki 均有回歸測試。CLI 使用現有登入狀態及預設模型，未固定模型；
一般 pytest 不啟動模型。本評估為合成資料，不代表一般 OCR、像素區域證據、
Excel 視覺保真或跨儲存格自動對應已完成。公開版仍 1.4.0／後續 1.4.x。

## CJK font correction evaluation (Unreleased)

The first Writer evaluation found boxes for 「研究」. No Chinese font was available;
Arial resolved to Liberation Sans. Even those boxes had nonzero PDF glyph IDs and
misleading Unicode mappings, so text extraction alone could not prove appearance.
The opt-in Linux fixture below supplies pinned Noto Sans TC Regular/Bold and copied
local Liberation Sans faces. It retains both licenses, hashes all font/configuration
bytes and includes only those font directories; global settings and DOCX run fonts
remain unchanged. A changed or unexpected font file causes the audit to fail.

```bash
# Requires Linux, Fontconfig, Liberation Sans and LibreOffice Writer.
uv run python -m tests.codex_docx_structure.fonts --output /tmp/docx-review-fonts
NATIVE_DOCX_FONT_FIXTURE=/tmp/docx-review-fonts uv run pytest tests/integration/test_native_docx_cjk_stdio.py -q
LIBREOFFICE_BIN=/usr/bin/libreoffice uv run python -m tests.codex_docx_structure.run --render --font-fixture /tmp/docx-review-fonts --output /tmp/docx-codex-cjk
uv run python -m tests.codex_docx_structure.audit /tmp/docx-codex-cjk
```

The setup command explicitly downloads about 11 MiB from the official
[Noto Sans 2.004 source](https://github.com/notofonts/noto-cjk/tree/523d033d6cb47f4a80c58a35753646f5c3608a78/Sans/SubsetOTF/TC),
verifies fixed hashes and copies installed Latin fonts. Keep the generated directory
for replay; choose a new directory to rebuild. No fonts are bundled in this project,
and ordinary pytest never downloads them. The runner forwards the private
[Fontconfig configuration](https://fontconfig.pages.freedesktop.org/fontconfig/fontconfig-user.html)
to its MCP process; the auditor restores the same recorded environment and checks
its hashes before and after rendering. Fontconfig cache UUIDs are permitted without
relaxing font-content checks. This does not standardize other platforms or scripts.

CJK run 01 on 2026-09-19 completed **49 MCP calls with zero tool errors**, one scan
PNG and two Word page PNGs at current/historical revisions. Codex reported readable
Chinese glyphs in both images; it preserved exact table values and saw no clipping.
Independent rendering matched every delivered RGB pixel and confirmed both Chinese
codepoints using distinct glyphs from the supplied Noto face. The separate SDK2
regression compares missing-font and corrected renderings of **identical DOCX bytes**
and preserves source bytes/mtime. Native content, five complete DFM revisions,
historical references, publication and wiki attachments also passed the model audit.

These are complementary checks: parsed text/font identities are mechanical evidence;
actual appearance is reviewed by the Agent. Word compatibility, different installed
fonts, repeated-header pagination and real-corpus coverage still require evaluation.
The original missing-glyph run below is retained as historical evidence; the private
fixture corrects that case without changing the machine's default font environment.
Public remains **1.4.0**, with new work Unreleased for **1.4.x**.

Local CJK gates passed **2,221 Python tests** (33 optional skips), the **37-test**
focused run including actual CJK SDK2 images, **199 extension tests**, lint/type,
workflow/dependency/harness checks and desktop/mobile zh/en browser review. Runtime
source and dependencies are unchanged from the previously verified page renderer.

## DOCX page rendering evaluation (Unreleased)

Add `--render` to `tests.codex_docx_structure.run` to make Codex view every page
of the final DOCX and the historical revision with the temporary `008` Count.
The isolated MCP server receives an explicit `LIBREOFFICE_BIN` when set. The
independent auditor reconverts exact stored bytes, checks every delivered RGB
pixel and verifies complete page coverage, revision identity, PNG hashes,
continuation, renderer metadata and the Agent's stated review scope.

```bash
NATIVE_DOCX_RENDER_TEST=1 uv run pytest tests/integration/test_native_docx_render_stdio.py -q
LIBREOFFICE_BIN=/usr/bin/libreoffice uv run python -m tests.codex_docx_structure.run --render --output /tmp/docx-codex-render
uv run python -m tests.codex_docx_structure.audit /tmp/docx-codex-render
```

Rendering run 01 on 2026-09-19 completed **47 MCP calls with zero tool errors**:
one source scan PNG and two Writer page PNGs across final/historical revisions,
with complete DFM reads for all five managed revisions. All delivered Word pixels
matched independent rendering. Table strings, merged title/grid, `007` versus
`008`, source integrity, published bytes and wiki attachments passed the audits.
Agent review detected **missing Chinese heading glyphs** on this machine; both
Writer previews showed boxes for 「研究」 while the stored text was correct. This
is an unresolved local font limitation, not a Word fidelity pass. Install suitable
fonts in the rendering environment and repeat visual review before relying on
those glyphs. The separate real SDK2 test covers two pages, headers/footers and
historical/current previews; the synthetic Codex document was one page per revision.
Neither check establishes Microsoft Word fidelity or real-corpus coverage.

Final page-preview gates on 2026-09-19 passed **2,210 Python tests** (32 optional
skips; Writer and Impress SDK2 image tests also passed separately), **199 extension
tests**, source/type/security/dependency checks, clean-wheel CLI/SDK2, Docker
CLI/SDK2, artifact audits and fresh/update VSIX install. Local GUI activation was
unavailable; remote CI covers that check. Public remains 1.4.0, with no new tag.

## Native DOCX structure evaluation (Unreleased)

The real Codex CLI can transcribe a synthetic scanned PDF page into a newly created,
editable DOCX table, change and restore a cell, insert/delete disposable body blocks,
verify historical references, and publish a wiki snapshot. Ordinary pytest never
starts Codex; this runner uses the existing logged-in CLI without reading credentials
or changing persistent configuration. Only the native document MCP tool is enabled.

```bash
uv run pytest tests/unit/test_native_docx_structure.py tests/unit/test_native_docx_structure_guards.py tests/unit/test_native_docx_structure_operations.py tests/integration/test_native_docx_structure_stdio.py -q
uv run python -m tests.codex_docx_structure.run --output /tmp/docx-codex-structure
uv run python -m tests.codex_docx_structure.audit /tmp/docx-codex-structure
```

The independent auditor checks actual source PNG pixels, exact strings, leading
zeros, run formatting, column/row grids, merges, managed history, complete DFM reads
before edits, full references, source bytes/mtime and wiki part attachments. This
does not establish full Word rendering fidelity or real-corpus coverage. Public
version remains 1.4.0; new features accumulate Unreleased for 1.4.x.

Run 01 on 2026-09-19 completed **45 MCP calls with zero tool errors**, one actual
source PNG and complete DFM readback for all five managed DOCX revisions. Exact
transcription, leading zeros, half-point Arial runs, merged title/grid, temporary
insert/delete, old evidence, published bytes and all 17 wiki package attachments
passed independent checks. Codex also exported a source PDF wiki and verified a
whole-file reference; the auditor accepts these additional valid outputs. It
explicitly reported that DOCX page rendering/page flow were not reviewed.


Final local gates passed on 2026-09-19: **2,156 Python tests passed, 31 optional
skipped**; extension **199 passed**. Ruff, mypy, dependency/security gates, Docker
CLI/SDK2 stdio, fresh/update VSIX install and clean-wheel CLI/stdio checks passed.
Local GUI activation was unavailable; CI runs that check. No public version bump.

## Whole-slide rendering evaluation (Unreleased)

Use `--render` with `tests.codex_pptx_tables.run` to make the real Codex CLI view
both the final slide and a historical slide through `render_pptx_slide`.
The runner forwards an explicitly set `LIBREOFFICE_BIN` to its isolated MCP server.
The auditor independently converts the exact stored PPTX revisions with LibreOffice,
uses raw ZIP slide relationships and PyMuPDF, and compares every delivered RGB pixel.
It checks revision/slide identity, image hashes, actual MCP image delivery and the
Agent's declared review scope. Agent observations remain judgments, not machine proofs.

Run 01 on 2026-09-19 completed **78 MCP calls with zero tool errors**, exact first
scan transcription, five complete native records and three actual images: one PDF
page and two whole-slide previews at distinct revisions. Source bytes/mtime,
published PPTX, history, old references and wiki checks passed. Codex identified
that a historical native `008` edit was hidden by a second overlapping table, so
both screenshots visibly showed `007`. It also reported that the new table's blue
style and equal column widths differed from the scanned original. This illustrates
why XML readback and visual review answer different questions.

The local renderer was LibreOffice 7.3.7 with matching Ubuntu Impress/Draw modules in
a private test overlay; the installed system originally had Writer only. No system
installation was changed. An SDK2 integration test separately checks hidden-slide
and reordered-slide colors plus historical image stability; enable it with
`NATIVE_PPTX_RENDER_TEST=1` and a usable Impress installation. CI installs Impress
for that test. Ordinary pytest never starts Codex. Full local suite: **2,095 passed,
30 optional skipped**; extension: **199 passed**. No PowerPoint, animations, media
playback, general OCR or real-corpus coverage is claimed. Public version stays 1.4.0.

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
