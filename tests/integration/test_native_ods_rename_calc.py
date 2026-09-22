"""Native package transaction compared with independent Calc edits and rendering."""

import hashlib
import json
import os
import subprocess
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pymupdf
import pytest

from src.domain.native_ods import NativeODSTableRename
from src.infrastructure.native_ods import NativeODSFileAdapter
from src.infrastructure.native_ods_render_source import rendering_source
from src.infrastructure.native_office_process import office_binary

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("NATIVE_ODS_REFERENCE_TEST") != "1",
        reason="Set NATIVE_ODS_REFERENCE_TEST=1 with Calc and matching pyuno Python",
    ),
    pytest.mark.timeout(180),
]


def oracle(output, *options):
    result = subprocess.run(
        [
            os.environ.get("NATIVE_ODS_UNO_PYTHON", "/usr/bin/python3"),
            "-B",
            str(Path(__file__).parents[1] / "native_ods_rename_oracle.py"),
            "--calc-bin",
            os.environ.get("NATIVE_ODS_CALC_BIN") or office_binary("Calc"),
            "--output",
            str(output),
            *map(str, options),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads((output / "oracle.json").read_text())


def native_records(path):
    """Independent XML inventory, deliberately not using production owner lists."""
    references, cells = [], []
    with zipfile.ZipFile(path) as archive:
        for part in archive.namelist():
            if not part.endswith(".xml") or part.startswith("META-INF/"):
                continue
            root = ET.fromstring(archive.read(part))  # noqa: S314 - generated fixture
            for node in root.iter():
                local = node.tag.split("}")[-1]
                for key, value in node.attrib.items():
                    suffix = key.split("}")[-1]
                    if (
                        any(
                            t in suffix
                            for t in (
                                "address",
                                "formula",
                                "expression",
                                "condition",
                                "print-ranges",
                                "notify-on-update",
                            )
                        )
                        or (local == "condition" and suffix == "value")
                        or (
                            local in {"table", "config-item-map-entry"}
                            and suffix == "name"
                        )
                    ):
                        references.append((part, node.tag, key, value))
                if (
                    local in {"desc", "config-item"}
                    and node.text
                    and (local == "desc" or "中文" in node.text)
                ):
                    references.append((part, node.tag, None, node.text))
                if local == "table-cell" and any(
                    k.endswith("}value-type") for k in node.attrib
                ):
                    attrs = sorted(
                        (k, v)
                        for k, v in node.attrib.items()
                        if k.split("}")[-1]
                        in {
                            "formula",
                            "value-type",
                            "value",
                            "string-value",
                            "boolean-value",
                            "date-value",
                            "time-value",
                            "currency",
                        }
                    )
                    content = (
                        ET.tostring(node, encoding="unicode")
                        .split(">", 1)[1]
                        .rsplit("</", 1)[0]
                    )
                    cells.append((part, attrs, content))
    return sorted(references, key=repr), cells


def compare_reimport(output):
    candidate, control = (
        native_records(output / "candidate.ods"),
        native_records(output / "control.ods"),
    )
    assert candidate[0] == control[0]
    assert candidate[1] == control[1]
    pages = []
    with (
        pymupdf.open(output / "candidate.pdf") as left,
        pymupdf.open(output / "control.pdf") as right,
    ):
        assert len(left) == len(right) == 2
        for index, (a, b) in enumerate(zip(left, right, strict=True)):
            actual = a.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
            expected = b.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
            assert (actual.width, actual.height, actual.samples) == (
                expected.width,
                expected.height,
                expected.samples,
            )
            assert a.get_text() == b.get_text()
            actual.save(output / f"candidate-page-{index}.png")
            expected.save(output / f"control-page-{index}.png")
            pages.append(
                {
                    "index": index,
                    "pixels_sha256": hashlib.sha256(actual.samples).hexdigest(),
                    "text": a.get_text(),
                }
            )
    report = {
        "reference_records_exact": len(candidate[0]),
        "typed_cells_exact": len(candidate[1]),
        "pages": pages,
        "semantic_and_visual_quality": "requires_agent_review; equality_to_control_is_not_correctness",
    }
    (output / "comparison.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    return report


def test_rename_transaction_reopens_like_independent_calc_with_chart_and_named_ranges(
    tmp_path,
):
    generated, reviewed = tmp_path / "generated", tmp_path / "reviewed"
    before = oracle(generated)
    source = generated / "source.ods"
    data, mtime = source.read_bytes(), source.stat().st_mtime_ns
    adapter = NativeODSFileAdapter()
    dependencies = adapter.dependencies(data)
    assert len(rendering_source(data)) == 2
    candidate, receipt = adapter.rename_table(
        data,
        NativeODSTableRename(
            table_index=0,
            table_name="Source",
            new_name="New 中文 O'Brien",
            dependencies_sha256=dependencies["inventory_sha256"],
        ),
    )
    assert receipt.changed_parts == [
        "ChartEvidence/content.xml",
        "content.xml",
        "settings.xml",
    ]
    assert (
        len(
            [
                c
                for c in receipt.changes
                if c["operation"] == "map_native_ods_dependency"
            ]
        )
        >= 20
    )
    assert receipt.repairs == ["invalidated_typed_formula_caches"]
    path = tmp_path / "candidate.ods"
    path.write_bytes(candidate)
    assert len(rendering_source(candidate)) == 2
    after = oracle(
        reviewed, "--candidate", path, "--control", generated / "control.ods"
    )
    assert before["renderer"] == after["renderer"]
    report = compare_reimport(reviewed)
    assert report["reference_records_exact"] >= 31 and report["typed_cells_exact"] == 19
    assert (
        "#REF!" in report["pages"][1]["text"]
    )  # Literal INDIRECT is intentionally unchanged.
    assert (source.read_bytes(), source.stat().st_mtime_ns) == (data, mtime)
