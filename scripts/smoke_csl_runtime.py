"""Check installed CSL resources and optional Node processing outside the checkout."""

import argparse
import hashlib
import json
from pathlib import Path

import src
from src.domain.csl_citations import CslDocument
from src.infrastructure.csl_processor import NodeCslProcessor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-unconfigured", action="store_true")
    args = parser.parse_args()
    processor = NodeCslProcessor()
    capability = processor.capabilities()
    source = Path(src.__file__).parent
    source_sha = hashlib.sha256(
        "\n".join(
            f"src/{path.relative_to(source).as_posix()}:{hashlib.sha256(path.read_bytes()).hexdigest()}"
            for path in sorted(source.rglob("*.py"))
        ).encode()
    ).hexdigest()
    document = CslDocument.model_validate(
        {
            "style": "apa",
            "items": [
                {
                    "id": key,
                    "type": "book",
                    "title": title,
                    "author": [{"family": "Doe", "given": "Jane"}],
                    "issued": {"date-parts": [[2020]]},
                    "publisher": "Example Press",
                }
                for key, title in (("a", "Alpha"), ("b", "Beta"))
            ],
            "clusters": [{"id": key, "cites": [{"id": key}]} for key in ("b", "a")],
        }
    )
    result = {
        "source_path": str(source),
        "source_sha256": source_sha,
        "capability": capability,
    }
    if capability["configured"]:
        rendered = processor.render(document)
        assert rendered["text"]["citations"] == ["(Doe, 2020b)", "(Doe, 2020a)"]
        assert rendered["text"]["entry_ids"] == [["a"], ["b"]]
        result["resources"] = rendered["resources"]
        result["rendered"] = True
    else:
        assert args.allow_unconfigured, "Node.js is required for this CSL smoke"
        try:
            processor.render(document)
        except ValueError as exc:
            assert "Node.js" in str(exc)
        else:
            raise AssertionError("Missing Node must fail explicitly")
        result["rendered"] = False
    result["passed"] = True
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
