#!/usr/bin/env python3
"""Local CI-parity gate: run the GitHub Actions jobs before pushing.

The gate reads ``.github/workflows/ci.yml`` (every job) and the ``test`` job of
``release.yml`` from the commit under test and executes their ``run:`` steps
verbatim, with the same tool pins, environment variables and Ubuntu image:

* ``ubuntu-*`` jobs run in the WSL distro provisioned by
  ``scripts/setup_local_ci_wsl.sh`` (natively when this host is Linux), each in
  its own clean checkout on the distro's ext4 filesystem;
* ``windows-*`` jobs run on this Windows host in a clean checkout with a short
  ASCII TEMP and ``--basetemp`` and the configured Node.js;
* jobs needing a platform this host cannot provide (macOS) are reported as
  NOT VERIFIED with the reason, never silently skipped.

Missing prerequisites (wrong uv/Node/LibreOffice, missing WSL distro) fail the
affected job loudly. ``uses:`` actions are emulated by verifying the tool they
would install; ``apt-get install`` steps verify that the packages are present.

Usage::

    python scripts/pretest.py                  # full gate, all runnable jobs
    python scripts/pretest.py --quick          # commit-speed checks, working tree
    python scripts/pretest.py --only integration-tests --skip windows-smoke
    python scripts/pretest.py --rev HEAD~1     # gate another commit
    python scripts/pretest.py --list           # job -> local executor mapping
    python scripts/pretest.py --setup-wsl      # provision/refresh the WSL distro

Per-clone settings (``git config --local``; environment variables win):

    pretest.wslDistro         PRETEST_WSL_DISTRO      default Ubuntu-26.04
    pretest.windowsNode       PRETEST_WINDOWS_NODE    dir containing node.exe
    pretest.windowsNodeMajor  PRETEST_WINDOWS_NODE_MAJOR  lowest accepted Node
                              major for Windows jobs (default: NODE_VERSION)
    pretest.home              PRETEST_HOME            work dir (logs, checkouts)

The host side only needs Python >= 3.9 and git; nothing is installed on it.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

# Inner runners are fed through stdin (`python3 -`) and never use ROOT.
ROOT = Path(__file__).resolve().parents[1] if __file__ != "<stdin>" else Path.cwd()
WORKFLOWS = (("ci.yml", None), ("release.yml", ("test",)))
# GitHub's ubuntu-latest image. Update together with the WSL distro when
# GitHub moves the label (https://github.com/actions/runner-images).
UBUNTU_LATEST = "26.04"
DEFAULT_DISTRO = "Ubuntu-26.04"
# Writer that tests/native_docx_note_lifecycle_helpers.py was re-baselined on;
# the integration job refuses an older local LibreOffice.
LIBREOFFICE_MIN = (26, 2, 7, 3)
CI_USER = "runner"
WSL_HOME = PurePosixPath("/home/runner/aam-ci")
LINUX_PATH = "/home/runner/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
KEEP_ON_CLEAN = (
    "/.venv",
    "/vscode-extension/.vscode-test",
    "/vscode-extension/node_modules",
)
MARK = "::pretest::"

# Steps that cannot mean the same thing outside GitHub. Each keeps a reason and
# an optional local substitute that checks the part that still applies.
NOT_APPLICABLE = {
    ("release.yml", "test", "Resolve and validate release source"): (
        "validates the pushed annotated release tag against origin; it only "
        "applies to a tag push, so the gate checks version consistency instead",
        "set -euo pipefail\n"
        'project="$(python3 scripts/get_version.py --strict-semver)"\n'
        'vsix="$(python3 -c \'import json; print(json.load(open("vscode-extension/package.json", encoding="utf-8"))["version"])\')"\n'
        'if [ "$project" != "$vsix" ]; then\n'
        '  echo "ERROR: release version mismatch: pyproject $project, VSIX $vsix"; exit 1\n'
        "fi\n"
        'echo "Release versions agree: $project"\n',
    ),
}
NOT_VERIFIED = {
    "macos": "needs a macOS runner; this host cannot provide one",
}

# --quick: offline commit-time subset, run in the working tree. Every command is
# taken verbatim from a workflow `run:` step (tests/unit/test_pretest_gate.py
# keeps them in sync). The network-bound `uv audit` waits for the full gate.
QUICK_COMMANDS = (
    ("docs site payload", ".", "uv run python scripts/build_docs_site.py --check"),
    ("release harness", ".", "uv run python scripts/audit_release_harness.py"),
    ("uv lock", ".", "uv lock --check"),
    ("ruff lint", ".", "uv run ruff check ."),
    ("ruff format", ".", "uv run ruff format --check ."),
    ("mypy", ".", "uv run mypy src --ignore-missing-imports"),
    ("bandit", ".", "uv run bandit -q -r src -x tests --severity-level medium"),
    (
        "zizmor",
        ".",
        "uv run zizmor --persona=regular --min-severity high .github/workflows",
    ),
    ("VSIX assets in sync", "vscode-extension", "npm run sync-assets:check"),
)
REQUIRED_FILES = ("README.md", "CHANGELOG.md", "CONSTITUTION.md", "LICENSE")


class GateError(RuntimeError):
    """A prerequisite or workflow construct the gate cannot honour."""


# ---------------------------------------------------------------------------
# Minimal YAML loader for the GitHub workflow subset used in this repository
# (block mappings/sequences, plain/quoted scalars, flow sequences, | and >
# block scalars, comments). The host gate must run without third-party
# packages; tests/unit/test_pretest_gate.py compares it with PyYAML.
# ---------------------------------------------------------------------------
class YamlError(ValueError):
    pass


_KEY = re.compile(r"([^\s:#'\"\[\]{},&*!|>%@`-][^:]*?|-[^\s:][^:]*?)\s*:(?=\s|$)")


def _quoted(text: str, start: int, lineno: int) -> tuple[str, int]:
    quote, out, i = text[start], [], start + 1
    escapes = {
        "n": "\n",
        "t": "\t",
        "\\": "\\",
        '"': '"',
        "/": "/",
        "0": "\0",
        " ": " ",
    }
    while i < len(text):
        char = text[i]
        if quote == "'" and char == "'":
            if text.startswith("''", i):
                out.append("'")
                i += 2
                continue
            return "".join(out), i + 1
        if quote == '"' and char == "\\":
            if text[i + 1 : i + 2] not in escapes:
                raise YamlError(f"line {lineno}: unsupported escape")
            out.append(escapes[text[i + 1]])
            i += 2
            continue
        if quote == '"' and char == '"':
            return "".join(out), i + 1
        out.append(char)
        i += 1
    raise YamlError(f"line {lineno}: unterminated quoted scalar")


def _plain(text: str) -> Any:
    if text in ("", "~", "null", "Null", "NULL"):
        return None
    if text in ("true", "True", "TRUE"):
        return True
    if text in ("false", "False", "FALSE"):
        return False
    if re.fullmatch(r"[-+]?\d+", text):
        return int(text)
    if re.fullmatch(r"[-+]?(\d+\.\d*|\.\d+)([eE][-+]?\d+)?", text):
        return float(text)
    return text


def _scalar(text: str, lineno: int) -> Any:
    text = text.strip()
    if not text or text.startswith("#"):
        return None
    if text[0] in "\"'":
        value, end = _quoted(text, 0, lineno)
        tail = text[end:].strip()
        if tail and not tail.startswith("#"):
            raise YamlError(f"line {lineno}: text after quoted scalar")
        return value
    if text[0] == "[":
        return _flow_sequence(text, lineno)
    if text[0] in "{&*!|>%@`":
        raise YamlError(f"line {lineno}: unsupported YAML construct {text[0]!r}")
    comment = re.search(r"\s#", text)
    return _plain(text[: comment.start()].rstrip() if comment else text)


def _flow_sequence(text: str, lineno: int) -> list[Any]:
    """``[a, 'b, c', "d[e]"]`` on one line; nested collections are rejected."""
    items, current, i = [], "", 1
    while i < len(text):
        char = text[i]
        if char in "\"'":
            _, end = _quoted(text, i, lineno)
            current += text[i:end]
            i = end
            continue
        if char in "[{":
            raise YamlError(f"line {lineno}: nested flow collections are unsupported")
        if char in ",]":
            if current.strip():
                items.append(_scalar(current, lineno))
            current = ""
            if char == "]":
                tail = text[i + 1 :].strip()
                if tail and not tail.startswith("#"):
                    raise YamlError(f"line {lineno}: text after flow sequence")
                return items
        else:
            current += char
        i += 1
    raise YamlError(f"line {lineno}: unterminated flow sequence")


def _split_key(content: str, lineno: int) -> tuple[str, str] | None:
    if content[0] in "\"'":
        key, end = _quoted(content, 0, lineno)
        rest = content[end:]
        if not re.match(r"\s*:(\s|$)", rest):
            return None
        return key, rest.split(":", 1)[1].strip()
    match = _KEY.match(content)
    if not match:
        return None
    return match.group(1), content[match.end() :].strip()


def _fold(lines: list[str]) -> str:
    text = ""
    for i, line in enumerate(lines):
        if i == 0:
            text = line
        elif line == "":
            text += "\n"
        elif lines[i - 1] == "" or line.startswith(" ") or lines[i - 1].startswith(" "):
            text += ("" if lines[i - 1] == "" else "\n") + line
        else:
            text += " " + line
    return text


class _Yaml:
    def __init__(self, text: str) -> None:
        self.raw = text.splitlines()
        self.i = 0
        self.override: tuple[int, int, str] | None = None

    def peek(self) -> tuple[int, int, str] | None:
        i = self.i
        while i < len(self.raw):
            if self.override and self.override[0] == i:
                return self.override
            line = self.raw[i]
            stripped = line.strip()
            if "\t" in line[: len(line) - len(line.lstrip())]:
                raise YamlError(f"line {i + 1}: tab indentation")
            if stripped and not stripped.startswith("#"):
                if stripped in ("---", "..."):
                    raise YamlError(f"line {i + 1}: multi-document YAML")
                return i, len(line) - len(line.lstrip(" ")), stripped
            i += 1
        return None

    def advance(self, record: tuple[int, int, str]) -> None:
        self.i = record[0] + 1
        if self.override and self.override[0] == record[0]:
            self.override = None

    def parse(self) -> Any:
        first = self.peek()
        value = self.node(first[1]) if first else None
        rest = self.peek()
        if rest:
            raise YamlError(f"line {rest[0] + 1}: unexpected content")
        return value

    def node(self, indent: int) -> Any:
        record = self.peek()
        if record is None or record[1] < indent:
            return None
        if record[2] == "-" or record[2].startswith("- "):
            return self.sequence(record[1])
        return self.mapping(record[1])

    def mapping(self, indent: int) -> dict[str, Any]:
        result: dict[str, Any] = {}
        while True:
            record = self.peek()
            if record is None or record[1] < indent:
                return result
            idx, level, content = record
            if level > indent:
                raise YamlError(f"line {idx + 1}: unexpected indentation")
            if content == "-" or content.startswith("- "):
                return result
            pair = _split_key(content, idx + 1)
            if pair is None:
                raise YamlError(f"line {idx + 1}: expected 'key: value'")
            key, rest = pair
            if key in result:
                raise YamlError(f"line {idx + 1}: duplicate key {key!r}")
            self.advance(record)
            result[key] = self.value(rest, indent, idx)

    def value(self, rest: str, indent: int, idx: int) -> Any:
        if rest.startswith("#"):
            rest = ""
        if rest and rest[0] in "|>":
            return self.block(rest, indent, idx)
        if rest:
            return _scalar(rest, idx + 1)
        following = self.peek()
        if following is None:
            return None
        if following[1] > indent:
            return self.node(following[1])
        if following[1] == indent and (
            following[2] == "-" or following[2].startswith("- ")
        ):
            return self.sequence(indent)
        return None

    def sequence(self, indent: int) -> list[Any]:
        items: list[Any] = []
        while True:
            record = self.peek()
            if record is None or record[1] < indent:
                return items
            idx, level, content = record
            if level > indent:
                raise YamlError(f"line {idx + 1}: unexpected indentation")
            if not (content == "-" or content.startswith("- ")):
                return items
            body = content[1:].lstrip(" ")
            if not body or body.startswith("#"):
                self.advance(record)
                following = self.peek()
                nested = following is not None and following[1] > indent
                items.append(self.node(following[1]) if nested else None)
                continue
            if body == "-" or body.startswith("- "):
                raise YamlError(f"line {idx + 1}: unsupported inline nested sequence")
            if _split_key(body, idx + 1) is not None:
                self.override = (idx, level + len(content) - len(body), body)
                items.append(self.mapping(self.override[1]))
                continue
            self.advance(record)
            if body[0] in "|>":
                items.append(self.block(body, indent, idx))
            else:
                items.append(_scalar(body, idx + 1))

    def block(self, header: str, indent: int, idx: int) -> str:
        match = re.fullmatch(r"([|>])([-+]?)\s*(#.*)?", header)
        if not match:
            raise YamlError(f"line {idx + 1}: unsupported block scalar header")
        style, chomp = match.group(1), match.group(2)
        lines: list[str] = []
        block_indent = None
        i = idx + 1
        while i < len(self.raw):
            line = self.raw[i]
            if not line.strip():
                lines.append("")
                i += 1
                continue
            level = len(line) - len(line.lstrip(" "))
            if block_indent is None:
                if level <= indent:
                    break
                block_indent = level
            if level < block_indent:
                break
            lines.append(line[block_indent:])
            i += 1
        self.i, self.override = i, None
        trailing = 0
        while lines and lines[-1] == "":
            lines.pop()
            trailing += 1
        if not lines:
            return ""
        text = "\n".join(lines) if style == "|" else _fold(lines)
        if chomp == "-":
            return text
        return text + "\n" * (1 + trailing if chomp == "+" else 1)


def load_yaml(text: str) -> Any:
    return _Yaml(text).parse()


# ---------------------------------------------------------------------------
# GitHub expression subset: ${{ a.b }}, ==, !=, &&, ||, !, (), literals and the
# status functions. Anything else raises instead of being guessed.
# ---------------------------------------------------------------------------
_EXPR = re.compile(r"\$\{\{\s*(.*?)\s*\}\}")
_TOKEN = re.compile(
    r"\s*(?:(?P<str>'(?:[^']|'')*')|(?P<num>-?\d+(?:\.\d+)?)|(?P<op>==|!=|&&|\|\||!|\(|\))"
    r"|(?P<path>[A-Za-z_][\w-]*(?:\.[A-Za-z_*][\w-]*)*))"
)


def _tokens(expr: str) -> list[tuple[str, str]]:
    tokens, pos = [], 0
    while pos < len(expr):
        if expr[pos:].strip() == "":
            break
        match = _TOKEN.match(expr, pos)
        if not match:
            raise GateError(f"unsupported expression syntax: {expr!r}")
        kind = match.lastgroup or ""
        tokens.append((kind, match.group(kind)))
        pos = match.end()
    return tokens


def _truthy(value: Any) -> bool:
    return value not in (None, False, 0, "")


def _lookup(path: str, contexts: dict[str, Any]) -> Any:
    head, *rest = path.split(".")
    if head == "secrets":
        raise GateError("the job needs repository secrets, which stay on GitHub")
    if head not in contexts:
        raise GateError(f"unsupported expression context {head!r}")
    value = contexts[head]
    for part in rest:
        value = value.get(part) if isinstance(value, dict) else None
    return value


def evaluate(expr: str, contexts: dict[str, Any]) -> Any:
    tokens, pos = _tokens(expr), 0

    def take(value: str | None = None) -> tuple[str, str]:
        nonlocal pos
        if pos >= len(tokens) or (value is not None and tokens[pos][1] != value):
            raise GateError(f"unsupported expression: {expr!r}")
        pos += 1
        return tokens[pos - 1]

    def primary() -> Any:
        kind, text = take()
        if kind == "str":
            return text[1:-1].replace("''", "'")
        if kind == "num":
            return float(text) if "." in text else int(text)
        if text == "(":
            value = disjunction()
            take(")")
            return value
        if text == "!":
            return not _truthy(primary())
        if kind != "path":
            raise GateError(f"unsupported expression: {expr!r}")
        if text in ("true", "false", "null"):
            return {"true": True, "false": False, "null": None}[text]
        if pos < len(tokens) and tokens[pos][1] == "(":
            take("(")
            take(")")
            statuses = {
                "always": True,
                "success": True,
                "failure": False,
                "cancelled": False,
            }
            if text not in statuses:
                raise GateError(f"unsupported expression function {text}()")
            return statuses[text]
        return _lookup(text, contexts)

    def comparison() -> Any:
        left = primary()
        if pos < len(tokens) and tokens[pos][1] in ("==", "!="):
            operator = take()[1]
            right = primary()
            same = (
                left.casefold() == right.casefold()
                if isinstance(left, str) and isinstance(right, str)
                else left == right
            )
            return same if operator == "==" else not same
        return left

    def conjunction() -> Any:
        value = comparison()
        while pos < len(tokens) and tokens[pos][1] == "&&":
            take()
            right = comparison()
            value = right if _truthy(value) else value
        return value

    def disjunction() -> Any:
        value = conjunction()
        while pos < len(tokens) and tokens[pos][1] == "||":
            take()
            right = conjunction()
            value = value if _truthy(value) else right
        return value

    result = disjunction()
    if pos != len(tokens):
        raise GateError(f"unsupported expression: {expr!r}")
    return result


def substitute(text: Any, contexts: dict[str, Any]) -> str:
    def render(match: re.Match[str]) -> str:
        value = evaluate(match.group(1), contexts)
        if isinstance(value, bool):
            return "true" if value else "false"
        return "" if value is None else str(value)

    return _EXPR.sub(render, str(text))


# ---------------------------------------------------------------------------
# Workflow model and step planning
# ---------------------------------------------------------------------------
@dataclass
class Job:
    workflow: str
    key: str
    data: dict[str, Any]
    workflow_env: dict[str, Any]

    @property
    def qualified(self) -> str:
        return f"{self.workflow.split('.')[0]}:{self.key}"

    @property
    def name(self) -> str:
        return str(self.data.get("name") or self.key)

    @property
    def runs_on(self) -> str:
        return str(self.data.get("runs-on", ""))

    @property
    def platform(self) -> str:
        label = self.runs_on
        if "${{" in label:
            return "matrix"
        for prefix, platform in (("ubuntu-", "linux"), ("windows-", "windows")):
            if label.startswith(prefix):
                return platform
        return "macos" if label.startswith("macos-") else "unknown"

    @property
    def aggregate(self) -> bool:
        return "${{ needs." in json.dumps(self.data.get("steps", []))


@dataclass
class Step:
    index: int
    name: str
    kind: str
    data: dict[str, Any]
    script: str = ""
    detail: dict[str, Any] = field(default_factory=dict)


def load_jobs(read: Any) -> list[Job]:
    jobs = []
    for workflow, only in WORKFLOWS:
        document = load_yaml(read(f".github/workflows/{workflow}"))
        for key, data in document.get("jobs", {}).items():
            if only is None or key in only:
                jobs.append(Job(workflow, key, data, document.get("env") or {}))
    return jobs


_APT_LINE = re.compile(r"^(?:sudo\s+)?apt-get\s+(update|install\s+(?P<args>.+))$")


def apt_packages(script: str) -> list[str] | None:
    """Packages of a step that only runs apt-get update/install, else None."""
    packages: list[str] = []
    commands = [c.strip() for line in script.splitlines() for c in line.split("&&")]
    for command in filter(None, commands):
        match = _APT_LINE.match(command)
        if not match:
            return None
        packages.extend(
            t for t in (match.group("args") or "").split() if not t.startswith("-")
        )
    return packages


def plan_steps(job: Job) -> list[Step]:
    if job.data.get("container") or job.data.get("services"):
        raise GateError("container/service jobs are not supported locally")
    if job.data.get("strategy"):
        raise GateError("matrix jobs are not supported locally")
    steps = []
    for index, data in enumerate(job.data.get("steps") or [], 1):
        uses, run = data.get("uses"), data.get("run")
        name = str(data.get("name") or uses or str(run).splitlines()[0])
        if uses:
            action = str(uses).split("@")[0]
            settings = data.get("with") or {}
            if action == "actions/checkout":
                steps.append(Step(index, name, "checkout", data))
            elif action == "astral-sh/setup-uv":
                if not settings.get("version"):
                    raise GateError(f"step {name!r}: setup-uv without a pinned version")
                steps.append(
                    Step(
                        index,
                        name,
                        "setup-uv",
                        data,
                        detail={"version": str(settings["version"])},
                    )
                )
            elif action == "actions/setup-node":
                steps.append(
                    Step(
                        index,
                        name,
                        "setup-node",
                        data,
                        detail={"version": str(settings.get("node-version", ""))},
                    )
                )
            elif action in ("actions/upload-artifact", "actions/download-artifact"):
                steps.append(Step(index, name, "artifact", data))
            else:
                raise GateError(
                    f"step {name!r}: no local emulation for action {action}"
                )
            continue
        script = str(run)
        policy = NOT_APPLICABLE.get((job.workflow, job.key, name))
        if policy:
            steps.append(
                Step(
                    index,
                    name,
                    "not-applicable",
                    data,
                    policy[1],
                    {"reason": policy[0]},
                )
            )
        elif re.search(r"\bapt-get\b", script):
            packages = apt_packages(script)
            if packages is None:
                raise GateError(f"step {name!r}: apt-get mixed with other commands")
            steps.append(Step(index, name, "apt", data, detail={"packages": packages}))
        else:
            steps.append(Step(index, name, "run", data, script))
    return steps


def safe_plan(job: Job) -> list[Step]:
    """Plan for inventory purposes; a broken job fails when it runs."""
    try:
        return plan_steps(job)
    except GateError:
        return []


def job_apt_packages(job: Job) -> list[str]:
    packages: list[str] = []
    for step in safe_plan(job):
        packages.extend(p for p in step.detail.get("packages", []) if p not in packages)
    return packages


def workflow_pins(jobs: list[Job]) -> dict[str, str]:
    """uv/Node/Python pins shared by the selected workflows (must be unique)."""
    found: dict[str, set[str]] = {"uv": set(), "node": set(), "python": set()}
    for job in jobs:
        found["node"].add(str(job.workflow_env.get("NODE_VERSION", "")))
        found["python"].add(str(job.workflow_env.get("PYTHON_VERSION", "")))
        for step in safe_plan(job):
            if step.kind == "setup-uv":
                found["uv"].add(step.detail["version"])
    pins = {}
    for key, values in found.items():
        values.discard("")
        if len(values) != 1:
            raise GateError(f"workflows disagree on the {key} pin: {sorted(values)}")
        pins[key] = values.pop()
    return pins


# ---------------------------------------------------------------------------
# Job execution (runs where the job runs: inside WSL/Linux or on Windows)
# ---------------------------------------------------------------------------
def emit(kind: str, payload: dict[str, Any]) -> None:
    sys.stdout.write(f"{MARK}{kind}::{json.dumps(payload)}\n")
    sys.stdout.flush()


def say(text: str) -> None:
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


def run_process(
    command: list[str],
    *,
    cwd: str | Path,
    env: dict[str, str],
    timeout: float | None = None,
    user: tuple[int, int] | None = None,
    capture: bool = False,
) -> tuple[int | None, str]:
    """Run ``command``; return (exit code or None on timeout, captured text)."""
    options: dict[str, Any] = {"cwd": str(cwd), "env": env, "stdin": subprocess.DEVNULL}
    if capture:
        options.update(stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if os.name == "posix":
        options["start_new_session"] = True
        if user:
            options.update(user=user[0], group=user[1], extra_groups=[])
    else:
        options["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    process = subprocess.Popen(command, **options)
    try:
        output, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_tree(process)
        process.communicate()
        return None, ""
    text = output.decode("utf-8", "replace") if capture and output else ""
    return process.returncode, text


def kill_tree(process: subprocess.Popen[Any]) -> None:
    if os.name == "posix":
        try:
            os.killpg(process.pid, 9)
        except OSError:
            process.kill()
    else:
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(process.pid)],
            capture_output=True,
            check=False,
        )


def _version_tuple(text: str) -> tuple[int, ...]:
    upstream = text.split(":", 1)[-1].split("-", 1)[0].split("+", 1)[0]
    return tuple(int(part) for part in re.findall(r"\d+", upstream)[:4])


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    lines = path.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if "<<" in line and ("=" not in line or line.index("<<") < line.index("=")):
            name, delimiter = line.split("<<", 1)
            body: list[str] = []
            i += 1
            while i < len(lines) and lines[i] != delimiter:
                body.append(lines[i])
                i += 1
            values[name] = "\n".join(body)
        elif "=" in line:
            name, value = line.split("=", 1)
            values[name] = value
        i += 1
    return values


class JobRunner:
    """Execute one job's planned steps in a prepared workspace."""

    def __init__(self, job: Job, payload: dict[str, Any]) -> None:
        self.job = job
        self.payload = payload
        self.platform = payload["platform"]
        self.workspace = Path(payload["workspace"])
        self.temp = Path(payload["runner_temp"])
        self.user = tuple(payload["user"]) if payload.get("user") else None
        self.notes: list[str] = []
        self.results: list[dict[str, Any]] = []
        self.extra_env: dict[str, str] = {}
        self.extra_path: list[str] = []

    # -- environment ------------------------------------------------------
    def owned_dir(self, path: Path) -> Path:
        path.mkdir(parents=True, exist_ok=True)
        if self.user:
            os.chown(path, *self.user)
        return path

    def base_env(self) -> dict[str, str]:
        files = self.owned_dir(self.temp / "_runner_file_commands")
        common = {
            "CI": "true",
            "GITHUB_ACTIONS": "true",
            "GITHUB_WORKFLOW": self.job.workflow,
            "GITHUB_JOB": self.job.key,
            "GITHUB_WORKSPACE": str(self.workspace),
            "GITHUB_SHA": self.payload["sha"],
            "GITHUB_REF": self.payload["ref"],
            "GITHUB_REF_NAME": self.payload["ref"].rsplit("/", 1)[-1],
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_REPOSITORY": "u9401066/asset-aware-mcp",
            "GITHUB_ENV": str(files / "env"),
            "GITHUB_PATH": str(files / "path"),
            "GITHUB_OUTPUT": str(files / "output"),
            "GITHUB_STEP_SUMMARY": str(files / "summary.md"),
            "RUNNER_TEMP": str(self.temp),
            "RUNNER_OS": {"linux": "Linux", "windows": "Windows"}[self.platform],
            "RUNNER_ARCH": "X64",
        }
        if self.platform == "linux":
            # Per-job TMPDIR keeps parallel pytest basetemps apart.
            env = {
                "HOME": f"/home/{CI_USER}",
                "USER": CI_USER,
                "LOGNAME": CI_USER,
                "SHELL": "/bin/bash",
                "LANG": "C.UTF-8",
                "PATH": LINUX_PATH,
                "DEBIAN_FRONTEND": "noninteractive",
                **(self.payload.get("linux_env") or {}),
                "TMPDIR": str(self.owned_dir(self.temp / "tmp")),
            }
        else:
            env = dict(self.payload["host_env"])
        env.update(common)
        return env

    def contexts(self, env: dict[str, str]) -> dict[str, Any]:
        return {
            "env": env,
            "runner": {"os": env["RUNNER_OS"], "temp": str(self.temp), "arch": "X64"},
            "github": {
                "sha": self.payload["sha"],
                "ref": self.payload["ref"],
                "event_name": "push",
                "workspace": str(self.workspace),
                "workflow": self.job.workflow,
                "job": self.job.key,
                "repository": "u9401066/asset-aware-mcp",
            },
            "matrix": {},
            "inputs": {},
            "steps": {},
            "needs": {},
        }

    def step_env(self, step: Step) -> dict[str, str]:
        env = self.base_env()
        for scope in (
            self.job.workflow_env,
            self.job.data.get("env") or {},
            step.data.get("env") or {},
        ):
            for key, value in scope.items():
                env[key] = substitute(value, self.contexts(env))
        env.update(self.extra_env)
        if self.extra_path:
            sep = ";" if self.platform == "windows" else ":"
            env["PATH"] = sep.join([*reversed(self.extra_path), env["PATH"]])
        return env

    # -- step kinds ---------------------------------------------------------
    def tool_version(self, tool: str, env: dict[str, str]) -> str:
        located = shutil.which(tool, path=env["PATH"])
        if not located:
            return ""
        code, text = run_process(
            [located, "--version"],
            cwd=self.workspace,
            env=env,
            timeout=60,
            capture=True,
            user=self.user,
        )
        return text.strip() if code == 0 else ""

    def check_uv(self, step: Step, env: dict[str, str]) -> str:
        wanted = step.detail["version"]
        found = self.tool_version("uv", env)
        if found.split()[1:2] != [wanted]:
            raise GateError(
                f"setup-uv pins uv {wanted}; local uv is {found or 'missing'}"
            )
        return f"uv {wanted} (as setup-uv)"

    def check_node(self, step: Step, env: dict[str, str]) -> str:
        wanted = substitute(step.detail["version"], self.contexts(env))
        major = int(wanted.split(".")[0])
        found = self.tool_version("node", env)
        found_major = int(found.lstrip("v").split(".")[0]) if found else 0
        minimum = int(self.payload.get("node_major_min") or major)
        if self.platform == "linux" and found_major != major:
            raise GateError(
                f"setup-node pins Node {wanted}; local node is {found or 'missing'}"
            )
        if found_major < minimum:
            raise GateError(
                f"needs Node >= {minimum} (CI: {wanted}); local node is {found or 'missing'}"
            )
        if found_major != major:
            note = f"Node {found} locally; CI uses Node {wanted} (allowed by pretest.windowsNodeMajor={minimum})"
            if note not in self.notes:
                self.notes.append(note)
        return f"node {found}"

    def check_apt(self, step: Step, env: dict[str, str]) -> str:
        if self.platform != "linux":
            raise GateError("apt-get step outside Linux")
        missing, versions = [], {}
        for package in step.detail["packages"]:
            code, text = run_process(
                ["dpkg-query", "-W", "-f=${Status}\t${Version}", package],
                cwd="/",
                env=env,
                capture=True,
                timeout=60,
            )
            status, _, version = text.partition("\t")
            if code != 0 or status.strip() != "install ok installed":
                missing.append(package)
            else:
                versions[package] = version.strip()
        if missing:
            raise GateError(
                f"apt packages missing: {' '.join(missing)}; run python scripts/pretest.py --setup-wsl"
            )
        office = {p: v for p, v in versions.items() if p.startswith("libreoffice-")}
        for package, version in office.items():
            if _version_tuple(version) < LIBREOFFICE_MIN:
                minimum = ".".join(map(str, LIBREOFFICE_MIN))
                raise GateError(
                    f"{package} {version} is older than the CI baseline {minimum}; run --setup-wsl"
                )
        if office:
            note = f"LibreOffice {next(iter(office.values()))}"
            if note not in self.notes:
                self.notes.append(note)
        return f"verified {len(versions)} apt packages (installed by setup_local_ci_wsl.sh)"

    def run_script(
        self, step: Step, env: dict[str, str], script: str, timeout: float | None
    ) -> int | None:
        shell = str(
            step.data.get("shell")
            or self.job.data.get("defaults", {}).get("run", {}).get("shell")
            or ""
        )
        shell = shell or ("pwsh" if self.platform == "windows" else "bash")
        folder = self.owned_dir(self.temp / "_pretest_steps")
        if shell == "bash":
            path = folder / f"step-{step.index}.sh"
            path.write_text(script, encoding="utf-8", newline="\n")
            bash = (
                "bash"
                if self.platform == "linux"
                else self.payload.get("git_bash", "bash")
            )
            command = [bash, "--noprofile", "--norc", "-eo", "pipefail", str(path)]
        elif shell in ("pwsh", "powershell"):
            path = folder / f"step-{step.index}.ps1"
            body = f"$ErrorActionPreference = 'stop'\n{script}\nif ((Test-Path -LiteralPath variable:\\LASTEXITCODE)) {{ exit $LASTEXITCODE }}\n"
            path.write_text(body, encoding="utf-8-sig")
            command = [
                shell,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                f". '{path}'",
            ]
        else:
            raise GateError(f"unsupported shell {shell!r}")
        if self.user:
            os.chown(path, *self.user)
        defaults = self.job.data.get("defaults", {}).get("run", {})
        directory = (
            step.data.get("working-directory")
            or defaults.get("working-directory")
            or "."
        )
        code, _ = run_process(
            command,
            cwd=self.workspace / str(directory),
            env=env,
            timeout=timeout,
            user=self.user,
        )
        return code

    def collect_file_commands(self, env: dict[str, str]) -> None:
        for key, value in _read_env_file(Path(env["GITHUB_ENV"])).items():
            self.extra_env[key] = value
        path_file = Path(env["GITHUB_PATH"])
        if path_file.exists():
            for line in path_file.read_text(encoding="utf-8").splitlines():
                if line.strip() and line.strip() not in self.extra_path:
                    self.extra_path.append(line.strip())

    # -- driver ---------------------------------------------------------------
    def run(self) -> dict[str, Any]:
        started = time.monotonic()
        status = "PASS"
        error = ""
        job_timeout = float(self.job.data.get("timeout-minutes", 360)) * 60
        try:
            steps = plan_steps(self.job)
        except GateError as exc:
            steps, status, error = [], "FAIL", str(exc)
        for step in steps:
            if status != "PASS":
                self.results.append({"name": step.name, "status": "not run"})
                continue
            step_started = time.monotonic()
            emit("step", {"index": step.index, "name": step.name, "kind": step.kind})
            say(
                f"\n===== [{self.job.qualified}] step {step.index}: {step.name} ({step.kind})"
            )
            outcome, detail = "PASS", ""
            try:
                env = self.step_env(step)
                condition = step.data.get("if")
                if condition is not None and not _truthy(
                    evaluate(
                        str(condition).replace("${{", "").replace("}}", ""),
                        self.contexts(env),
                    )
                ):
                    outcome, detail = "skipped", f"if: {condition}"
                elif step.kind == "checkout":
                    detail = f"clean checkout of {self.payload['sha'][:12]} prepared by the gate"
                elif step.kind == "setup-uv":
                    detail = self.check_uv(step, env)
                elif step.kind == "setup-node":
                    detail = self.check_node(step, env)
                elif step.kind == "artifact":
                    outcome, detail = "skipped", "artifact transfer is GitHub-only"
                elif step.kind == "apt":
                    detail = self.check_apt(step, env)
                else:
                    if step.kind == "not-applicable":
                        reason = f"N/A: {step.detail['reason']}"
                        self.notes.append(f"{step.name}: {reason}")
                        say(reason)
                    remaining = job_timeout - (time.monotonic() - started)
                    step_limit = step.data.get("timeout-minutes")
                    limit = (
                        min(remaining, float(step_limit) * 60)
                        if step_limit
                        else remaining
                    )
                    code = self.run_script(step, env, step.script, max(limit, 1))
                    self.collect_file_commands(env)
                    if code is None:
                        outcome, detail = "FAIL", "timed out (CI timeout-minutes)"
                    elif code != 0:
                        outcome, detail = "FAIL", f"exit code {code}"
                    if outcome == "FAIL" and step.data.get("continue-on-error") is True:
                        self.notes.append(f"{step.name}: failed but continue-on-error")
                        outcome = "PASS"
            except GateError as exc:
                outcome, detail = "FAIL", str(exc)
            seconds = time.monotonic() - step_started
            say(
                f"----- [{self.job.qualified}] {step.name}: {outcome} {detail} ({seconds:.1f}s)"
            )
            self.results.append(
                {
                    "name": step.name,
                    "status": outcome,
                    "detail": detail,
                    "seconds": round(seconds, 1),
                }
            )
            if outcome == "FAIL":
                status, error = "FAIL", f"{step.name}: {detail}"
        result = {
            "status": status,
            "error": error,
            "notes": self.notes,
            "steps": self.results,
            "seconds": round(time.monotonic() - started, 1),
        }
        emit("result", result)
        return result


