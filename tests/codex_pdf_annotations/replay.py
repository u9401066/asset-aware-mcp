"""Replay immutable real-PDF evidence with the installed wheel/container sources."""

import argparse
import hashlib
import json
from pathlib import Path

import src
from tests.codex_pdf_annotations.audit import audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    source = Path(src.__file__).resolve().parent
    expected = json.loads((args.output / "expected.json").read_text())
    fingerprint = hashlib.sha256(
        "\n".join(
            f"src/{p.relative_to(source)}:{hashlib.sha256(p.read_bytes()).hexdigest()}"
            for p in sorted(source.rglob("*.py"))
        ).encode()
    ).hexdigest()
    if fingerprint != expected["server_source_sha256"]:
        raise ValueError("Installed sources differ from actual Codex evaluation")
    result = audit(args.output, save_images=False)
    print(
        json.dumps(
            {**result, "source_path": str(source), "source_sha256": fingerprint},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
