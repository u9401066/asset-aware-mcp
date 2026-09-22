"""Compare structural reference edits with actual Calc UNO insert/delete/rename."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from src.domain.native_ods_references import (
    OPENFORMULA,
    ODSAxisEdit,
    ODSSheetDelete,
    ODSSheetRename,
    rewrite_ods_formula,
)
from src.infrastructure.native_office_process import office_binary

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("NATIVE_ODS_REFERENCE_TEST") != "1",
        reason="Set NATIVE_ODS_REFERENCE_TEST=1 with Calc and OS Python pyuno",
    ),
    pytest.mark.timeout(180),
]


def test_reference_edits_match_independent_calc_structure_operations(tmp_path):
    destination = tmp_path / "calc-oracle"
    command = [
        os.environ.get("NATIVE_ODS_UNO_PYTHON", "/usr/bin/python3"),
        "-B",
        str(Path(__file__).parents[1] / "native_ods_formula_oracle.py"),
        "--calc-bin",
        os.environ.get("NATIVE_ODS_CALC_BIN") or office_binary("Calc"),
        "--output",
        str(destination),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    oracle = json.loads((destination / "oracle.json").read_text())
    assert "LibreOffice" in oracle["renderer"]
    assert len(oracle["cases"]) == 16
    candidates = []
    for case in oracle["cases"]:
        if case["axis"] == "sheet":
            change = (
                ODSSheetRename("Source", "New 中文 O'Brien")
                if case["operation"] == "rename"
                else ODSSheetDelete("Source")
            )
        else:
            change = ODSAxisEdit(
                sheet="Source",
                axis=case["axis"],
                operation=case["operation"],
                index=case["index"],
                count=case["count"],
                row_limit=case["row_limit"],
                column_limit=case["column_limit"],
            )
        assert len(case["before"]) == len(case["after"]) == 19
        formulas = []
        for before in case["before"]:
            actual, events = rewrite_ods_formula(
                before,
                formula_sheet="Observer",
                edit=change,
                namespaces={"of": OPENFORMULA},
            )
            formulas.append(actual)
            rebuilt, end = [], 0
            for event in events:
                assert before[event.start : event.end] == event.before
                rebuilt.extend((before[end : event.start], event.after))
                end = event.end
            assert "".join([*rebuilt, before[end:]]) == actual
        candidates.append(
            {
                "operation": f"{case['axis']}-{case['operation']}-{case['index']}-{case['count']}",
                "before": case["before"],
                "formulas": formulas,
            }
        )
    proposals = tmp_path / "candidates.json"
    proposals.write_text(json.dumps(candidates, ensure_ascii=False), encoding="utf-8")
    reviewed = tmp_path / "calc-reviewed"
    # Calc 24.2 writes whole-axis shorthand where 7.3 writes explicit bounds.
    # Reopen real candidate ODS through the SAME Calc, then require every complete
    # formula to equal the independently edited workbook. Numeric agreement alone
    # or an ad-hoc formula normalizer cannot satisfy this comparison.
    command[-1] = str(reviewed)
    result = subprocess.run(
        [*command, "--candidates", str(proposals)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    review = json.loads((reviewed / "oracle.json").read_text())
    assert review["renderer"] == oracle["renderer"]
    assert len(review["cases"]) == len(candidates)
    raw_differences = []
    for original, proposal, case in zip(
        oracle["cases"], candidates, review["cases"], strict=True
    ):
        assert case["before"] == original["before"]
        assert case["after"] == original["after"]
        assert case["candidate_input"] == proposal["formulas"]
        assert case["control_input"] == case["after"]
        assert case["candidate_output"] == case["control_output"], case
        raw_differences.extend(
            {"operation": proposal["operation"], "candidate": actual, "calc": expected}
            for actual, expected in zip(
                case["candidate_input"], case["after"], strict=True
            )
            if actual != expected
        )
    (reviewed / "raw-spelling-differences.json").write_text(
        json.dumps(raw_differences, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