# ---------------------------------------------------------------------------
# Inner entry points (executed inside WSL via `python3 -` or on the host)
# ---------------------------------------------------------------------------
def git_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def linux_user() -> tuple[int, int] | None:
    if os.geteuid() != 0:  # type: ignore[attr-defined]
        return None
    import pwd

    entry = pwd.getpwnam(CI_USER)
    return entry.pw_uid, entry.pw_gid


def as_user(command: list[str], user: tuple[int, int] | None, cwd: str = "/") -> str:
    """Run as the CI user when started as root (WSL), else as ourselves."""
    env = (
        {"HOME": f"/home/{CI_USER}", "PATH": LINUX_PATH, "LANG": "C.UTF-8"}
        if user
        else git_env()
    )
    code, text = run_process(
        command, cwd=cwd, env=env, user=user, capture=True, timeout=1800
    )
    if code != 0:
        raise GateError(f"{' '.join(command)} failed: {text.strip()[-2000:]}")
    return text


def inner_sync(payload: dict[str, Any]) -> int:
    """Inside WSL: preflight facts and fetch the snapshot into the mirror."""
    facts: dict[str, Any] = {"errors": []}
    os_release = Path("/etc/os-release").read_text(encoding="utf-8")
    version = re.search(r'^VERSION_ID="?([^"\n]+)', os_release, re.M)
    facts["ubuntu"] = version.group(1) if version else "unknown"
    env = {"PATH": LINUX_PATH, "HOME": "/root"}
    for tool in ("uv", "node", "git", "bash"):
        located = shutil.which(tool, path=LINUX_PATH)
        code, text = (
            run_process(
                [located, "--version"], cwd="/", env=env, capture=True, timeout=60
            )
            if located
            else (1, "")
        )
        facts[tool] = text.strip().splitlines()[0] if code == 0 and text.strip() else ""
    packages: dict[str, str] = {}
    for package in payload["packages"]:
        code, text = run_process(
            ["dpkg-query", "-W", "-f=${Status}\t${Version}", package],
            cwd="/",
            env=env,
            capture=True,
            timeout=60,
        )
        status, _, found = text.partition("\t")
        packages[package] = (
            found.strip()
            if code == 0 and status.strip() == "install ok installed"
            else ""
        )
    facts["packages"] = packages
    lists = Path("/var/lib/apt/lists")
    stamps = (
        [p.stat().st_mtime for p in lists.glob("*InRelease")] if lists.exists() else []
    )
    facts["apt_index_age_days"] = (
        round((time.time() - max(stamps)) / 86400, 1) if stamps else None
    )
    try:
        user = linux_user()
        if user is None:
            raise GateError("the WSL gate must start as root (wsl.exe -u root)")
        mirror = WSL_HOME / "mirror.git"
        if not Path(mirror, "HEAD").exists():
            as_user(["git", "init", "--quiet", "--bare", str(mirror)], user)
        source = payload["source"]
        as_user(
            [
                "git",
                "-c",
                f"safe.directory={source}",
                "-C",
                str(mirror),
                "fetch",
                "--quiet",
                "--force",
                "--no-tags",
                source,
                "+refs/pretest/snapshot:refs/heads/pretest-snapshot",
                "+refs/tags/*:refs/tags/*",
            ],
            user,
        )
        as_user(
            [
                "git",
                "-C",
                str(mirror),
                "symbolic-ref",
                "HEAD",
                "refs/heads/pretest-snapshot",
            ],
            user,
        )
        resolved = as_user(
            ["git", "-C", str(mirror), "rev-parse", "refs/heads/pretest-snapshot"], user
        ).strip()
        if resolved != payload["sha"]:
            raise GateError(f"mirror resolved {resolved}, expected {payload['sha']}")
    except (GateError, KeyError, OSError) as exc:
        facts["errors"].append(str(exc))
    emit("sync", facts)
    return 0


