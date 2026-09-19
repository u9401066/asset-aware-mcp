"""Pagination corrections retain all native content and explicit source meaning."""

from __future__ import annotations

from copy import deepcopy

import pytest
from lxml import etree

from src.infrastructure.native_docx_grid import read_table
from src.infrastructure.native_docx_grid_model import W
from src.infrastructure.native_docx_structure import canonical
from src.infrastructure.native_docx_workspace import MAIN_PART, checked_docx
from tests.unit.test_native_docx_grid import CHAIN, request, run, source, transform


def test_auto_height_and_keep_row_together_preserve_every_cell_and_other_part():
    data = source()
    before = checked_docx(data)
    cells = [canonical(c) for c in before.xml(MAIN_PART).iter(W + "tc")]
    updated, receipt = run(
        data,
        {
            "op": "set_row_layout",
            "index": 1,
            "count": 2,
            "height": {"rule": "auto"},
            "split": "prevent",
        },
    )
    after = checked_docx(updated)
    assert [canonical(c) for c in after.xml(MAIN_PART).iter(W + "tc")] == cells
    assert all(after.parts[n] == b for n, b in before.parts.items() if n != MAIN_PART)
    record = read_table(updated, CHAIN)
    assert record["row_layout"][1]["split"] == "prevent"
    assert record["row_layout"][2]["heights"] == [{"value_twips": 0, "rule": "auto"}]
    change = receipt.changes[0]["edits"][0]
    assert change["before"][0]["split"] == "inherit"
    assert change["after"][0]["split"] == "prevent"
    assert (
        run(
            updated,
            {
                "op": "set_row_layout",
                "index": 1,
                "count": 2,
                "height": {"rule": "auto"},
                "split": "prevent",
            },
        )[0]
        == updated
    )


def test_repeated_header_prefix_cannot_cut_an_existing_vertical_merge():
    data = source()
    with pytest.raises(ValueError, match=r"[Hh]eader"):
        run(data, {"op": "set_header_rows", "count": 2})
    updated, _ = run(data, {"op": "set_header_rows", "count": 3})
    record = read_table(updated, CHAIN)
    assert record["repeat_header_rows"] == [0, 1, 2]
    assert record["repeat_header_prefix_length"] == 3
    cleared, _ = run(updated, {"op": "set_header_rows", "count": 0})
    assert read_table(cleared, CHAIN)["repeat_header_rows"] == []
    assert run(cleared, {"op": "set_header_rows", "count": 0})[0] == cleared


@pytest.mark.parametrize(
    "rule,size", [("at_least", 360), ("exact", 420), ("auto", None), ("inherit", None)]
)
def test_height_rules_and_explicit_inheritance(rule, size):
    data = source()
    height = {"rule": rule}
    if size is not None:
        height["value_twips"] = size
    updated, _ = run(
        data,
        {
            "op": "set_row_layout",
            "index": 0,
            "count": 1,
            "height": height,
            "split": "allow",
        },
    )
    record = read_table(updated, CHAIN)["row_layout"][0]
    assert record["split"] == "allow"
    assert record["heights"] == (
        []
        if rule == "inherit"
        else [
            {
                "value_twips": size or 0,
                "rule": "atLeast" if rule == "at_least" else rule,
            }
        ]
    )
    inherited, _ = run(
        updated, {"op": "set_row_layout", "index": 0, "count": 1, "split": "inherit"}
    )
    assert read_table(inherited, CHAIN)["row_layout"][0]["split"] == "inherit"


@pytest.mark.parametrize(
    "edit",
    [
        {"op": "set_row_layout", "index": 0, "count": 1},
        {"op": "set_row_layout", "index": 0, "count": 1, "height": {"rule": "exact"}},
        {
            "op": "set_row_layout",
            "index": 0,
            "count": 1,
            "height": {"rule": "auto", "value_twips": 30},
        },
        {"op": "set_header_rows", "count": True},
    ],
)
def test_invalid_layout_requests_have_no_implied_mutation(edit):
    with pytest.raises(ValueError):
        request(source(), edit)


