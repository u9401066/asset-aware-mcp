"""Release metadata audit regressions."""

from __future__ import annotations

import json
import runpy
import zipfile
from pathlib import Path
from typing import Any

import pytest


def test_release_link_audit_accepts_main_and_rejects_retired_master(
    tmp_path: Path,
) -> None:
    namespace: dict[str, Any] = runpy.run_path("scripts/audit_release_artifacts.py")
    check_links = namespace["check_links"]
    check_links.__globals__["ROOT"] = tmp_path
    paths = [
        "pyproject.toml",
        "vscode-extension/README.md",
        "README.md",
        "README.zh-TW.md",
    ]
    for relative in paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "https://github.com/u9401066/asset-aware-mcp/blob/main/README.md",
            encoding="utf-8",
        )

    assert check_links() == []

    (tmp_path / "README.md").write_text(
        "https://github.com/u9401066/asset-aware-mcp/blob/master/README.md",
        encoding="utf-8",
    )
    assert check_links() == ["README.md: contains stale 'blob/master' link"]


def test_required_artifact_modes_fail_closed(tmp_path: Path) -> None:
    namespace: dict[str, Any] = runpy.run_path("scripts/audit_release_artifacts.py")
    namespace["check_required_artifacts"].__globals__["ROOT"] = tmp_path
    check_required_artifacts = namespace["check_required_artifacts"]
    artifact_paths = namespace["artifact_paths"]

    assert check_required_artifacts("1.2.3", "metadata") == []
    assert [
        Path(error.split(": required", maxsplit=1)[0]).name
        for error in check_required_artifacts("1.2.3", "python")
    ] == [
        "asset_aware_mcp-1.2.3.tar.gz",
        "asset_aware_mcp-1.2.3-py3-none-any.whl",
    ]
    assert [
        Path(error.split(": required", maxsplit=1)[0]).name
        for error in check_required_artifacts("1.2.3", "vsix")
    ] == ["asset-aware-mcp-1.2.3.vsix"]
    assert len(check_required_artifacts("1.2.3", "all")) == 3

    for artifact in artifact_paths("1.2.3").values():
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.touch()
    assert check_required_artifacts("1.2.3", "all") == []


def test_public_doc_version_audit_checks_all_release_facing_readmes(
    tmp_path: Path,
) -> None:
    namespace: dict[str, Any] = runpy.run_path("scripts/audit_release_artifacts.py")
    check_public_doc_versions = namespace["check_public_doc_versions"]
    check_public_doc_versions.__globals__["ROOT"] = tmp_path

    content = {
        "README.md": "## v1.2.3 current\n",
        "README.zh-TW.md": "## v1.2.3 最新\n",
        "vscode-extension/README.md": (
            "## What's New in v1.2.3\nasset-aware-mcp/v1.2.3/resources/banner.png\n"
        ),
    }
    for relative, text in content.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    assert check_public_doc_versions("1.2.3") == []

    (tmp_path / "README.zh-TW.md").write_text("## v1.2.2 舊版\n", encoding="utf-8")
    assert check_public_doc_versions("1.2.3") == [
        "README.zh-TW.md: missing current-version marker '## v1.2.3 '"
    ]


def test_vsix_audit_rejects_generated_media_at_extension_root(tmp_path: Path) -> None:
    namespace: dict[str, Any] = runpy.run_path("scripts/audit_release_artifacts.py")
    check_vsix = namespace["check_vsix"]
    check_vsix.__globals__["ROOT"] = tmp_path
    vsix = tmp_path / "vscode-extension" / "asset-aware-mcp-1.2.3.vsix"
    vsix.parent.mkdir(parents=True)
    with zipfile.ZipFile(vsix, "w") as archive:
        archive.writestr("extension/package.json", json.dumps({"version": "1.2.3"}))
        archive.writestr(
            "extension/readme.md",
            "raw.githubusercontent.com/u9401066/asset-aware-mcp/"
            "v1.2.3/resources/banner.png",
        )
        archive.writestr("extension/page_3_drawings.png", b"generated")

    assert check_vsix("1.2.3") == [
        f"{vsix}: contains generated media at extension root: "
        "extension/page_3_drawings.png"
    ]


def test_release_artifact_cli_defaults_to_metadata_and_validates_choices() -> None:
    namespace: dict[str, Any] = runpy.run_path("scripts/audit_release_artifacts.py")
    parse_args = namespace["parse_args"]

    assert parse_args([]).require == "metadata"
    assert parse_args(["--require", "python"]).require == "python"
    assert parse_args(["--require", "vsix"]).require == "vsix"
    assert parse_args(["--require", "all"]).require == "all"
    with pytest.raises(SystemExit):
        parse_args(["--require", "unknown"])


def test_release_artifact_cli_returns_nonzero_when_required_files_are_missing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    namespace: dict[str, Any] = runpy.run_path("scripts/audit_release_artifacts.py")
    main = namespace["main"]
    globals_ = main.__globals__
    globals_["ROOT"] = tmp_path
    globals_["read_project_version"] = lambda: "1.2.3"
    globals_["check_versions"] = list
    globals_["check_links"] = list
    globals_["check_public_doc_versions"] = lambda _version: []

    assert main(["--require", "python"]) == 1
    output = capsys.readouterr().out
    assert "required sdist artifact not found" in output
    assert "required wheel artifact not found" in output


def test_release_script_is_tag_first_and_never_publishes_registries_directly() -> None:
    script = Path("scripts/release.sh").read_text(encoding="utf-8")

    for required_gate in [
        "git status --porcelain=v1 --untracked-files=all",
        'CURRENT_BRANCH" != "main',
        'DEFAULT_BRANCH" != "main',
        "uv lock --check",
        "uvx --from uv==0.12.3 uv audit",
        "--preview-features audit-command --frozen --python-version 3.10",
        "npm --prefix vscode-extension audit --package-lock-only --audit-level=low",
        "audit_release_artifacts.py --require python",
        "audit_release_artifacts.py --require all",
    ]:
        assert required_gate in script

    assert "uv publish" not in script
    assert "vsce publish" not in script
    assert script.index('git tag -a "$RELEASE_TAG"') < script.index(
        'git push origin "refs/tags/$RELEASE_TAG"'
    )