def prepare_checkout(
    directory: Path, source: str, sha: str, user: tuple[int, int] | None
) -> None:
    def git(*args: str) -> str:
        command = [
            "git",
            "-c",
            f"safe.directory={source}",
            "-c",
            f"safe.directory={directory}",
            *args,
        ]
        if os.name == "posix":
            return as_user(command, user)
        code, text = run_process(
            command, cwd=directory.parent, env=git_env(), capture=True, timeout=1800
        )
        if code != 0:
            raise GateError(f"git {' '.join(args)} failed: {text.strip()[-2000:]}")
        return text

    if not (directory / ".git").exists():
        directory.parent.mkdir(parents=True, exist_ok=True)
        if user:
            os.chown(directory.parent, *user)
        git("clone", "--quiet", "--shared", "--no-checkout", source, str(directory))
    git("-C", str(directory), "fetch", "--quiet", "--force", "--tags", "origin")
    git(
        "-C",
        str(directory),
        "-c",
        "advice.detachedHead=false",
        "checkout",
        "--quiet",
        "--force",
        "--detach",
        sha,
    )
    clean = ["-C", str(directory), "clean", "-ffdxq"]
    for keep in KEEP_ON_CLEAN:
        clean += ["-e", keep]
    git(*clean)


def isolate_absent_packages(job: Job) -> list[str]:
    """Hide LibreOffice from jobs whose workflow does not install it."""
    if any(p.startswith("libreoffice") for p in job_apt_packages(job)):
        return []
    office = Path("/usr/lib/libreoffice")
    if not office.exists():
        return []
    if not hasattr(os, "unshare") or os.geteuid() != 0:  # type: ignore[attr-defined]
        return [
            "LibreOffice is installed but this job's workflow does not install it; could not hide it (needs root and Python 3.12+)"
        ]
    os.unshare(os.CLONE_NEWNS)  # type: ignore[attr-defined]
    subprocess.run(["mount", "--make-rprivate", "/"], check=True)
    subprocess.run(
        ["mount", "-t", "tmpfs", "-o", "ro,size=4k", "tmpfs", str(office)], check=True
    )
    return ["LibreOffice hidden: this job's workflow does not install it"]