def test_pure_layout_preserves_fields_but_rejects_tracked_row_properties():
    def add_field(table):
        paragraph = table.find(".//" + W + "p")
        field = etree.SubElement(paragraph, W + "fldSimple", {W + "instr": "PAGE"})
        etree.SubElement(etree.SubElement(field, W + "r"), W + "t").text = "1"

    data = transform(source(), add_field)
    updated, _ = run(
        data, {"op": "set_row_layout", "index": 0, "count": 1, "split": "prevent"}
    )
    assert (
        checked_docx(updated).xml(MAIN_PART).find(".//" + W + "fldSimple") is not None
    )

    def tracked(table):
        pr = table.find(W + "tr/" + W + "trPr")
        etree.SubElement(pr, W + "trPrChange", {W + "id": "1"}).append(deepcopy(pr))

    data = transform(source(), tracked)
    with pytest.raises(ValueError, match="tracked"):
        run(data, {"op": "set_row_layout", "index": 0, "count": 1, "split": "prevent"})


def test_noncontiguous_header_flags_are_not_reported_as_repeating_prefix():
    data, _ = run(source(), {"op": "set_header_rows", "count": 0})

    def late_headers(table):
        for row in table.findall(W + "tr")[1:]:
            etree.SubElement(row.find(W + "trPr"), W + "tblHeader")

    data = transform(data, late_headers)
    record = read_table(data, CHAIN)
    assert record["repeat_header_rows"] == [1, 2]
    assert record["repeat_header_prefix_length"] == 0
    updated, _ = run(data, {"op": "set_header_rows", "count": 3})
    assert read_table(updated, CHAIN)["repeat_header_prefix_length"] == 3


def test_multiple_heights_are_explicitly_coalesced_and_others_survive():
    def duplicate(table):
        pr = table.find(W + "tr/" + W + "trPr")
        etree.SubElement(pr, W + "trHeight", {W + "val": "240", W + "hRule": "exact"})
        etree.SubElement(pr, W + "hidden", {W + "val": "0"})

    data = transform(source(), duplicate)
    assert len(read_table(data, CHAIN)["row_layout"][0]["heights"]) == 2
    updated, receipt = run(
        data,
        {"op": "set_row_layout", "index": 0, "count": 1, "height": {"rule": "auto"}},
    )
    assert len(receipt.changes[0]["edits"][0]["before"][0]["heights"]) == 2
    assert len(read_table(updated, CHAIN)["row_layout"][0]["heights"]) == 1
    assert (
        checked_docx(updated).xml(MAIN_PART).find(".//" + W + "hidden").get(W + "val")
        == "0"
    )


def test_layout_check_rejects_accidental_native_content_change(monkeypatch):
    from src.infrastructure import native_docx_table_layout as module

    original = module._set

    def corrupt(row, name, attrs):
        original(row, name, attrs)
        row.find(".//" + W + "t").text = "corrupted"

    monkeypatch.setattr(module, "_set", corrupt)
    with pytest.raises(ValueError, match="unrelated properties"):
        run(
            source(),
            {"op": "set_row_layout", "index": 0, "count": 1, "split": "prevent"},
        )


@pytest.mark.parametrize(
    "edit",
    [
        {"op": "set_header_rows", "count": 4},
        {"op": "set_row_layout", "index": 2, "count": 2, "split": "allow"},
    ],
)
def test_layout_bounds_are_checked_against_intermediate_grid(edit):
    with pytest.raises(ValueError, match="exceeds"):
        run(source(), edit)


def test_unknown_direct_split_is_exposed_without_inventing_a_layout_verdict():
    def unknown(table):
        etree.SubElement(
            table.find(W + "tr/" + W + "trPr"), W + "cantSplit", {W + "val": "unknown"}
        )

    data = transform(source(), unknown)
    state = read_table(data, CHAIN)["row_layout"][0]
    assert state["split"] == "unknown" and state["split_raw_value"] == "unknown"
    updated, _ = run(
        data, {"op": "set_row_layout", "index": 0, "count": 1, "split": "prevent"}
    )
    assert read_table(updated, CHAIN)["row_layout"][0]["split"] == "prevent"


@pytest.mark.parametrize(
    "edit",
    [
        {"op": "set_header_rows", "count": 0},
        {"op": "set_row_layout", "index": 0, "count": 1, "split": "prevent"},
        {"op": "set_row_layout", "index": 0, "count": 1, "height": {"rule": "auto"}},
    ],
)
def test_requested_property_is_checked_against_actual_readback(monkeypatch, edit):
    from src.infrastructure import native_docx_table_layout as module

    monkeypatch.setattr(module, "_set", lambda *args: None)
    with pytest.raises(ValueError, match="readback"):
        run(source(), edit)
