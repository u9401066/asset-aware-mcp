# 貢獻指南

感謝你有興趣為此專案做出貢獻！

## 如何貢獻

### 回報問題 (Bug Report)

1. 先搜尋現有 Issues，確認問題未被回報
2. 使用 Issue 模板提交問題
3. 提供清晰的重現步驟

### 功能建議 (Feature Request)

1. 先搜尋現有 Issues
2. 描述功能的使用場景
3. 說明期望的行為

### 提交程式碼 (Pull Request)

#### 開發流程

1. Fork 此專案
2. 建立功能分支：`git checkout -b feature/your-feature`
3. 遵循專案架構（參見 `CONSTITUTION.md`）
4. 提交變更：`git commit -m 'feat: add your feature'`（commit hook 會跑 `pretest.py --quick`）
5. 推送分支：`git push origin feature/your-feature`（pre-push hook 會跑完整 CI 對等檢查）
6. 建立 Pull Request

#### Commit 訊息格式

遵循 Conventional Commits：

```
<type>(<scope>): <subject>

<body>

<footer>
```

類型：
- `feat`: 新功能
- `fix`: 修復
- `docs`: 文檔
- `refactor`: 重構
- `test`: 測試
- `chore`: 雜項

#### 本機 CI 對等檢查（push 前必跑）

GitHub Actions 依秒計費，CI 能抓到的問題要先在本機抓到。`scripts/pretest.py`
直接讀取「受測 commit」的 `.github/workflows/ci.yml`（全部 job）與
`release.yml` 的 `test` job，逐步執行相同的 `run:` 指令，並使用 workflow 釘選的
uv／Node／Python 版本：

- `ubuntu-latest` 的 job 在 WSL `Ubuntu-26.04`（與 GitHub ubuntu-latest 相同的
  Ubuntu 26.04、LibreOffice 26.2.7.3）內執行；每個 job 在 `/home/runner/aam-ci`
  有自己的乾淨 checkout，不會碰到 Windows 工作目錄或 `.venv`。workflow 沒安裝
  LibreOffice 的 job 會看不到 LibreOffice，與乾淨 runner 一致。
- `windows-latest` 的 job 在本機 Windows 的乾淨 checkout 執行（預設 `C:\aamg`，
  可用 `git config pretest.windowsTemp` 改），使用短 ASCII `TEMP` 與 `--basetemp`，
  以及設定的 Node。GitHub 的 Windows runner 已啟用 Win32 長路徑；本機若
  `LongPathsEnabled=0`，內容雜湊命名的 Wiki／證據路徑會超過 260 字元，gate 會讓
  pytest 的 `--basetemp` 使用 `\\?\` 長路徑前綴（只解除 MAX_PATH，全部測試照跑）
  並在表格註明。以系統管理員執行
  `reg add HKLM\SYSTEM\CurrentControlSet\Control\FileSystem /v LongPathsEnabled /t REG_DWORD /d 1 /f`
  後就不需要這個前綴。
- macOS job 無法在本機執行，表格會標示 **NOT VERIFIED** 與原因，不會靜默略過。
- uv／Node／LibreOffice 版本不符、缺少 WSL distro 或套件時，相關 job 直接
  FAIL 並提示修正方式。

一次性設定（Windows）：

```powershell
wsl --install -d Ubuntu-26.04                    # 若尚未安裝
python scripts/pretest.py --setup-wsl            # 冪等；安裝 CI 用的 apt 套件、uv、Node
git config --local pretest.windowsNode "C:\path\to\node22"   # 預設 PATH 的 Node 太舊時
git config --local pretest.windowsNodeMajor 22   # 明確接受 Windows 端比 CI（24）舊的 Node
uvx --from uv==0.12.3 uv run --frozen pre-commit install --hook-type pre-commit --hook-type pre-push --hook-type commit-msg
```

日常使用：

```bash
python scripts/pretest.py --quick      # commit 時自動執行：ruff/format/mypy/bandit/zizmor/uv lock/文件/資產同步
python scripts/pretest.py              # push 時自動執行：所有 CI job，最後輸出 CI job → 本機結果對照表
python scripts/pretest.py --only integration-tests --skip windows-smoke
python scripts/pretest.py --rev HEAD~1 # 驗證指定 commit（預設為工作目錄快照）
python scripts/pretest.py --list       # 只看 job 對應；--dry-run 會列出每個 step 的處理方式
```

`uses:` action 以「驗證它會安裝的工具版本」模擬；`apt-get install` step 改為
驗證套件已安裝（由 `scripts/setup_local_ci_wsl.sh` 安裝）。只在 GitHub 有意義的
release tag 驗證 step 會標示 N/A 並改做版本一致性檢查。紀錄檔與 `summary.json`
位於 `%LOCALAPPDATA%\aam-pretest\runs\`。GitHub 把 `ubuntu-latest` 換到新映像時，
請同步更新 `scripts/pretest.py` 的 `UBUNTU_LATEST`、WSL distro 並重跑 `--setup-wsl`。

#### 程式碼規範

- 遵循 DDD 架構（參見 `.github/bylaws/ddd-architecture.md`）
- DAL 必須獨立
- 提交前更新相關文檔

### 審查流程

1. 自動化檢查通過（push 前本機 `python scripts/pretest.py` 已全綠）
2. 至少一位維護者審查
3. 所有討論已解決
4. 文檔已更新

## 行為準則

請參閱 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

## 問題？

如有任何問題，歡迎開 Issue 討論！