def rmtree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def inner_job(payload: dict[str, Any]) -> int:
    """Prepare a clean checkout, then run one job's steps here."""
    workspace = Path(payload["workspace"])
    temp = Path(payload["runner_temp"])
    if os.name == "posix":
        user = linux_user()
        payload["user"] = list(user) if user else None
    else:
        user = None
    try:
        prepare_checkout(workspace, payload["source"], payload["sha"], user)
        rmtree(temp)
        temp.mkdir(parents=True)
        if user:
            os.chown(temp, *user)
        text = (workspace / ".github/workflows" / payload["workflow"]).read_text(
            encoding="utf-8"
        )
        document = load_yaml(text)
        job = Job(
            payload["workflow"],
            payload["job"],
            document["jobs"][payload["job"]],
            document.get("env") or {},
        )
        notes = isolate_absent_packages(job) if payload["platform"] == "linux" else []
    except (
        GateError,
        OSError,
        KeyError,
        YamlError,
        subprocess.CalledProcessError,
    ) as exc:
        emit(
            "result",
            {
                "status": "FAIL",
                "error": f"workspace setup: {exc}",
                "notes": [],
                "steps": [],
                "seconds": 0,
            },
        )
        return 1
    runner = JobRunner(job, payload)
    runner.notes.extend(notes)
    result = runner.run()
    return 0 if result["status"] == "PASS" else 1


