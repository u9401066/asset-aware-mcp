"""Changed font environments and false CJK extraction evidence fail review."""

from __future__ import annotations

import hashlib
import json
import os
import uuid

import pytest

from tests.codex_docx_structure import fonts
from tests.codex_docx_structure.renders import check_cjk


@pytest.fixture
def font_fixture(tmp_path, monkeypatch):
    root = tmp_path / "font & fixture"
    (root / "latin").mkdir(parents=True)
    (root / "cjk").mkdir()
    downloads = {}
    for name, (relative, _) in fonts.DOWNLOADS.items():
        data = name.encode()
        (root / name).write_bytes(data)
        downloads[name] = (relative, hashlib.sha256(data).hexdigest())
    monkeypatch.setattr(fonts, "DOWNLOADS", downloads)
    for name in (
        "latin/LiberationSans-Regular.ttf",
        "latin/LiberationSans-Bold.ttf",
        "Liberation-LICENSE",
    ):
        (root / name).write_bytes(name.encode())
    for enabled, name in ((True, "with-cjk.conf"), (False, "latin-only.conf")):
        (root / name).write_text(fonts.configuration(root, enabled), encoding="utf-8")
    files = {
        p.relative_to(root).as_posix(): fonts.digest(p)
        for p in root.rglob("*")
        if p.is_file()
    }
    (root / "manifest.json").write_text(
        json.dumps({"schema": "docx-font-fixture-v1", "files": files}), encoding="utf-8"
    )
    return root


@pytest.mark.parametrize("fault", [None, "font", "config", "extra", "manifest", "uuid"])
def test_font_environment_identity_and_restoration(font_fixture, monkeypatch, fault):
    root = font_fixture
    expected = fonts.snapshot(root)
    monkeypatch.setenv("FONTCONFIG_FILE", "original.conf")
    for folder in ("latin", "cjk"):
        (root / folder / ".uuid").write_text(str(uuid.uuid4()), encoding="ascii")
    assert fonts.snapshot(root) == expected  # Fontconfig 2.13 creates cache UUIDs.
    changes = {
        "font": "cjk/NotoSansTC-Bold.otf",
        "config": "with-cjk.conf",
        "extra": "latin/extra.ttf",
        "manifest": "manifest.json",
        "uuid": "cjk/.uuid",
    }
    if fault:
        path = root / changes[fault]
        if fault == "manifest":
            path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        else:
            path.write_bytes(b"modified")
        with pytest.raises(ValueError), fonts.environment(expected):
            pytest.fail("Changed font environment was accepted")
    else:
        with (
            pytest.raises(RuntimeError, match="interrupt"),
            fonts.environment(expected),
        ):
            assert os.environ["FONTCONFIG_FILE"] == str(root / "with-cjk.conf")
            raise RuntimeError("interrupt")
    assert os.environ["FONTCONFIG_FILE"] == "original.conf"


def test_mutation_during_review_is_detected(font_fixture, monkeypatch):
    monkeypatch.delenv("FONTCONFIG_FILE", raising=False)
    expected = fonts.snapshot(font_fixture)
    with pytest.raises(ValueError, match="changed"), fonts.environment(expected):
        (font_fixture / "latin/LiberationSans-Regular.ttf").write_bytes(b"changed")
    assert "FONTCONFIG_FILE" not in os.environ


@pytest.mark.parametrize("fault", [None, "text", "font", "glyph"])
def test_chinese_glyph_check_does_not_accept_nonzero_id_alone(fault):
    class Page:
        number = 0

        def get_texttrace(self):
            # Writer may paint the Latin space before the Chinese run.
            chars = [
                (ord("研"), 1),
                (ord("研" if fault == "text" else "究"), 1 if fault == "glyph" else 2),
            ]
            return [
                {"font": "LiberationSans", "chars": [(32, 1)]},
                {
                    "font": "LiberationSans" if fault == "font" else "NotoSansTC-Bold",
                    "chars": chars,
                },
            ]

    if fault:
        with pytest.raises(ValueError):
            check_cjk(Page())
    else:
        check_cjk(Page())
