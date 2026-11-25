"""The local CI-parity gate must read the workflows exactly like GitHub does."""

import argparse
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))


def _load_gate():
    spec = importlib.util.spec_from_file_location(
        "pretest_gate", ROOT / "scripts" / "pretest.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gate = _load_gate()


def _github(document):
    """PyYAML follows YAML 1.1 and turns the `on:` key into True."""
    if isinstance(document, dict):
        return {
            ("on" if key is True else key): _github(value)
            for key, value in document.items()
        }
    if isinstance(document, list):
        return [_github(item) for item in document]
    return document


@pytest.mark.parametrize("path", [*WORKFLOWS, ROOT / ".pre-commit-config.yaml"])
def test_stdlib_loader_matches_pyyaml_on_repository_files(path):
    text = path.read_text(encoding="utf-8")
    assert gate.load_yaml(text) == _github(yaml.safe_load(text))


@pytest.mark.parametrize(
    "text",
    [
        "a: |\n  one\n\n  two  # kept\n    more\nb: 1\n",
        "a: >-\n  folded\n  line\n\n  next\nb: [x, 'y, z', \"w[1]\"]\n",
        "a: |-\n  keep\n\n\nc:\n- k: v\n  n:\n    - 1\n    - two\n- plain # note\n",
        "a: >\n  x\n    indented\n  y\nb: 'it''s'\nc: \"q\\\"d\"\nd:\ne: ~\n",
        "jobs:\n  x:\n    steps:\n      - run: echo a:b\n        if: runner.os == 'Linux'\n",
    ],
)
def test_stdlib_loader_matches_pyyaml_on_edge_cases(text):
    assert gate.load_yaml(text) == yaml.safe_load(text)


@pytest.mark.parametrize(
    "text", ["a: &x 1\n", "a: {b: 1}\n", "a:\n\tb: 1\n", "- - nested\n"]
)
def test_unsupported_yaml_fails_loudly(text):
    with pytest.raises(gate.YamlError):
        gate.load_yaml(text)


def test_expressions_cover_the_workflow_subset():
    contexts = {
        "env": {"NODE_VERSION": "24"},
        "runner": {"os": "Linux", "temp": "/t"},
        "inputs": {},
        "needs": {"x": {"result": "success"}},
    }
    assert gate.substitute("${{ env.NODE_VERSION }}", contexts) == "24"
    assert gate.substitute("${{ runner.temp }}/fonts", contexts) == "/t/fonts"
    assert gate.evaluate("runner.os == 'linux'", contexts) is True
    assert gate.evaluate("inputs.prerelease || false", contexts) is False
    assert gate.evaluate("always()", contexts) is True
    assert gate.evaluate("needs.x.result != 'success'", contexts) is False
    with pytest.raises(gate.GateError):
        gate.evaluate("secrets.VSCE_PAT", contexts)
    with pytest.raises(gate.GateError):
        gate.evaluate("hashFiles('x')", contexts)


def _jobs():
    return gate.load_jobs(lambda path: (ROOT / path).read_text(encoding="utf-8"))


def test_every_gated_job_has_a_local_plan_and_shared_pins():
    jobs = _jobs()
    assert {job.qualified for job in jobs} >= {
        "ci:docs-check",
        "ci:static-analysis",
        "ci:python311-mcp-smoke",
        "ci:npm-security",
        "ci:macos-smoke",
        "ci:windows-smoke",
        "ci:linux-vsix-smoke",
        "ci:unit-tests",
        "ci:integration-tests",
        "ci:test-summary",
        "release:test",
    }
    for job in jobs:
        steps = gate.plan_steps(job)
        assert steps, job.qualified
        assert job.aggregate or steps[0].kind == "checkout", job.qualified
    assert [job.qualified for job in jobs if job.aggregate] == ["ci:test-summary"]
    pins = gate.workflow_pins(jobs)
    assert re.fullmatch(r"\d+\.\d+\.\d+", pins["uv"])
    assert pins["node"].isdigit() and re.fullmatch(r"3\.\d+", pins["python"])


def test_integration_job_still_installs_the_baselined_libreoffice():
    jobs = {job.qualified: job for job in _jobs()}
    integration = gate.job_apt_packages(jobs["ci:integration-tests"])
    assert {"libreoffice-writer", "python3-uno", "fonts-liberation"} <= set(integration)
    assert jobs["ci:integration-tests"].runs_on == "ubuntu-latest"
    # Every other Linux job runs with LibreOffice hidden, as on a fresh runner.
    others = [
        job
        for name, job in jobs.items()
        if job.platform == "linux" and name != "ci:integration-tests"
    ]
    assert not any(
        p.startswith("libreoffice")
        for job in others
        for p in gate.job_apt_packages(job)
    )


def test_not_applicable_steps_still_exist_in_their_workflow():
    jobs = {(job.workflow, job.key): job for job in _jobs()}
    for workflow, key, name in gate.NOT_APPLICABLE:
        steps = jobs[workflow, key].data["steps"]
        assert any(step.get("name") == name for step in steps), name


def test_quick_commands_are_verbatim_workflow_commands():
    text = "\n".join(path.read_text(encoding="utf-8") for path in WORKFLOWS)
    for _label, _directory, command in gate.QUICK_COMMANDS:
        core = command.removeprefix("uv run python ")
        assert core in text, command


def test_apt_steps_and_file_commands(tmp_path):
    assert gate.apt_packages(
        "sudo apt-get update && sudo apt-get install -y --no-install-recommends a b"
    ) == ["a", "b"]
    assert gate.apt_packages("sudo apt-get update\nmake") is None
    # The gate replays CI's exact install arguments with --simulate.
    assert gate.apt_installs(
        "sudo apt-get update\nsudo apt-get install -y xvfb libgtk-3-0"
    ) == [["-y", "xvfb", "libgtk-3-0"]]
    jobs = {job.qualified: job for job in _jobs()}
    apt = next(
        s for s in gate.plan_steps(jobs["ci:integration-tests"]) if s.kind == "apt"
    )
    assert apt.detail["installs"][0][:2] == ["-y", "--no-install-recommends"]
    commands = tmp_path / "env"
    commands.write_text("A=1\nB<<EOF\nx\ny\nEOF\nC=a=b\n", encoding="utf-8")
    assert gate._read_env_file(commands) == {"A": "1", "B": "x\ny", "C": "a=b"}
    assert gate._version_tuple("4:26.2.7.3-0ubuntu0.26.04.1") == (26, 2, 7, 3)
    assert gate._version_tuple("4:26.2.7.3-0ubuntu0.26.04.1") >= gate.LIBREOFFICE_MIN


@pytest.mark.parametrize("long_paths", [True, False])
def test_windows_basetemp_is_short_and_lifts_max_path_only_when_needed(
    tmp_path, monkeypatch, long_paths
):
    monkeypatch.setenv("PRETEST_WINDOWS_TEMP", str(tmp_path / "aamg"))
    monkeypatch.setattr(gate, "windows_long_paths", lambda: long_paths)
    job = next(job for job in _jobs() if job.key == "windows-smoke")
    notes = []
    env = gate.Gate(argparse.Namespace()).windows_env(job, [], notes)
    option = env["PYTEST_ADDOPTS"]
    # pytest shlex-splits PYTEST_ADDOPTS: backslashes would be swallowed.
    assert "\\" not in option and option.endswith("/b/ws")
    assert option.startswith("--basetemp=//?/") is not long_paths
    assert bool(notes) is not long_paths
    assert (tmp_path / "aamg" / "b").is_dir() and (
        tmp_path / "aamg" / "t" / "ws"
    ).is_dir()


@pytest.mark.parametrize(("scale", "outcome"), [("1", "failed"), ("4", "passed")])
def test_timeout_scale_plugin_stretches_pytest_timeout_markers(
    tmp_path, scale, outcome
):
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    (plugin / f"{gate.TIMEOUT_PLUGIN}.py").write_text(
        gate.TIMEOUT_PLUGIN_SOURCE, encoding="utf-8"
    )
    (tmp_path / "test_slow.py").write_text(
        "import time\nimport pytest\n\n\n@pytest.mark.timeout(0.5)\n"
        "def test_slow():\n    time.sleep(1.0)\n",
        encoding="utf-8",
    )
    env = {
        **os.environ,
        "PYTHONPATH": str(plugin),
        "PRETEST_TIMEOUT_SCALE": scale,
        "PYTEST_ADDOPTS": "",
    }
    done = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            gate.TIMEOUT_PLUGIN,
            "-p",
            "no:cacheprovider",
            str(tmp_path / "test_slow.py"),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    output = done.stdout + done.stderr
    if outcome == "passed":
        assert done.returncode == 0 and "1 passed" in output, output
    else:
        # signal method reports "1 failed"; the Windows thread method exits.
        assert done.returncode != 0 and "Timeout" in output, output


@pytest.mark.skipif(os.name != "nt", reason="Win32 MAX_PATH only")
def test_rmtree_removes_trees_deeper_than_max_path(tmp_path):
    root = tmp_path / "bt"
    deep = Path(r"\\?" + "\\" + str(root.resolve())).joinpath(*["d" * 60] * 5)
    deep.mkdir(parents=True)
    (deep / ("f" * 60 + ".md")).write_text("x", encoding="utf-8")
    assert len(str(deep)) > 300
    gate.rmtree(root)
    assert not root.exists()


def _git(cwd, *args):
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


@pytest.mark.parametrize("linked_worktree", [False, True])
def test_wsl_mirror_fetches_from_the_common_git_dir(
    tmp_path, monkeypatch, linked_worktree
):
    """A linked worktree's .git is a file naming a Windows gitdir WSL cannot follow."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "--quiet")
    (repo / "f.txt").write_text("x", encoding="utf-8")
    _git(repo, "add", "f.txt")
    _git(repo, "commit", "--quiet", "-m", "init")
    root = repo
    if linked_worktree:
        root = tmp_path / "wt"
        _git(repo, "worktree", "add", "--quiet", "-b", "wt", str(root))
        assert (root / ".git").is_file()
    monkeypatch.setattr(gate, "ROOT", root)
    runner = gate.Gate(argparse.Namespace())
    # Stand-in for `wsl.exe wslpath -a <path>`: echo the path with a POSIX prefix.
    monkeypatch.setattr(
        runner,
        "wsl",
        lambda *args: [
            sys.executable,
            "-c",
            "import sys; print('/mnt/' + sys.argv[-1].replace(chr(92), '/'))",
            *args,
        ],
    )
    source = runner.wsl_git_source()
    expected = (repo / ".git").resolve().as_posix()
    assert source.lower().endswith(expected.lower())
    assert "worktrees" not in source