# ---------------------------------------------------------------------------
# Host orchestration
# ---------------------------------------------------------------------------
def git(*args: str, env: dict[str, str] | None = None, check: bool = True) -> str:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, env=env, check=False
    )
    if check and completed.returncode != 0:
        raise GateError(
            f"git {' '.join(args)}: {completed.stderr.decode('utf-8', 'replace').strip()}"
        )
    return completed.stdout.decode("utf-8", "replace").strip()


def git_config(key: str, env_name: str, default: str = "") -> str:
    return (
        os.environ.get(env_name) or git("config", "--get", key, check=False) or default
    )


def snapshot(rev: str | None) -> tuple[str, str]:
    """Return (commit, description); the commit is published as refs/pretest/snapshot."""
    if rev:
        sha = git("rev-parse", "--verify", f"{rev}^{{commit}}")
        label = f"{rev} ({sha[:12]})"
    elif os.environ.get("PRE_COMMIT_TO_REF"):
        sha = git(
            "rev-parse", "--verify", f"{os.environ['PRE_COMMIT_TO_REF']}^{{commit}}"
        )
        label = f"pushed commit {sha[:12]}"
    else:
        head = git("rev-parse", "--verify", "HEAD")
        if not git("status", "--porcelain", "--untracked-files=normal"):
            sha, label = head, f"HEAD {head[:12]} (clean)"
        else:
            index = Path(
                git("rev-parse", "--path-format=absolute", "--git-path", "index")
            )
            with tempfile.TemporaryDirectory(prefix="pretest-index-") as temp:
                scratch = Path(temp) / "index"
                if index.exists():
                    shutil.copyfile(index, scratch)
                env = {**os.environ, "GIT_INDEX_FILE": str(scratch)}
                env.setdefault("GIT_AUTHOR_NAME", "pretest")
                env.setdefault("GIT_AUTHOR_EMAIL", "pretest@localhost")
                env.setdefault("GIT_COMMITTER_NAME", "pretest")
                env.setdefault("GIT_COMMITTER_EMAIL", "pretest@localhost")
                git("add", "-A", env=env)
                tree = git("write-tree", env=env)
                sha = git(
                    "commit-tree",
                    tree,
                    "-p",
                    head,
                    "-m",
                    "pretest: working tree snapshot",
                    env=env,
                )
            label = f"working tree on {head[:12]} (snapshot {sha[:12]}, incl. uncommitted changes)"
    git("update-ref", "refs/pretest/snapshot", sha)
    return sha, label


def read_at(sha: str) -> Any:
    def read(path: str) -> str:
        return git("show", f"{sha}:{path}")

    return read


