"""Tests for the Docling subprocess bridge.

Covers serialisation round-trips, backend-mode detection, and the subprocess
parse path (success / failure / timeout) using mocks — no real docling backend
required, so these run on the base (pre-release) interpreter.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.docling_adapter import (
    DoclingBackendUnavailable,
    DoclingExtractor,
    DoclingParseError,
    _block_from_dict,
    _block_to_dict,
    _deserialize_result_from_dir,
    _serialize_result_to_dir,
)
from src.infrastructure.marker_adapter import MarkerBlock, MarkerParseResult


class TestBlockSerialization:
    def test_round_trip_preserves_all_fields(self) -> None:
        block = MarkerBlock(
            block_id="b1",
            block_type="Figure",
            page=3,
            text="Figure 1: caption",
            bbox=[1.0, 2.0, 3.0, 4.0],
            polygon=[[1.0, 2.0], [3.0, 4.0]],
            section_hierarchy={1: "Introduction"},
            metadata={"docling_label": "picture"},
        )
        restored = _block_from_dict(_block_to_dict(block))
        assert restored.block_id == "b1"
        assert restored.block_type == "Figure"
        assert restored.page == 3
        assert restored.text == "Figure 1: caption"
        assert restored.bbox == [1.0, 2.0, 3.0, 4.0]
        assert restored.polygon == [[1.0, 2.0], [3.0, 4.0]]
        assert restored.section_hierarchy == {1: "Introduction"}
        assert restored.metadata == {"docling_label": "picture"}

    def test_round_trip_nested_children(self) -> None:
        child = MarkerBlock(block_id="c1", block_type="Text", page=1, text="cell")
        parent = MarkerBlock(
            block_id="p1", block_type="Table", page=1, children=[child]
        )
        restored = _block_from_dict(_block_to_dict(parent))
        assert len(restored.children) == 1
        assert restored.children[0].block_id == "c1"
        assert restored.children[0].text == "cell"

    def test_section_hierarchy_int_keys_survive_json(self) -> None:
        block = MarkerBlock(
            block_id="b", block_type="Text", page=1, section_hierarchy={2: "S"}
        )
        restored = _block_from_dict(_block_to_dict(block))
        assert restored.section_hierarchy == {2: "S"}


class TestResultSerialization:
    def test_round_trip_with_images(self, tmp_path: Path) -> None:
        result = MarkerParseResult(
            markdown="# Attention Is All You Need",
            blocks=[MarkerBlock(block_id="b1", block_type="Text", page=1, text="hi")],
            toc=[{"title": "Intro", "page": 1, "level": 1}],
            images={"_page_0_Figure_0.png": b"\x89PNG\r\nDATA"},
            metadata={"backend": "docling"},
            page_count=11,
        )
        _serialize_result_to_dir(result, tmp_path)
        assert (tmp_path / "result.json").exists()

        restored = _deserialize_result_from_dir(tmp_path)
        assert restored.markdown == "# Attention Is All You Need"
        assert restored.page_count == 11
        assert restored.images == {"_page_0_Figure_0.png": b"\x89PNG\r\nDATA"}
        assert len(restored.blocks) == 1
        assert restored.blocks[0].block_id == "b1"
        assert restored.toc == [{"title": "Intro", "page": 1, "level": 1}]
        assert restored.metadata == {"backend": "docling"}

    def test_round_trip_without_images(self, tmp_path: Path) -> None:
        result = MarkerParseResult(
            markdown="x", blocks=[], toc=[], images={}, metadata={}, page_count=0
        )
        _serialize_result_to_dir(result, tmp_path)
        restored = _deserialize_result_from_dir(tmp_path)
        assert restored.images == {}
        assert restored.markdown == "x"

    def test_multiple_images_preserved(self, tmp_path: Path) -> None:
        result = MarkerParseResult(
            markdown="",
            blocks=[],
            toc=[],
            images={"a.png": b"AAA", "b.png": b"BBBB"},
            metadata={},
            page_count=0,
        )
        _serialize_result_to_dir(result, tmp_path)
        restored = _deserialize_result_from_dir(tmp_path)
        assert restored.images == {"a.png": b"AAA", "b.png": b"BBBB"}


class TestVenvPythonCrossPlatform:
    def test_posix_layout(self) -> None:
        venv_dir = Path("/proj/.venv-docling")
        with patch("src.infrastructure.docling_adapter.os.name", "posix"):
            py = DoclingExtractor._venv_python(venv_dir)
        assert py.as_posix().endswith(".venv-docling/bin/python")

    def test_windows_layout(self) -> None:
        venv_dir = Path("/proj/.venv-docling")  # PosixPath on Linux; / keeps type
        with patch("src.infrastructure.docling_adapter.os.name", "nt"):
            py = DoclingExtractor._venv_python(venv_dir)
        assert py.name == "python.exe"
        assert "Scripts" in py.parts


class TestBackendModeDetection:
    def test_env_var_priority(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_py = tmp_path / "python"
        fake_py.write_text("")
        monkeypatch.setenv("DOCLING_PYTHON_PATH", str(fake_py))
        assert DoclingExtractor._docling_python() == str(fake_py)

    def test_subprocess_mode_when_backend_only_isolated(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(sys.modules, "docling", None)  # force import failure
        monkeypatch.setattr(
            DoclingExtractor, "_docling_python", staticmethod(lambda: "/fake/python")
        )
        assert DoclingExtractor._resolve_backend_mode() == "subprocess"

    def test_unavailable_when_no_backend_anywhere(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(sys.modules, "docling", None)
        monkeypatch.setattr(
            DoclingExtractor, "_docling_python", staticmethod(lambda: None)
        )
        with pytest.raises(DoclingBackendUnavailable):
            DoclingExtractor._resolve_backend_mode()

    def test_require_backend_available_accepts_isolated(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(sys.modules, "docling", None)
        monkeypatch.setattr(
            DoclingExtractor, "_docling_python", staticmethod(lambda: "/fake/python")
        )
        DoclingExtractor.require_backend_available()  # should not raise


class TestSubprocessParse:
    def test_success_rebuilds_result(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            DoclingExtractor, "_docling_python", staticmethod(lambda: "/fake/python")
        )

        def fake_run(cmd: list[str], **_kwargs: object) -> MagicMock:
            out_dir = Path(cmd[4])  # [py, -m, module, pdf, out_dir]
            worker_result = MarkerParseResult(
                markdown="mocked markdown",
                blocks=[
                    MarkerBlock(block_id="f1", block_type="Figure", page=2),
                    MarkerBlock(block_id="c1", block_type="Caption", page=2),
                ],
                toc=[{"title": "S", "page": 1, "level": 1}],
                images={"_page_1_Figure_0.png": b"IMG"},
                metadata={"backend": "docling"},
                page_count=7,
            )
            _serialize_result_to_dir(worker_result, out_dir)
            return MagicMock(returncode=0, stderr="")

        with patch("subprocess.run", side_effect=fake_run):
            result = DoclingExtractor().parse(Path("dummy.pdf"))

        assert result.markdown == "mocked markdown"
        assert result.page_count == 7
        assert result.images == {"_page_1_Figure_0.png": b"IMG"}
        assert result.metadata["docling_mode"] == "subprocess"
        assert len([b for b in result.blocks if b.block_type == "Figure"]) == 1
        assert len([b for b in result.blocks if b.block_type == "Caption"]) == 1

    def test_page_map_and_page_count_applied_parent_side(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            DoclingExtractor, "_docling_python", staticmethod(lambda: "/fake/python")
        )

        def fake_run(cmd: list[str], **_kwargs: object) -> MagicMock:
            out_dir = Path(cmd[4])
            worker_result = MarkerParseResult(
                markdown="",
                blocks=[MarkerBlock(block_id="b", block_type="Text", page=1)],
                toc=[],
                images={},
                metadata={},
                page_count=0,
            )
            _serialize_result_to_dir(worker_result, out_dir)
            return MagicMock(returncode=0, stderr="")

        with patch("subprocess.run", side_effect=fake_run):
            result = DoclingExtractor().parse(
                Path("dummy.pdf"), page_map=[42], reported_page_count=99
            )
        assert result.blocks[0].page == 42
        assert result.page_count == 99

    def test_nonzero_exit_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            DoclingExtractor, "_docling_python", staticmethod(lambda: "/fake/python")
        )
        failing = MagicMock(returncode=1, stderr="boom")
        with patch("subprocess.run", return_value=failing):  # noqa: SIM117
            with pytest.raises(DoclingParseError, match="exit 1"):
                DoclingExtractor().parse(Path("dummy.pdf"))

    def test_timeout_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            DoclingExtractor, "_docling_python", staticmethod(lambda: "/fake/python")
        )
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="docling", timeout=1),
        ), pytest.raises(DoclingParseError, match="timed out"):
            DoclingExtractor().parse(Path("dummy.pdf"))
