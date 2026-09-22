"""Replay actual Calc-checked formula candidates against an installed wheel/image."""

import argparse
import hashlib
import json
from pathlib import Path

import src
from src.domain.native_ods_references import (
    OPENFORMULA,
    ODSAxisEdit,
    ODSSheetDelete,
    ODSSheetRename,
    rewrite_ods_formula,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--proof", type=Path, action="append", required=True)
    args = parser.parse_args()
    installed = Path(src.__file__).resolve().parent
    assert "site-packages" in str(installed) or "archive-v0" in str(installed), (
        installed
    )
    sources = {
        str(p.relative_to(installed)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(installed.rglob("*.py"))
    }
    assert sources == json.loads(args.source_manifest.read_text())
    total, renderers = 0, []
    for directory in args.proof:
        proof = json.loads((directory / "proof.json").read_text())
        for name, expected in proof["files"].items():
            assert (
                hashlib.sha256((directory / name).read_bytes()).hexdigest() == expected
            )
        oracle = json.loads((directory / "calc-reviewed/oracle.json").read_text())
        renderers.append(oracle["renderer"])
        assert len(oracle["cases"]) == proof["cases"] == 16
        count = 0
        for case in oracle["cases"]:
            if case["axis"] == "sheet":
                edit = (
                    ODSSheetRename("Source", "New 中文 O'Brien")
                    if case["operation"] == "rename"
                    else ODSSheetDelete("Source")
                )
            else:
                edit = ODSAxisEdit(
                    "Source",
                    case["axis"],
                    case["operation"],
                    case["index"],
                    case["count"],
                    case["row_limit"],
                    case["column_limit"],
                )
            assert case["candidate_output"] == case["control_output"]
            assert case["control_input"] == case["after"]
            assert len(case["before"]) == len(case["candidate_input"]) == 19
            for before, checked_candidate in zip(
                case["before"], case["candidate_input"], strict=True
            ):
                actual, events = rewrite_ods_formula(
                    before,
                    formula_sheet="Observer",
                    edit=edit,
                    namespaces={"of": OPENFORMULA},
                )
                assert actual == checked_candidate
                for event in events:
                    assert before[event.start : event.end] == event.before
                count += 1
        assert count == proof["formulas"] == 304
        total += count
    print(
        json.dumps(
            {
                "installed_source": str(installed),
                "source_files": len(sources),
                "captured_calc_versions": renderers,
                "exact_candidate_replays": total,
                "actual_calc_run_in_artifact": False,
            }
        )
    )


if __name__ == "__main__":
    main()