@dataclass
class Outcome:
    job: Job
    status: str
    executor: str
    seconds: float = 0.0
    error: str = ""
    notes: list[str] = field(default_factory=list)
    log: Path | None = None


class Gate:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.windows = os.name == "nt"
        self.distro = git_config(
            "pretest.wslDistro", "PRETEST_WSL_DISTRO", DEFAULT_DISTRO
        )
        cache = (
            os.environ.get("LOCALAPPDATA")
            or os.environ.get("XDG_CACHE_HOME")
            or str(Path.home() / ".cache")
        )
        default_home = Path(cache) / "aam-pretest"
        self.home = Path(git_config("pretest.home", "PRETEST_HOME", str(default_home)))
        self.run_dir = self.home / "runs" / time.strftime("%Y%m%d-%H%M%S")
        self.lock = threading.Lock()
        self.source_cache: str | None = None
        # Inner runners get the gate code as it was when this run started.
        self.source = Path(__file__).read_bytes()

    # -- WSL ----------------------------------------------------------------
    def wsl(self, *args: str, root: bool = True) -> list[str]:
        return [
            "wsl.exe",
            "-d",
            self.distro,
            "-u",
            "root" if root else CI_USER,
            "--cd",
            "/",
            "--exec",
            *args,
        ]

    def wsl_distros(self) -> list[str]:
        if shutil.which("wsl.exe") is None:
            return []
        completed = subprocess.run(
            ["wsl.exe", "-l", "-q"],
            capture_output=True,
            check=False,
            cwd=self.ascii_cwd(),
        )
        raw = completed.stdout
        text = (
            raw.decode("utf-16-le", "replace")
            if raw[1:2] == b"\x00"
            else raw.decode("utf-8", "replace")
        )
        return [
            line.strip().strip("\x00")
            for line in text.splitlines()
            if line.strip().strip("\x00")
        ]

    @staticmethod
    def ascii_cwd() -> str:
        return os.environ.get("SYSTEMROOT", "C:\\Windows") if os.name == "nt" else "/"

    def wsl_source(self) -> str:
        if self.source_cache is None:
            completed = subprocess.run(
                self.wsl("wslpath", "-a", str(ROOT)),
                capture_output=True,
                check=False,
                cwd=self.ascii_cwd(),
            )
            path = completed.stdout.decode("utf-8", "replace").strip()
            if completed.returncode != 0 or not path.startswith("/"):
                raise GateError(f"cannot translate {ROOT} into a WSL path")
            self.source_cache = path
        return self.source_cache

    def python_payload(self, mode: str, payload: dict[str, Any]) -> list[str]:
        encoded = base64.b64encode(json.dumps(payload).encode()).decode()
        return [mode, encoded]

    def run_inner(
        self, command: list[str], log: Path, prefix: str
    ) -> dict[str, Any] | None:
        """Run an inner gate process, tee it into ``log``, return its result marker."""
        result: dict[str, Any] | None = None
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("wb") as handle:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=self.ascii_cwd(),
                env=self.inner_env(),
            )
            assert process.stdin is not None and process.stdout is not None
            if "-" in command:
                process.stdin.write(self.source)
            process.stdin.close()
            for raw in process.stdout:
                handle.write(raw)
                handle.flush()
                line = raw.decode("utf-8", "replace").rstrip("\r\n")
                if line.startswith(MARK):
                    kind, _, body = line[len(MARK) :].partition("::")
                    try:
                        data = json.loads(body)
                    except ValueError:
                        continue
                    if kind == "step":
                        self.print(f"  [{prefix}] step {data['index']}: {data['name']}")
                    else:
                        result = data
            process.wait()
        return result

    @staticmethod
    def job_env() -> dict[str, str]:
        """Host environment minus state that would leak into a CI job."""
        env = git_env()
        for key in list(env):
            if key.startswith(
                (
                    "PRE_COMMIT",
                    "VIRTUAL_ENV",
                    "UV_",
                    "PYTEST_",
                    "CONDA",
                    "PYTHONIOENCODING",
                )
            ) or key in ("PYTHONPATH", "PYTHONHOME"):
                env.pop(key)
        return env

    def inner_env(self) -> dict[str, str]:
        env = self.job_env()
        env["PYTHONIOENCODING"] = "utf-8"
        return env

    def print(self, text: str) -> None:
        with self.lock:
            sys.stdout.write(text + "\n")
            sys.stdout.flush()

    # -- preflight ------------------------------------------------------------
    def linux_preflight(
        self, jobs: list[Job], sha: str, pins: dict[str, str]
    ) -> list[str]:
        packages: list[str] = []
        for job in jobs:
            packages.extend(p for p in job_apt_packages(job) if p not in packages)
        if self.windows:
            distros = self.wsl_distros()
            if self.distro not in distros:
                return [
                    f"WSL distro {self.distro!r} is missing (found: {', '.join(distros) or 'none'}); "
                    f"install it (wsl --install -d {DEFAULT_DISTRO}) then run python scripts/pretest.py --setup-wsl"
                ]
            payload = {"packages": packages, "source": self.wsl_source(), "sha": sha}
            command = self.wsl(
                "python3", "-", *self.python_payload("--internal-sync", payload)
            )
        else:
            return self.native_linux_preflight(packages, pins)
        result = self.run_inner(command, self.run_dir / "wsl-sync.log", "wsl")
        if result is None:
            return [f"WSL sync failed; see {self.run_dir / 'wsl-sync.log'}"]
        return self.check_facts(result, pins)

    def native_linux_preflight(
        self, packages: list[str], pins: dict[str, str]
    ) -> list[str]:
        facts: dict[str, Any] = {"errors": [], "packages": {}}
        os_release = Path("/etc/os-release").read_text(encoding="utf-8")
        version = re.search(r'^VERSION_ID="?([^"\n]+)', os_release, re.M)
        facts["ubuntu"] = version.group(1) if version else "unknown"
        for tool in ("uv", "node"):
            located = shutil.which(tool)
            done = (
                subprocess.run([located, "--version"], capture_output=True, check=False)
                if located
                else None
            )
            facts[tool] = (
                done.stdout.decode().strip() if done and done.returncode == 0 else ""
            )
        for package in packages:
            done = subprocess.run(
                ["dpkg-query", "-W", "-f=${Status}\t${Version}", package],
                capture_output=True,
                check=False,
            )
            status, _, found = done.stdout.decode().partition("\t")
            facts["packages"][package] = (
                found if status.strip() == "install ok installed" else ""
            )
        return self.check_facts(facts, pins)

    def check_facts(self, facts: dict[str, Any], pins: dict[str, str]) -> list[str]:
        problems = list(facts.get("errors", []))
        hint = "run python scripts/pretest.py --setup-wsl"
        if facts.get("ubuntu") != UBUNTU_LATEST:
            problems.append(
                f"local Ubuntu is {facts.get('ubuntu')}, GitHub ubuntu-latest is {UBUNTU_LATEST}"
            )
        if facts.get("uv", "").split()[1:2] != [pins["uv"]]:
            problems.append(
                f"uv {pins['uv']} required, found {facts.get('uv') or 'none'}; {hint}"
            )
        node = facts.get("node", "")
        if not node.startswith(f"v{pins['node']}."):
            problems.append(
                f"Node {pins['node']}.x required, found {node or 'none'}; {hint}"
            )
        missing = [p for p, v in facts.get("packages", {}).items() if not v]
        if missing:
            problems.append(f"apt packages missing: {' '.join(missing)}; {hint}")
        office = facts.get("packages", {}).get("libreoffice-writer")
        if office and _version_tuple(office) < LIBREOFFICE_MIN:
            problems.append(
                f"LibreOffice {office} < CI baseline {'.'.join(map(str, LIBREOFFICE_MIN))}; {hint}"
            )
        age = facts.get("apt_index_age_days")
        if age is not None and age > 7:
            self.print(
                f"WARNING: WSL apt indexes are {age} days old; CI installs today's LibreOffice. {hint}"
            )
        self.facts = facts
        return problems

    # -- Windows ----------------------------------------------------------------
    def windows_tools(self, pins: dict[str, str]) -> tuple[list[str], int, list[str]]:
        """Return (PATH prefix, accepted Node major, problems) for Windows jobs."""
        problems: list[str] = []
        prefix: list[str] = []
        uv_dir = self.home / "tools" / f"uv-{pins['uv']}"
        if not (uv_dir / "uv.exe").exists():
            uv = shutil.which("uv")
            located = ""
            if uv:
                done = subprocess.run(
                    [uv, "--version"], capture_output=True, check=False
                )
                if done.stdout.decode().split()[1:2] == [pins["uv"]]:
                    located = uv
            if not located and shutil.which("uvx"):
                done = subprocess.run(
                    [
                        "uvx",
                        "--from",
                        f"uv=={pins['uv']}",
                        "python",
                        "-c",
                        "import shutil; print(shutil.which('uv'))",
                    ],
                    capture_output=True,
                    check=False,
                    cwd=str(self.home.parent),
                )
                located = (
                    done.stdout.decode().strip().splitlines()[-1]
                    if done.returncode == 0 and done.stdout.strip()
                    else ""
                )
            if located:
                uv_dir.mkdir(parents=True, exist_ok=True)
                for name in ("uv.exe", "uvx.exe"):
                    candidate = Path(located).with_name(name)
                    if candidate.exists():
                        shutil.copy2(candidate, uv_dir / name)
        if (uv_dir / "uv.exe").exists():
            prefix.append(str(uv_dir))
        else:
            problems.append(
                f"uv {pins['uv']} not available (install uv/uvx so `uvx --from uv=={pins['uv']}` works)"
            )
        node_dir = git_config("pretest.windowsNode", "PRETEST_WINDOWS_NODE")
        node = (
            str(Path(node_dir) / "node.exe")
            if node_dir
            else (shutil.which("node") or "")
        )
        minimum = int(
            git_config(
                "pretest.windowsNodeMajor", "PRETEST_WINDOWS_NODE_MAJOR", pins["node"]
            )
        )
        version = ""
        if node and Path(node).exists():
            done = subprocess.run([node, "--version"], capture_output=True, check=False)
            version = done.stdout.decode().strip()
        major = int(version.lstrip("v").split(".")[0]) if version else 0
        if major < minimum:
            problems.append(
                f"Windows jobs need Node >= {minimum} (CI: {pins['node']}); found {version or 'none'} at {node or 'PATH'}. "
                "Set git config pretest.windowsNode <dir with node.exe> (and pretest.windowsNodeMajor to accept an older major)"
            )
        elif node_dir:
            prefix.append(node_dir)
        if not shutil.which("pwsh"):
            problems.append("PowerShell 7 (pwsh) is required for `shell: pwsh` steps")
        return prefix, minimum, problems

    def windows_env(self, job: Job, prefix: list[str]) -> dict[str, str]:
        env = self.job_env()
        short = self.home / "t" / job.key
        temp, basetemp = short / "tmp", short / "bt"
        rmtree(short)
        temp.mkdir(parents=True)
        env["TEMP"] = env["TMP"] = str(temp)
        env["PYTEST_ADDOPTS"] = f"--basetemp={basetemp}"
        env["PATH"] = os.pathsep.join([*prefix, env.get("PATH", "")])
        return env

    # -- dispatch ---------------------------------------------------------------
    def executor_label(self, job: Job) -> str:
        if job.aggregate:
            return "gate (aggregate)"
        if job.platform == "linux":
            return f"WSL {self.distro}" if self.windows else "this Linux host"
        if job.platform == "windows":
            return "this Windows host" if self.windows else "-"
        return "-"

    def run_job(self, job: Job, sha: str, ref: str, context: dict[str, Any]) -> Outcome:
        label = self.executor_label(job)
        log = self.run_dir / f"{job.qualified.replace(':', '_')}.log"
        started = time.monotonic()
        self.print(f"> {job.qualified} ({job.runs_on} -> {label}) started")
        payload: dict[str, Any] = {
            "workflow": job.workflow,
            "job": job.key,
            "platform": job.platform,
            "sha": sha,
            "ref": ref,
        }
        if job.platform == "linux" and self.windows:
            payload.update(
                source=str(WSL_HOME / "mirror.git"),
                workspace=str(WSL_HOME / "jobs" / job.key),
                runner_temp=str(WSL_HOME / "tmp" / job.key),
            )
            command = self.wsl(
                "python3", "-", *self.python_payload("--internal-job", payload)
            )
        elif job.platform == "linux":
            base = self.home / "linux"
            payload.update(
                source=str(ROOT),
                workspace=str(base / "jobs" / job.key),
                runner_temp=str(base / "tmp" / job.key),
                linux_env={
                    k: os.environ[k]
                    for k in ("HOME", "USER", "LOGNAME", "PATH")
                    if k in os.environ
                },
            )
            command = [
                sys.executable,
                "-",
                *self.python_payload("--internal-job", payload),
            ]
        else:
            env = self.windows_env(job, context["windows_prefix"])
            payload.update(
                source=str(ROOT),
                workspace=str(self.home / "ws" / job.key),
                runner_temp=str(self.home / "t" / job.key / "rt"),
                host_env=env,
                node_major_min=context["windows_node_major"],
                git_bash=git_bash(),
            )
            command = [
                sys.executable,
                "-",
                *self.python_payload("--internal-job", payload),
            ]
        result = self.run_inner(command, log, job.key)
        seconds = time.monotonic() - started
        if result is None:
            outcome = Outcome(
                job, "FAIL", label, seconds, "job runner crashed; see log", log=log
            )
        else:
            outcome = Outcome(
                job,
                result["status"],
                label,
                seconds,
                result.get("error", ""),
                result.get("notes", []),
                log,
            )
        self.print(
            f"< {job.qualified}: {outcome.status} in {fmt(seconds)}"
            + (f" - {outcome.error}" if outcome.error else "")
        )
        if outcome.status == "FAIL":
            tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]
            self.print(
                "\n".join(f"    | {line}" for line in tail if not line.startswith(MARK))
            )
        return outcome


