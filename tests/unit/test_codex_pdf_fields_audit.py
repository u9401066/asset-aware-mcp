"""Reject incomplete field reads, premature edits and independently corrupted PDFs."""

import copy
import io
import json
import subprocess
import sys
from pathlib import Path

import pikepdf
import pytest

from tests.codex_native_pdf.trace import canonical, digest
from tests.codex_pdf_fields import VALUE
from tests.codex_pdf_fields_audit import (
    REQUIRED,
    calls_from,
    collect_page,
    require_ready,
    validate_selection,
)
from tests.codex_pdf_fields_checks import check_states, preserve_body
from tests.native_pdf_helpers import rewrite
from tests.unit.test_native_pdf_field_edits import apply, create, delete, update


def test_audit_cli_rejects_missing_trace_with_failure_exit(tmp_path):
    result = subprocess.run(
        [sys.executable, "-B", "-m", "tests.codex_pdf_fields_audit", str(tmp_path)],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 1, result.stderr
    report = json.loads(result.stdout)
    assert report["passed"] is False
    assert "FileNotFoundError" in report["error"]
    assert json.loads((tmp_path / "audit.json").read_text()) == report


def small_form():
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page(page_size=(120, 120))
        page.obj.Contents = pdf.make_stream(b"q .75 .75 .75 rg 0 40 120 20 re f Q")
        page.obj.Annots = pikepdf.Array()
        fields = pikepdf.Array()
        font = pdf.make_indirect(
            pikepdf.Dictionary(
                Type=pikepdf.Name.Font,
                Subtype=pikepdf.Name.Type1,
                BaseFont=pikepdf.Name.Helvetica,
            )
        )
        pdf.Root.AcroForm = pikepdf.Dictionary(
            Fields=fields,
            DA=pikepdf.String("/Helv 8 Tf 0 g"),
            DR=pikepdf.Dictionary(Font=pikepdf.Dictionary(Helv=font)),
        )

        def appearance(color):
            obj = pdf.make_stream(f"q {color} g 0 0 20 20 re f Q".encode())
            obj.Type = pikepdf.Name.XObject
            obj.Subtype = pikepdf.Name.Form
            obj.BBox = pikepdf.Array([0, 0, 20, 20])
            obj.Resources = pikepdf.Dictionary()
            return obj

        def widget(rect, on=None):
            obj = pdf.make_indirect(
                pikepdf.Dictionary(
                    Type=pikepdf.Name.Annot,
                    Subtype=pikepdf.Name.Widget,
                    Rect=pikepdf.Array(rect),
                    F=4,
                    P=page.obj,
                )
            )
            if on:
                obj.AP = pikepdf.Dictionary(
                    N=pikepdf.Dictionary({"/Off": appearance(1), on: appearance(0)})
                )
                obj.AS = pikepdf.Name.Off
            page.obj.Annots.append(obj)
            return obj

        for name, kind, rect in [
            ("Text1", "/Tx", [0, 40, 120, 60]),
            ("Button2", "/Btn", [0, 0, 20, 20]),
            ("Check Box3", "/Btn", [25, 0, 45, 20]),
        ]:
            obj = widget(rect, "/Yes" if name == "Check Box3" else None)
            obj.T, obj.FT = pikepdf.String(name), pikepdf.Name(kind)
            if name == "Button2":
                obj.Ff = 65536
                obj.AP = pikepdf.Dictionary(N=appearance(0.5))
            fields.append(obj)
        radio = pdf.make_indirect(
            pikepdf.Dictionary(
                T=pikepdf.String("Group4"), FT=pikepdf.Name.Btn, Ff=49152
            )
        )
        kids = [
            widget([50 + i * 25, 0, 70 + i * 25, 20], f"/Choice{i + 1}")
            for i in range(2)
        ]
        for child in kids:
            child.Parent = radio
        radio.Kids = pikepdf.Array(kids)
        fields.append(radio)
        output = io.BytesIO()
        pdf.save(output)
        return output.getvalue()


def stages():
    source = small_form()
    changed, _ = apply(
        source,
        [
            update(
                source,
                "Text1",
                {"kind": "text", "text": VALUE},
                style={"font_size": 8, "border_width": 0},
            ),
            update(source, "Check Box3", {"kind": "button", "state": "/Yes"}),
            update(source, "Group4", {"kind": "button", "state": "/Choice2"}),
        ],
    )
    edit = create(changed, name="ReviewCopy", value={"kind": "text", "text": VALUE})
    edit["field"]["widgets"][0].update(
        rect=[0.1, 0.1, 0.9, 0.25], style={"font_size": 8, "border_width": 0}
    )
    added, _ = apply(changed, [edit])
    removed, _ = apply(added, [delete(added, "Text1")])
    return [source, changed, added, removed]


def test_native_case_audit_rejects_wrong_values_and_preserves_original_appearances():
    data = stages()
    check_states(data)
    corrupted = rewrite(
        data[-1],
        lambda p: setattr(
            p.Root.AcroForm.Fields[-1], "V", pikepdf.String("中文 008 µg")
        ),
    )
    with pytest.raises(ValueError, match="Final native field values"):
        check_states([*data[:-1], corrupted])


@pytest.mark.parametrize("fault", ["body", "pushbutton", "button_appearance"])
def test_independent_checks_reject_unrequested_native_drift(fault):
    source, changed, *_ = stages()

    def tamper(pdf):
        if fault == "body":
            pdf.pages[0].obj.Contents.write(b"q 0 g 0 0 120 120 re f Q")
        elif fault == "pushbutton":
            pdf.Root.AcroForm.Fields[1].TU = pikepdf.String("changed")
        else:
            pdf.Root.AcroForm.Fields[2].AP.N.Yes.write(b"q .5 g 0 0 20 20 re f Q")

    with pytest.raises(ValueError, match=r"Body streams|pushbutton|button appearance"):
        preserve_body(source, rewrite(changed, tamper))


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "pin_missing",
        "pin_wrong",
        "offset",
        "missing_first",
        "digest",
        "asset",
        "locator",
        "length",
        "continuation",
    ],
)
def test_field_read_audit_requires_complete_identity_bound_pinned_chunks(fault):
    value = {"field": "中文 007 µg"}
    text = canonical(value).decode()
    request = {
        "op": "read_pdf_field",
        "asset_id": "a",
        "revision": "b",
        "pdf_field_locator": {"field_path": [0]},
    }
    sha = digest(text.encode())
    first = {
        "text_excerpt": text[:8],
        "text_sha256": sha,
        "excerpt_char_range": [0, 8],
        "next_text_offset": 8,
        "text_length": len(text),
    }
    buffers = {}
    assert collect_page(buffers, request, first) is None
    last = {
        **first,
        "text_excerpt": text[8:],
        "excerpt_char_range": [8, len(text)],
        "next_text_offset": None,
    }
    args = {**copy.deepcopy(request), "text_offset": 8, "pdf_field_text_sha256": sha}
    if fault == "pin_missing":
        del args["pdf_field_text_sha256"]
    elif fault == "pin_wrong":
        args["pdf_field_text_sha256"] = "f" * 64
    elif fault == "offset":
        args["text_offset"] = 9
    elif fault == "missing_first":
        buffers.clear()
    elif fault == "digest":
        last["text_excerpt"] = last["text_excerpt"].replace("007", "008")
    elif fault == "asset":
        args["asset_id"] = "other"
    elif fault == "locator":
        args["pdf_field_locator"]["field_path"] = [1]
    elif fault == "length":
        last["text_length"] += 1
    elif fault == "continuation":
        last["next_text_offset"] = len(text) + 1
    if fault:
        with pytest.raises(ValueError):
            collect_page(buffers, args, last)
    else:
        assert collect_page(buffers, args, last) == value and not buffers


