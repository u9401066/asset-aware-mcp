# GitHub CLI 團隊操作文件

> 常用 `gh` 指令整理，供團隊日常維護使用。

---

## 前置條件

```bash
# 安裝 gh CLI
# macOS: brew install gh
# Ubuntu: sudo apt install gh
# 或 https://cli.github.com/

# 登入
gh auth login

# 驗證
gh auth status
```

---

## 1. Repository 管理

### 檢視 Repo 資訊

```bash
# 基本資訊
gh repo view

# JSON 格式（程式化使用）
gh repo view --json description,repositoryTopics,url

# 列出所有 release
gh release list
```

### 更新 Repo Description & Topics

```bash
# 使用專案腳本（推薦）
./scripts/gh_update_repo_metadata.sh

# 或手動更新
gh repo edit u9401066/asset-aware-mcp \
  --description "your new description" \
  --add-topic segmentation \
  --add-topic ocr \
  --remove-topic old-topic
```

---

## 2. Issue 管理

### 建立 Issue

```bash
# 互動式
gh issue create

# 一行指令
gh issue create --title "Bug: ..." --body "描述" --label bug

# 從檔案
gh issue create --title "Feature request" --body-file docs/proposal.md --label enhancement
```

### 查詢 Issue

```bash
# 列出所有 open issues
gh issue list

# 篩選 label
gh issue list --label "bug"
gh issue list --label "v0.7.0"

# 搜尋
gh issue list --search "segmentation"

# 檢視特定 issue
gh issue view 42
```

### 批次更新 Issue

```bash
# 使用專案腳本（推薦）
./scripts/gh_update_issue_or_pr.sh issue 42 --body "new body" --add-label bug
./scripts/gh_update_issue_or_pr.sh issues 1,2,3 --add-label "v0.7.0"

# 手動更新
gh issue edit 42 --body "Updated description" --add-label enhancement
gh issue edit 42 --title "New title" --add-assignee username
gh issue edit 42 --milestone "v0.7.0"
```

### 關閉 / 重開

```bash
gh issue close 42 --comment "Fixed in v0.6.2"
gh issue reopen 42
```

---

## 3. Pull Request 管理

### 建立 PR

```bash
# 互動式
gh pr create

# 一行指令
gh pr create --title "feat: add segmentation" --body "描述" --label enhancement

# draft PR
gh pr create --draft --title "WIP: new feature"
```

### 查詢 PR

```bash
# 列出所有 open PRs
gh pr list

# 檢視特定 PR
gh pr view 10

# 檢查 CI 狀態
gh pr checks 10
```

### 更新 PR

```bash
# 使用專案腳本
./scripts/gh_update_issue_or_pr.sh pr 10 --body-file docs/pr-body.md --add-label enhancement

# 手動更新
gh pr edit 10 --body "Updated description" --add-label bug-fix
gh pr edit 10 --title "feat: improved segmentation"
```

### 合併 PR

```bash
# 預設 merge commit
gh pr merge 10

# squash merge（推薦）
gh pr merge 10 --squash --delete-branch

# rebase merge
gh pr merge 10 --rebase
```

---

## 4. Release 管理

### 檢視 Release

```bash
# 列出所有 release
gh release list

# 檢視特定 release
gh release view v0.6.2

# JSON 格式
gh release view v0.6.2 --json tagName,publishedAt,body
```

### 建立 Release（自動化推薦）

本專案使用 tag-driven release workflow，推送 tag 即自動觸發：

```bash
# 推送 tag → 自動觸發 GitHub Actions release
git tag v0.7.0
git push origin v0.7.0

# 檢查 workflow 狀態
gh run list --workflow=release.yml --limit 3
gh run view <run-id>
```

### 手動建立 Release（非常規情況）

```bash
gh release create v0.7.0 \
  --title "v0.7.0" \
  --notes-file CHANGELOG.md \
  --target master
```

---

## 5. GitHub Actions / CI

### 檢視 Workflow

```bash
# 列出最近的 workflow runs
gh run list --limit 10

# 篩選特定 workflow
gh run list --workflow=ci.yml --limit 5
gh run list --workflow=release.yml --limit 5

# 檢視 run 詳情
gh run view <run-id>

# JSON 格式（程式化）
gh run view <run-id> --json conclusion,status,jobs
```

### 重新觸發

```bash
# 重跑失敗的 jobs
gh run rerun <run-id> --failed

# 重跑整個 workflow
gh run rerun <run-id>
```

---

## 6. Label 管理

### 列出所有 Label

```bash
gh label list
```

### 建立 Label

```bash
gh label create "v0.7.0" --color "0E8A16" --description "v0.7.0 milestone"
gh label create "segmentation" --color "1D76DB" --description "Segmentation export feature"
```

### 刪除 Label

```bash
gh label delete "old-label" --yes
```

---

## 7. 搜尋

### 搜尋程式碼

```bash
gh search code "ReadingOrderPolicy" --repo u9401066/asset-aware-mcp
```

### 搜尋 Issues / PRs

```bash
gh search issues "segmentation" --repo u9401066/asset-aware-mcp
gh search prs "OCR" --repo u9401066/asset-aware-mcp
```

---

## 8. 快速參考

| 操作 | 指令 |
|------|------|
| 更新 repo 說明 | `./scripts/gh_update_repo_metadata.sh` |
| 批次更新 issue | `./scripts/gh_update_issue_or_pr.sh issues 1,2,3 --add-label v0.7.0` |
| 檢查 CI 狀態 | `gh run list --limit 5` |
| 建立 release | `git tag v0.x.x && git push origin v0.x.x` |
| 搜尋 issue | `gh issue list --search "keyword"` |
| 查看 repo 資訊 | `gh repo view --json description,repositoryTopics` |