def git_bash() -> str:
    """Git for Windows' bash (what GitHub's `shell: bash` uses), not WSL's."""
    git_exe = shutil.which("git")
    if git_exe:
        for candidate in (
            Path(git_exe).parents[1] / "bin" / "bash.exe",
            Path(git_exe).parents[1] / "usr" / "bin" / "bash.exe",
        ):
            if candidate.exists():
                return str(candidate)
    return shutil.which("bash") or "bash"


def fmt(seconds: float) -> str:
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


def resolve_selection(jobs: list[Job], names: list[str]) -> set[str]:
    wanted = set()
    for raw in names:
        for name in filter(None, (n.strip() for n in raw.split(","))):
            matches = [
                j.qualified
                for j in jobs
                if name in (j.qualified, j.key, j.qualified.replace(":", "-"))
            ]
            if not matches:
                valid = ", ".join(j.qualified for j in jobs)
                raise GateError(f"unknown job {name!r}; valid: {valid}")
            if len(matches) > 1:
                raise GateError(f"ambiguous job {name!r}: {', '.join(matches)}")
            wanted.update(matches)
    return wanted


def pytest_files(job: Job) -> set[str]:
    text = json.dumps(job.data.get("steps", []))
    return set(re.findall(r"tests/[\w/.-]+\.py", text))


def coverage_note(job: Job, outcomes: list[Outcome]) -> str:
    files = pytest_files(job)
    covered: set[str] = set()
    for outcome in outcomes:
        if outcome.status == "PASS":
            covered |= pytest_files(outcome.job)
    if any(o.status == "PASS" and o.job.qualified == "release:test" for o in outcomes):
        covered = files
    if not files:
        return ""
    return f"{len(files & covered)}/{len(files)} of its pytest files passed in other local jobs"


def print_table(outcomes: list[Outcome], gate: Gate, header: str) -> None:
    rows = [("CI job", "CI runner", "Local executor", "Result", "Time")]
    for o in outcomes:
        rows.append(
            (
                o.job.qualified,
                o.job.runs_on,
                o.executor,
                o.status,
                fmt(o.seconds) if o.seconds else "-",
            )
        )
    widths = [max(len(r[i]) for r in rows) for i in range(5)]
    line = "-+-".join("-" * w for w in widths)
    gate.print("\n" + header)
    gate.print(line)
    for i, row in enumerate(rows):
        gate.print(" | ".join(cell.ljust(widths[n]) for n, cell in enumerate(row)))
        if i == 0:
            gate.print(line)
        elif outcomes[i - 1].error or outcomes[i - 1].notes:
            o = outcomes[i - 1]
            for note in [*([o.error] if o.error else []), *o.notes]:
                gate.print(f"    - {note}")
    gate.print(line)


