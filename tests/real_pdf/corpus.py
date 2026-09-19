"""Explicit, bounded retrieval of hash-pinned public source PDFs."""

import argparse
import hashlib
import json
from pathlib import Path

import httpx
import pymupdf

MAX_SOURCE_BYTES = 32 * 1024 * 1024


def cases():
    return json.loads(Path(__file__).with_name("corpus.json").read_text())["cases"]


def check_source(path, case):
    if path.stat().st_size != case["size_bytes"]:
        raise ValueError("Corpus source size differs from pinned original")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != case["sha256"]:
        raise ValueError("Corpus source SHA-256 differs from pinned original")
    with pymupdf.open(path) as pdf:
        if len(pdf) != case["page_count"]:
            raise ValueError("Corpus source page count differs")
        for page in case["pages"]:
            p = pdf[page["index"]]
            if not p.get_text().strip():
                raise ValueError("Expected digital/OCR text layer is missing")
            if case["kind"] == "scan_with_ocr" and not p.get_images():
                raise ValueError("Expected original scan image is missing")
    return data


def fetch(directory, case):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / case["filename"]
    if path.exists():
        check_source(path, case)
        return path
    # Some government endpoints reject urllib's default User-Agent.
    with httpx.stream(
        "GET",
        case["url"],
        follow_redirects=True,
        timeout=60,
        headers={"User-Agent": "Mozilla/5.0 Asset-Aware-MCP-corpus/1.4"},
    ) as response:
        response.raise_for_status()
        data = bytearray()
        for chunk in response.iter_bytes():
            data.extend(chunk)
            if len(data) > min(MAX_SOURCE_BYTES, case["size_bytes"]):
                raise ValueError("Corpus download exceeds pinned byte limit")
    if (
        len(data) != case["size_bytes"]
        or hashlib.sha256(data).hexdigest() != case["sha256"]
    ):
        raise ValueError("Corpus download identity changed; review a new manifest")
    with path.open("xb") as target:
        target.write(data)
    check_source(path, case)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument(
        "--fetch", action="store_true", help="Explicitly allow downloads"
    )
    args = parser.parse_args()
    for case in cases():
        path = (
            fetch(args.directory, case)
            if args.fetch
            else args.directory / case["filename"]
        )
        check_source(path, case)
        print(
            json.dumps(
                {"case": case["id"], "path": str(path), "sha256": case["sha256"]}
            )
        )


if __name__ == "__main__":
    main()