def test_mutation_readiness_checks_duplicate_physical_records_not_names():
    catalog = {
        "r": {
            "fields": [
                {"locator": {"field_path": [i]}, "qualified_name": "duplicate"}
                for i in range(2)
            ]
        }
    }
    record = {"locator": {"field_path": [0]}, "evidence": {"revision": "r"}}
    args = (
        "r",
        catalog,
        {"r"},
        {"one": record},
        {("r", 0)},
        {"update_pdf_fields"},
        {"update_pdf_fields"},
    )
    with pytest.raises(ValueError, match="every complete field"):
        require_ready(*args)
    args[3]["two"] = {"locator": {"field_path": [1]}, "evidence": {"revision": "r"}}
    require_ready(*args)
    with pytest.raises(ValueError, match="actual page"):
        require_ready(*args[:4], set(), *args[5:])


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("fault", [None, "parent", "value", "context", "override"])
def test_selection_audit_checks_initial_and_historical_full_content(existing, fault):
    from src.domain.native_pdf_fields import PdfFieldReference
    from src.domain.native_selection import NativeSelectionSelector, selection_record

    parent = PdfFieldReference(
        asset_id="file_" + "a" * 32,
        revision="b" * 64,
        locator={"field_path": [0], "object_id": 1, "generation": 0},
        value_sha256="c" * 64,
    )
    representation = {"inherited_entries": {"/V": {"text": VALUE}}}
    selector = NativeSelectionSelector(pointer="/inherited_entries/~1V/text")
    record = selection_record(parent, selector, representation)
    evidence = copy.deepcopy(record["evidence"])
    args = {"reference": copy.deepcopy(evidence if existing else parent.model_dump())}
    if not existing:
        args["selection"] = {"pointer": selector.pointer}
    result = {
        "asset_id": parent.asset_id,
        "inspected_revision": parent.revision,
        "evidence": evidence,
    }
    records = {canonical(parent.model_dump()): representation}
    if fault == "parent":
        records.clear()
    elif fault == "value":
        record["value"] = "中文 008 µg"
    elif fault == "context":
        record["text_context"]["utf8_byte_range"][-1] -= 1
    elif fault == "override":
        args["selection"] = {"pointer": "/different"}
    if fault:
        with pytest.raises(ValueError):
            validate_selection(args, result, record, records)
    else:
        assert validate_selection(args, result, record, records) == evidence


def test_listing_is_optional_when_full_widget_record_supplies_the_page_locator():
    events = [{"type": "turn.completed"}]
    for op in REQUIRED:
        events.append(
            {
                "type": "item.completed",
                "item": {
                    "type": "mcp_tool_call",
                    "status": "completed",
                    "server": "asset_aware_under_test",
                    "tool": "document",
                    "arguments": {"op": "native", "native_request": {"op": op}},
                    "result": {
                        "content": [{"type": "text", "text": '{"success":true}'}]
                    },
                },
            }
        )
    assert "read_pdf" not in REQUIRED
    assert len(calls_from(events)) == len(REQUIRED)


def test_prose_or_shell_cannot_substitute_for_actual_field_workflow():
    with pytest.raises(ValueError, match="Missing field workflow"):
        calls_from(
            [
                {"type": "turn.completed"},
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": "All passed"},
                },
            ]
        )
    with pytest.raises(ValueError, match="Non-MCP"):
        calls_from(
            [
                {"type": "turn.completed"},
                {"type": "item.completed", "item": {"type": "command_execution"}},
            ]
        )