def main_gate(args: argparse.Namespace) -> int:
    gate = Gate(args)
    sha, label = snapshot(args.rev)
    jobs = load_jobs(read_at(sha))
    selected = {j.qualified for j in jobs}
    if args.only:
        selected = resolve_selection(jobs, args.only)
    if args.skip:
        selected -= resolve_selection(jobs, args.skip)
    pins = workflow_pins(jobs)
    ref = "refs/heads/" + (
        git("rev-parse", "--abbrev-ref", "HEAD", check=False) or "local"
    )
    gate.print(f"CI-parity gate for {label}")
    gate.print(
        f"workflows: ci.yml (all jobs), release.yml (test); pins: uv {pins['uv']}, Node {pins['node']}, Python {pins['python']}"
    )
    gate.print(f"logs: {gate.run_dir}")
    outcomes: dict[str, Outcome] = {}
    runnable: list[Job] = []
    for job in jobs:
        executor = gate.executor_label(job)
        if job.qualified not in selected:
            outcomes[job.qualified] = Outcome(
                job, "not selected", executor, error="excluded by --only/--skip"
            )
        elif job.aggregate:
            continue
        elif job.platform == "linux" or (job.platform == "windows" and gate.windows):
            runnable.append(job)
        else:
            reason = NOT_VERIFIED.get(
                job.platform, f"no local executor for runs-on {job.runs_on!r}"
            )
            if job.platform == "windows":
                reason = "needs a Windows host"
            outcomes[job.qualified] = Outcome(job, "NOT VERIFIED", "-", error=reason)
    if args.list or args.dry_run:
        for job in jobs:
            outcomes.setdefault(
                job.qualified, Outcome(job, "planned", gate.executor_label(job))
            )
            if args.dry_run and job.qualified in selected and not job.aggregate:
                gate.print(
                    f"\n{job.qualified} [{job.runs_on} -> {gate.executor_label(job)}]"
                )
                for step in plan_steps(job):
                    extra = (
                        step.detail.get("reason")
                        or " ".join(step.detail.get("packages", []))
                        or step.detail.get("version", "")
                    )
                    gate.print(
                        f"  {step.index:>2}. {step.kind:<14} {step.name}"
                        + (f"  [{extra}]" if extra else "")
                    )
        print_table([outcomes[j.qualified] for j in jobs], gate, "Job mapping")
        return 0
    context: dict[str, Any] = {}
    blocked: dict[str, str] = {}
    linux_jobs = [j for j in runnable if j.platform == "linux"]
    if linux_jobs:
        problems = gate.linux_preflight(linux_jobs, sha, pins)
        for job in linux_jobs if problems else []:
            blocked[job.qualified] = "prerequisite: " + "; ".join(problems)
    windows_jobs = [j for j in runnable if j.platform == "windows"]
    if windows_jobs:
        prefix, minimum, problems = gate.windows_tools(pins)
        context.update(windows_prefix=prefix, windows_node_major=minimum)
        for job in windows_jobs if problems else []:
            blocked[job.qualified] = "prerequisite: " + "; ".join(problems)
    for name, reason in blocked.items():
        job = next(j for j in runnable if j.qualified == name)
        outcomes[name] = Outcome(job, "FAIL", gate.executor_label(job), error=reason)
        gate.print(f"! {name}: FAIL - {reason}")
    todo = [j for j in runnable if j.qualified not in blocked]
    order = [
        "integration-tests",
        "test",
        "unit-tests",
        "python311-mcp-smoke",
        "windows-smoke",
        "linux-vsix-smoke",
        "static-analysis",
    ]
    todo.sort(key=lambda j: order.index(j.key) if j.key in order else len(order))
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = [pool.submit(gate.run_job, job, sha, ref, context) for job in todo]
        try:
            for future in futures:
                outcome = future.result()
                outcomes[outcome.job.qualified] = outcome
        except KeyboardInterrupt:
            gate.print("interrupted: stopping WSL job runners")
            if gate.windows:
                subprocess.run(
                    gate.wsl("pkill", "-f", "internal-job"),
                    check=False,
                    cwd=gate.ascii_cwd(),
                )
            raise
    ordered = [o for o in (outcomes.get(j.qualified) for j in jobs) if o is not None]
    for outcome in ordered:
        if outcome.status == "NOT VERIFIED":
            note = coverage_note(outcome.job, ordered)
            if note:
                outcome.notes.append(note)
    for job in jobs:
        if job.aggregate and job.qualified in selected:
            needs = job.data.get("needs") or []
            needed = [outcomes[f"{job.workflow.split('.')[0]}:{n}"] for n in needs]
            failed = [o.job.key for o in needed if o.status == "FAIL"]
            status = "FAIL" if failed else "PASS"
            unverified = [o.job.key for o in needed if o.status not in ("PASS", "FAIL")]
            notes = (
                [f"needs not verified locally: {', '.join(unverified)}"]
                if unverified
                else []
            )
            outcomes[job.qualified] = Outcome(
                job,
                status,
                "gate (aggregate)",
                error=f"failed: {', '.join(failed)}" if failed else "",
                notes=notes,
            )
    ordered = [outcomes[j.qualified] for j in jobs if j.qualified in outcomes]
    print_table(
        ordered,
        gate,
        f"CI job -> local result ({label}; wall time {fmt(time.monotonic() - started)})",
    )
    summary = [
        {
            "job": o.job.qualified,
            "runs_on": o.job.runs_on,
            "executor": o.executor,
            "status": o.status,
            "seconds": round(o.seconds, 1),
            "error": o.error,
            "notes": o.notes,
            "log": str(o.log or ""),
        }
        for o in ordered
    ]
    gate.run_dir.mkdir(parents=True, exist_ok=True)
    (gate.run_dir / "summary.json").write_text(
        json.dumps({"snapshot": sha, "label": label, "jobs": summary}, indent=2),
        encoding="utf-8",
    )
    failed = [o for o in ordered if o.status == "FAIL"]
    unverified = [o for o in ordered if o.status == "NOT VERIFIED"]
    if failed:
        gate.print(
            f"\nGATE FAILED: {', '.join(o.job.qualified for o in failed)} (logs in {gate.run_dir})"
        )
        return 1
    gate.print(
        f"\nGATE PASSED{' (NOT VERIFIED: ' + ', '.join(o.job.qualified for o in unverified) + ')' if unverified else ''}"
    )
    return 0


def main_quick(args: argparse.Namespace) -> int:
    """Commit-time subset: offline CI commands in the working tree."""
    gate = Gate(args)
    jobs = load_jobs(lambda path: (ROOT / path).read_text(encoding="utf-8"))
    pins = workflow_pins(jobs)
    problems = []
    env = gate.inner_env()
    env["UV_PROJECT_ENVIRONMENT"] = str(gate.home / f"quick-venv-py{pins['python']}")
    env["UV_PYTHON"] = pins["python"]
    if gate.windows:
        prefix, _, issues = gate.windows_tools(pins)
        problems += issues
        env["PATH"] = os.pathsep.join([*prefix, env.get("PATH", "")])
    else:
        found = subprocess.run(
            ["uv", "--version"], capture_output=True, check=False
        ).stdout.decode()
        if found.split()[1:2] != [pins["uv"]]:
            problems.append(
                f"uv {pins['uv']} required, found {found.strip() or 'none'}"
            )
    missing = [name for name in REQUIRED_FILES if not (ROOT / name).is_file()]
    if missing:
        problems.append(f"missing required files: {', '.join(missing)}")
    if problems:
        for problem in problems:
            gate.print(f"QUICK FAILED (prerequisite): {problem}")
        return 1
    started = time.monotonic()
    results = []
    sync = ["uv", "sync", "--frozen"]
    for label, directory, command in (
        ("uv sync", ".", " ".join(sync)),
        *QUICK_COMMANDS,
    ):
        step_started = time.monotonic()
        argv = command.split()
        if argv[2:3] == ["mypy"] and not sys.platform.startswith("linux"):
            # CI type-checks on Linux; os.killpg & co. only exist there.
            argv.append("--platform=linux")
            command += " --platform=linux"
        located = shutil.which(argv[0], path=env["PATH"])
        if not located:
            results.append((label, "FAIL", 0.0, f"{argv[0]} not found"))
            continue
        done = subprocess.run(
            [located, *argv[1:]],
            cwd=str(ROOT / directory),
            env=env,
            capture_output=True,
            check=False,
        )
        seconds = time.monotonic() - step_started
        status = "PASS" if done.returncode == 0 else "FAIL"
        output = (done.stdout + done.stderr).decode("utf-8", "replace").strip()
        results.append(
            (label, status, seconds, "" if status == "PASS" else output[-3000:])
        )
        gate.print(f"  {status:<4} {label:<22} {seconds:6.1f}s  {command}")
        if status == "FAIL":
            gate.print(
                "\n".join(f"       | {line}" for line in output.splitlines()[-30:])
            )
    failed = [r for r in results if r[1] == "FAIL"]
    gate.print(
        f"quick gate: {len(results) - len(failed)}/{len(results)} passed in {fmt(time.monotonic() - started)}; uv audit and the test jobs run in the pre-push gate"
    )
    return 1 if failed else 0


def main_setup(gate: Gate) -> int:
    if not gate.windows:
        command = ["sudo", "bash", str(ROOT / "scripts" / "setup_local_ci_wsl.sh")]
    else:
        if gate.distro not in gate.wsl_distros():
            gate.print(
                f"WSL distro {gate.distro!r} is missing; install it first: wsl --install -d {DEFAULT_DISTRO}"
            )
            return 2
        command = gate.wsl("bash", f"{gate.wsl_source()}/scripts/setup_local_ci_wsl.sh")
    return subprocess.run(command, check=False, cwd=gate.ascii_cwd()).returncode


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    internal = argv[:1] in (["--internal-sync"], ["--internal-job"])
    if hasattr(sys.stdout, "reconfigure"):
        # Inner runners talk UTF-8 to the host; the console only needs to survive.
        sys.stdout.reconfigure(encoding="utf-8" if internal else None, errors="replace")  # type: ignore[union-attr]
    if internal:
        payload = json.loads(base64.b64decode(argv[1]).decode())
        return (
            inner_sync(payload) if argv[0] == "--internal-sync" else inner_job(payload)
        )
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--quick",
        action="store_true",
        help="offline commit-time subset in the working tree",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="run only these jobs (repeatable, comma-separated)",
    )
    parser.add_argument(
        "--skip",
        action="append",
        default=[],
        help="skip these jobs (repeatable, comma-separated)",
    )
    parser.add_argument("--rev", help="gate this commit instead of the working tree")
    parser.add_argument(
        "--jobs", type=int, default=4, help="jobs to run in parallel (default 4)"
    )
    parser.add_argument(
        "--list", action="store_true", help="print the CI job -> local executor mapping"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print how every step would be executed"
    )
    parser.add_argument(
        "--setup-wsl",
        action="store_true",
        help="provision the WSL distro (setup_local_ci_wsl.sh)",
    )
    args = parser.parse_args(argv)
    try:
        if args.setup_wsl:
            return main_setup(Gate(args))
        if args.quick:
            return main_quick(args)
        return main_gate(args)
    except (GateError, YamlError) as exc:
        print(f"pretest: ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
