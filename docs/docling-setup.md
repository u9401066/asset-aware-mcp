# Docling Engine Setup (High-Fidelity PDF → Assets)

The **Docling** engine gives Asset-Aware MCP high-fidelity PDF extraction:
semantic **figures with bound captions**, **table structure**, **reading order**,
and formula/heading recovery — far beyond the fast PyMuPDF default. It is
**MIT-licensed** (clean for commercial use) and runs on **CPU**.

This guide lets **any agent** (CLI, VS Code, Cline, Codex, or any MCP client)
install it on **Windows / macOS / Linux** with a single command.

---

## TL;DR — one command

| Environment | Command |
|-------------|---------|
| **Any OS, with uv** (recommended) | `uv run python scripts/setup_docling.py` |
| **Linux / macOS** | `python3 scripts/setup_docling.py` &nbsp;or&nbsp; `bash scripts/setup_docling.sh` |
| **Windows** | `python scripts\setup_docling.py` &nbsp;or&nbsp; `powershell -ExecutionPolicy Bypass -File scripts\setup_docling.ps1` |

Then select the engine:

```bash
export ETL_ENGINE=docling        # macOS/Linux
$env:ETL_ENGINE="docling"        # Windows PowerShell
```

That's it. The MCP server auto-detects the installed engine — **no path
configuration needed**.

---

## Why an isolated environment?

Docling depends on `torch`, which:

- has **no wheels for pre-release Python** (e.g. `3.11.0rc1`), and
- pulls **CUDA packages by default**, which fail/waste space on CPU-only hosts.

So the installer creates an **isolated** environment named `.venv-docling`
(stable Python + CPU-only torch). The MCP server — running on **any** Python —
calls Docling through a **subprocess bridge**, so heavy `torch` never enters the
server process. This keeps the server lightweight and OOM-safe.

```
┌──────────────────────────┐        subprocess         ┌───────────────────────┐
│  Asset-Aware MCP server   │  ───────────────────────► │  .venv-docling         │
│  (any Python, no torch)   │   pdf path + out dir      │  (Python 3.12 + torch) │
│  DoclingExtractor.parse() │  ◄─────────────────────── │  docling worker        │
└──────────────────────────┘   result.json + images/   └───────────────────────┘
```

---

## Install by agent / tool

All paths are relative to the repository root.

### CLI agents (bash / zsh / any shell)

```bash
uv run python scripts/setup_docling.py         # preferred (uv handles CPU torch)
# or, without uv:
python3 scripts/setup_docling.py               # Linux/macOS
bash scripts/setup_docling.sh                   # wrapper (auto-detects python)
```

### VS Code (Copilot agent, terminal, or task)

Run in the integrated terminal:

```bash
uv run python scripts/setup_docling.py
```

Or add a one-off task (`.vscode/tasks.json`):

```json
{ "label": "Install Docling Engine", "type": "shell",
  "command": "uv run python scripts/setup_docling.py" }
```

### Cline / Codex / other MCP dev tools

Run the same command in their terminal step. The installer is **idempotent**:
re-running it is a fast no-op when the engine is already healthy, so it is safe
to include in a bootstrap step.

```bash
uv run python scripts/setup_docling.py
```

### Windows (PowerShell)

```powershell
python scripts\setup_docling.py
# or the wrapper:
powershell -ExecutionPolicy Bypass -File scripts\setup_docling.ps1
```

---

## Verify

```bash
python3 scripts/setup_docling.py --check      # Linux/macOS
python  scripts\setup_docling.py --check      # Windows
```

Expected output ends with:

```
[OK] Docling engine is READY.
DOCLING_PYTHON_PATH=/abs/path/.venv-docling/bin/python
```

---

## Configuration (optional)

The adapter resolves the isolated interpreter in this order:

1. **`DOCLING_PYTHON_PATH`** environment variable (explicit override).
2. **`docling_python_path`** setting (from `.env` / `Settings`).
3. **`./.venv-docling`** auto-detected in the project root
   (`bin/python` on POSIX, `Scripts\python.exe` on Windows).

So the default install needs **no configuration**. Override only for a custom
location:

```bash
export DOCLING_PYTHON_PATH=/opt/docling-venv/bin/python     # macOS/Linux
$env:DOCLING_PYTHON_PATH="C:\docling-venv\Scripts\python.exe" # Windows
```

Other knobs:

| Variable | Default | Purpose |
|----------|---------|---------|
| `ETL_ENGINE` | `pymupdf` | Set to `docling` to select this engine |
| `DOCLING_TIMEOUT_SECONDS` | `900` | Hard wall-clock cap per document |
| `DOCLING_PYTHON_PATH` | (auto) | Explicit isolated interpreter path |

---

## Installer options

```
python scripts/setup_docling.py [--check] [--force] [--venv PATH] [--no-uv]
```

| Flag | Effect |
|------|--------|
| `--check` | Diagnostics only; no changes. Exit 0 = ready, 1 = not installed |
| `--force` | Recreate the environment from scratch |
| `--venv PATH` | Install into a custom location (remember to set `DOCLING_PYTHON_PATH`) |
| `--no-uv` | Force the stdlib `venv` + `pip` path (skip uv) |

---

## How it works (for maintainers)

- `scripts/setup_docling.py` — cross-platform installer (pure stdlib; prefers
  `uv`, falls back to `venv` + `pip`; installs CPU torch from
  `download.pytorch.org/whl/cpu`; verifies `import docling`).
- `scripts/setup_docling.sh` / `.ps1` — thin wrappers that locate a Python
  interpreter (`python3`/`python`/`py`) and forward to the installer.
- `src/infrastructure/docling_adapter.py` — the adapter. `parse()` dispatches to
  **direct** mode (docling importable in-process) or **subprocess** mode
  (runs `python -m src.infrastructure.docling_adapter <pdf> <out>` under the
  isolated interpreter). The worker serialises a `MarkerParseResult` to
  `result.json` + `images/`; the server rebuilds it. Image bytes cross the
  process boundary as files, so figures survive intact.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `No Python interpreter found` | No `python`/`python3`/`py` on PATH | Install Python 3.12 from python.org, or install [uv](https://astral.sh/uv), then re-run |
| `torch ... no wheel for the current platform` | Pre-release/edge Python | The isolated venv uses stable Python 3.12; run the installer (do **not** install docling in the main env) |
| `403 Forbidden ... nvidia-*` | Resolver pulled CUDA torch | The installer uses `--torch-backend cpu` / the CPU index; re-run `python scripts/setup_docling.py --force` |
| Docling engine `SKIPPED` in tests | `.venv-docling` absent | `python scripts/setup_docling.py`, then re-run tests |
| `Docling worker timed out` | Very large/slow PDF on CPU | Raise `DOCLING_TIMEOUT_SECONDS`, or use a machine with more cores |
| `Input document ... is not valid` | Corrupt/placeholder PDF | Use a valid PDF; the error is surfaced as `DoclingParseError` |

Full diagnostics:

```bash
python scripts/setup_docling.py --check
```

---

## Uninstall

Delete the isolated environment (it is git-ignored):

```bash
rm -rf .venv-docling          # macOS/Linux
Remove-Item -Recurse -Force .venv-docling   # Windows
```

Set `ETL_ENGINE=pymupdf` (the default) to fall back to the fast engine.
