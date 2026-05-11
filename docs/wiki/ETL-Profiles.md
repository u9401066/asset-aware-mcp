# ETL Profiles

![ETL profiles overview](assets/etl-profiles.jpg)

## 目的

ETL profile 控制 heading detection、caption/table/figure filters、section keyword、numbered section pattern 與出版格式差異。它讓同一套 PDF ingest pipeline 可以適應 arXiv、Nature、IEEE、Elsevier 等格式。

來源：`src/domain/etl_profile.py`、`src/presentation/tools/profile_tools.py`。

## 內建 profiles

| Profile | 說明 |
|---|---|
| `default` | 通用 PDF |
| `arxiv` | double-column、bold numbered sections、通常沒有 PDF TOC |
| `nature` | Nature/Scientific Reports，single-column、大圖 |
| `ieee` | double-column、Roman numeral sections |
| `elsevier` | single-column、numbered sections、highlights |

## Tools

| Tool | 用途 |
|---|---|
| `list_etl_profiles` | 列出 profiles |
| `get_etl_profile` | 檢視 profile |
| `get_current_etl_profile` | 查詢 active profile |
| `set_etl_profile` | 切換 active profile |
| `load_etl_profile_from_json` | 載入自訂 JSON profile |
| `etl_profile` | consolidated profile entrypoint |

## 自訂 profile

JSON profile 可繼承 built-in base，並覆寫：

- font thresholds
- heading noise patterns
- section keywords
- table/figure caption regex
- min figure/table filters
- numbered section regex

Profile 切換會影響後續 ingest；已建立的 background job 應保存 job creation 時的 profile context，避免中途切換造成 drift。
