"""Opt-in Linux font fixture; no global installation or implicit test downloads."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path
from xml.sax.saxutils import escape

import httpx

REVISION = "523d033d6cb47f4a80c58a35753646f5c3608a78"
BASE = f"https://raw.githubusercontent.com/notofonts/noto-cjk/{REVISION}/"
DOWNLOADS = {
    "cjk/NotoSansTC-Regular.otf": (
        "Sans/SubsetOTF/TC/NotoSansTC-Regular.otf",
        "5bab0cb3c1cf89dde07c4a95a4054b195afbcfe784d69d75c340780712237537",
    ),
    "cjk/NotoSansTC-Bold.otf": (
        "Sans/SubsetOTF/TC/NotoSansTC-Bold.otf",
        "55420b259eb119bf5f2a0aadba10cf9d736c12d64ab93e78546d69ef5f43558b",
    ),
    "Noto-LICENSE": (
        "LICENSE",
        "6a73f9541c2de74158c0e7cf6b0a58ef774f5a780bf191f2d7ec9cc53efe2bf2",
    ),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(relative, expected):
    data = bytearray()
    with httpx.stream("GET", BASE + relative, timeout=60) as response:
        response.raise_for_status()
        for chunk in response.iter_bytes():
            data.extend(chunk)
            if len(data) > 8 * 1024 * 1024:
                raise ValueError("Pinned font download exceeds budget")
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("Pinned Noto font/license download differs")
    return bytes(data)


def configuration(root, cjk):
    dirs = [root / "latin"] + ([root / "cjk"] if cjk else [])
    return (
        '<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">'
        "<fontconfig>"
        + "".join(f"<dir>{escape(str(path))}</dir>" for path in dirs)
        + f"<cachedir>{escape(str(root / 'cache'))}</cachedir>"
        + "<alias><family>Arial</family><prefer><family>Liberation Sans</family>"
        "</prefer></alias></fontconfig>"
    )


def setup(root):
    if sys.platform != "linux":
        raise ValueError("This controlled Fontconfig fixture is Linux-only")
    # Resolve before creating output so an unavailable local prerequisite leaves no files.
    latin = {}
    for style in ("Regular", "Bold"):
        path = subprocess.check_output(
            ["fc-match", "-f", "%{file}", f"Liberation Sans:style={style}"],
            text=True,
            encoding="utf-8",
            timeout=15,
        ).strip()
        source = Path(path)
        if source.name != f"LiberationSans-{style}.ttf" or not source.is_file():
            raise ValueError("Install Liberation Sans Regular and Bold first")
        latin[style] = source
    package = (
        "fonts-liberation2"
        if latin["Regular"].parent.name == "liberation2"
        else "fonts-liberation"
    )
    license_path = Path("/usr/share/doc") / package / "copyright"
    if not license_path.is_file():
        raise ValueError("Local Liberation font license is unavailable")
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    try:
        (root / "latin").mkdir()
        (root / "cjk").mkdir()
        for name, (relative, expected) in DOWNLOADS.items():
            (root / name).write_bytes(fetch(relative, expected))
        for style, source in latin.items():
            shutil.copyfile(source, root / "latin" / f"LiberationSans-{style}.ttf")
        shutil.copyfile(license_path, root / "Liberation-LICENSE")
        for enabled, name in ((True, "with-cjk.conf"), (False, "latin-only.conf")):
            (root / name).write_text(configuration(root, enabled), encoding="utf-8")
        files = {
            path.relative_to(root).as_posix(): digest(path)
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }
        manifest = {
            "schema": "docx-font-fixture-v1",
            "upstream_revision": REVISION,
            "files": files,
            "latin_sources": {style: str(path) for style, path in latin.items()},
        }
        (root / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
    except BaseException:
        shutil.rmtree(root)
        raise
    return snapshot(root)


def snapshot(root):
    root = root.resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    expected_names = set(DOWNLOADS) | {
        "Liberation-LICENSE",
        "with-cjk.conf",
        "latin-only.conf",
        "latin/LiberationSans-Regular.ttf",
        "latin/LiberationSans-Bold.ttf",
    }
    if (
        manifest.get("schema") != "docx-font-fixture-v1"
        or set(manifest["files"]) != expected_names
    ):
        raise ValueError("Unexpected font fixture inventory")
    for name, expected in manifest["files"].items():
        path = root / name
        if path.is_symlink() or not path.is_file() or digest(path) != expected:
            raise ValueError("Font fixture bytes changed")
        if name in DOWNLOADS and expected != DOWNLOADS[name][1]:
            raise ValueError("Pinned Noto font identity differs")
    for folder in ("latin", "cjk"):
        cache_id = root / folder / ".uuid"
        if cache_id.exists():
            if cache_id.is_symlink() or cache_id.stat().st_size > 64:
                raise ValueError("Invalid Fontconfig cache identity")
            uuid.UUID(cache_id.read_text(encoding="ascii").strip())
        actual = {
            path.relative_to(root).as_posix()
            for path in (root / folder).iterdir()
            if path.name != ".uuid"
        }
        if (root / folder).is_symlink() or actual != {
            name for name in expected_names if name.startswith(folder + "/")
        }:
            raise ValueError("Unexpected additional font resources")
    for enabled, name in ((True, "with-cjk.conf"), (False, "latin-only.conf")):
        if (root / name).read_text(encoding="utf-8") != configuration(root, enabled):
            raise ValueError("Fontconfig fixture configuration differs")
    return {
        "root": str(root),
        "manifest_sha256": digest(root / "manifest.json"),
        "files": manifest["files"],
    }


@contextmanager
def environment(expected, cjk=True):
    if not expected:
        yield
        return
    root = Path(expected["root"])
    if snapshot(root) != expected:
        raise ValueError("Recorded font environment differs")
    previous = os.environ.get("FONTCONFIG_FILE")
    os.environ["FONTCONFIG_FILE"] = str(
        root / ("with-cjk.conf" if cjk else "latin-only.conf")
    )
    try:
        yield
        if snapshot(root) != expected:
            raise ValueError("Font environment changed during review")
    finally:
        if previous is None:
            os.environ.pop("FONTCONFIG_FILE", None)
        else:
            os.environ["FONTCONFIG_FILE"] = previous


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(setup(args.output), indent=2))


if __name__ == "__main__":
    main()
