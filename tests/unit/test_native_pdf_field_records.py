"""Field evidence must not lose duplicate identities, radio groups or page views."""

from __future__ import annotations

import hashlib
import io

import pikepdf
import pytest

from src.domain.native_pdf_fields import PdfFieldLocator, PdfFieldReference
from src.infrastructure.native_pdf_fields import (
    FieldCatalog,
    inspect_fields,
    read_field,
)
from src.infrastructure.native_pdf_graph import PdfObjectGraph, canonical, graph_digest
from src.infrastructure.native_pdf_package import NativePdfPackage
from tests.native_pdf_field_helpers import form_pdf
from tests.native_pdf_helpers import build_pdf, pixels, rewrite


def records(data):
    with NativePdfPackage(data) as package:
        catalog = FieldCatalog(package)
        return [catalog.record(node.locator) for node in catalog.tree.nodes.values()]


def named(data, name):
    return next(r for r in records(data) if r["qualified_name"] == name)


def test_duplicate_names_are_distinct_source_objects_and_readback_targets():
    source = form_pdf()
    catalog = inspect_fields(source)
    assert catalog["field_count"] == 7
    assert catalog["terminal_field_count"] == 6
    assert catalog["page_widget_occurrence_count"] == 7
    duplicate = [r for r in records(source) if r["qualified_name"] == "duplicate"]
    assert len(duplicate) == 2
    assert duplicate[0]["locator"] != duplicate[1]["locator"]
    assert [r["inherited_entries"]["/V"]["text"] for r in duplicate] == [
        "第一筆 007 µg",
        "second 0008",
    ]
    for record in duplicate:
        locator = PdfFieldLocator.model_validate(record["locator"])
        assert read_field(source, locator) == record
        with pytest.raises(ValueError, match="locator"):
            read_field(source, locator.model_copy(update={"object_id": 999999}))
    assert not catalog["orphan_page_widgets"]


def test_radio_widgets_belong_to_one_logical_field_on_both_pages():
    radio = named(form_pdf(), "radio")
    assert radio["kind"] == "terminal"
    assert radio["child_fields"] == []
    assert [w["tree_path"] for w in radio["widgets"]] == [[3, 0], [3, 1]]
    assert [w["normal_appearance_states"] for w in radio["widgets"]] == [
        ["/First", "/Off"],
        ["/Off", "/Second"],
    ]
    assert [
        w["page_occurrences"][0]["locator"]["page"]["page_index"]
        for w in radio["widgets"]
    ] == [0, 1]
    assert all(not w["issues"] for w in radio["widgets"])
    assert all(w["parent_link"]["field_paths"] == [[3]] for w in radio["widgets"])


def test_nonvisual_field_retains_inheritance_origins_without_inheriting_actions():
    hidden = named(form_pdf(), "person.hidden")
    assert hidden["widgets"] == []
    assert hidden["field_type"] == "/Tx"
    assert hidden["inherited_entries"]["/V"]["text"] == "007"
    assert hidden["inherited_entries"]["/Ff"]["value"] == 2
    assert hidden["inherited_entries"]["/DA"]["source"]["field"]["field_path"] == [2]
    assert hidden["inherited_entries"]["/MaxLen"]["value"] == 40
    assert "/AA" not in hidden["inherited_entries"]
    assert "/AA" in str(hidden["ancestor_fields"][0]["native_graph"])
    assert hidden["parent_link"]["field_paths"] == [[2]]


def test_form_defaults_and_multiselect_indices_are_not_simplified():
    source = form_pdf()
    choice = named(source, "choice")
    assert choice["inherited_entries"]["/DA"]["source"] == {"acroform": True}
    assert choice["inherited_entries"]["/V"]["native_graph"]["root"] == [
        {"string_hex": "61"},
        {"string_hex": "62"},
    ]
    assert choice["inherited_entries"]["/I"]["native_graph"]["root"] == [
        {"number": "0"},
        {"number": "2"},
    ]
    assert choice["inherited_entries"]["/TI"]["value"] == 1
    assert len(choice["inherited_entries"]["/Opt"]["native_graph"]["root"]) == 3


def test_all_widgets_expose_displayed_geometry_with_rotation_and_crop():
    source = form_pdf()
    across = named(source, "across")
    positions = [w["page_occurrences"][0] for w in across["widgets"]]
    assert [p["locator"]["page"]["page_index"] for p in positions] == [0, 2]
    assert positions[0]["display_geometry"]["rect"] == pytest.approx(
        [0.15, 0.56, 0.4, 0.6]
    )
    assert positions[1]["display_geometry"]["rect"] == pytest.approx(
        [50 / 380, 260 / 460, 150 / 380, 280 / 460]
    )
    rotated = [r for r in records(source) if r["qualified_name"] == "duplicate"][1]
    geometry = rotated["widgets"][0]["page_occurrences"][0]["display_geometry"]
    assert geometry["rect"] == pytest.approx([0.4, 0.15, 0.44, 0.4])


def test_catalog_is_readonly_even_with_xfa_and_need_appearances():
    def dual(pdf):
        pdf.Root.AcroForm.XFA = pikepdf.Array(
            ["template", pdf.make_stream(b"<template/>")]
        )
        pdf.Root.AcroForm.NeedAppearances = True

    source = rewrite(form_pdf(), dual)
    before_pixels = pixels(source)
    with NativePdfPackage(source) as package:
        before = graph_digest(
            PdfObjectGraph(package.page_map()).describe(package.pdf.Root)
        )
        catalog = FieldCatalog(package)
        assert catalog.inspect()["xfa_present"] is True
        for node in catalog.tree.nodes.values():
            catalog.record(node.locator)
        assert (
            graph_digest(PdfObjectGraph(package.page_map()).describe(package.pdf.Root))
            == before
        )
        assert package.pdf.Root.AcroForm.NeedAppearances is True
        with pytest.raises(ValueError, match="XFA"):
            package.check_editable()
    assert pixels(source) == before_pixels


def test_current_reference_rejects_stale_revision_and_changed_shared_resource():
    source = form_pdf()
    record = named(source, "across")
    ref = PdfFieldReference(
        asset_id="file_" + "a" * 32,
        revision=hashlib.sha256(source).hexdigest(),
        locator=PdfFieldLocator.model_validate(record["locator"]),
        value_sha256=graph_digest(record),
    )
    with NativePdfPackage(source) as package:
        catalog = FieldCatalog(package)
        assert catalog.verify(ref).obj.T == "across"
        with pytest.raises(ValueError, match="Stale"):
            catalog.verify(ref.model_copy(update={"revision": "0" * 64}))
        with pytest.raises(ValueError, match="Stale"):
            catalog.verify(ref.model_copy(update={"value_sha256": "0" * 64}))

    def font(pdf):
        pdf.Root.AcroForm.DR.Font.Helv.BaseFont = pikepdf.Name.Courier

    changed = rewrite(source, font)
    assert graph_digest(named(changed, "across")) != graph_digest(record)


def test_orphan_and_repeated_page_widgets_are_reported_without_deduplication():
    def alter(pdf):
        obj = pdf.Root.AcroForm.Fields[0]
        pdf.pages[2].obj.Annots.append(obj)
        orphan = pdf.make_indirect(
            pikepdf.Dictionary(
                Type=pikepdf.Name.Annot,
                Subtype=pikepdf.Name.Widget,
                Rect=pikepdf.Array([1, 2, 3, 4]),
            )
        )
        pdf.pages[0].obj.Annots.append(orphan)

    source = rewrite(form_pdf(), alter)
    catalog = inspect_fields(source)
    assert catalog["page_widget_occurrence_count"] == 9
    assert len(catalog["orphan_page_widgets"]) == 1
    widget = named(source, "duplicate")["widgets"][0]
    assert len(widget["page_occurrences"]) == 2
    assert set(widget["issues"]) == {
        "widget_has_multiple_page_occurrences",
        "widget_page_link_disagrees_with_annots",
    }


def test_direct_equal_dictionaries_are_not_matched_as_object_identity():
    def alter(pdf):
        obj = pikepdf.Dictionary(
            Type=pikepdf.Name.Annot,
            Subtype=pikepdf.Name.Widget,
            FT=pikepdf.Name.Tx,
            T=pikepdf.String("direct"),
            Rect=pikepdf.Array([1, 2, 3, 4]),
        )
        pdf.Root.AcroForm.Fields.append(obj)
        pdf.pages[0].obj.Annots.append(obj)

    source = rewrite(form_pdf(), alter)
    record = named(source, "direct")
    assert record["locator"]["object_id"] == 0
    assert record["widgets"][0]["page_occurrences"] == []
    assert "unresolved_direct_widget_identity" in record["widgets"][0]["issues"]
    assert (
        inspect_fields(source)["orphan_page_widgets"][0]["reason"]
        == "unresolved_direct_widget_identity"
    )


@pytest.mark.parametrize(
    "problem", ["cycle", "shared", "bad_fields", "bad_kids", "scalar_field"]
)
def test_invalid_or_unbounded_field_trees_fail_explicitly(problem):
    def alter(pdf):
        fields = pdf.Root.AcroForm.Fields
        if problem == "cycle":
            fields[2].Kids.append(fields[2])
        elif problem == "shared":
            fields.append(fields[0])
        elif problem == "bad_fields":
            pdf.Root.AcroForm.Fields = 7
        elif problem == "bad_kids":
            fields[2].Kids = 7
        else:
            fields.append(7)

    with pytest.raises(ValueError, match=r"field tree|form /Fields|form /Kids"):
        inspect_fields(rewrite(form_pdf(), alter))


def test_bad_parent_and_ambiguous_widget_value_are_not_repaired_or_hidden():
    def alter(pdf):
        fields = pdf.Root.AcroForm.Fields
        fields[2].Kids[0].Parent = fields[0]
        fields[3].Kids[0].V = pikepdf.String("ambiguous child value")

    source = rewrite(form_pdf(), alter)
    hidden = named(source, "person.hidden")
    assert hidden["issues"] == ["parent_link_disagrees_with_tree"]
    assert hidden["parent_link"]["field_paths"] == [[0]]
    radio = named(source, "radio")
    assert radio["widgets"][0]["issues"] == ["widget_has_ambiguous_field_attributes"]
    assert "/V" in str(radio["widgets"][0]["native_graph"])


def test_empty_form_and_no_form_are_distinct_catalogs():
    source = build_pdf()
    first = inspect_fields(source)
    assert first["field_count"] == first["page_widget_occurrence_count"] == 0
    second = inspect_fields(
        rewrite(
            source,
            lambda pdf: setattr(
                pdf.Root,
                "AcroForm",
                pikepdf.Dictionary(Fields=pikepdf.Array(), NeedAppearances=True),
            ),
        )
    )
    assert first["catalog_sha256"] != second["catalog_sha256"]


@pytest.mark.parametrize(
    "rect", [None, [1, 2, 3], [1, 2, 1, 4], ["1", 2, 3, 4], [True, 2, 3, 4]]
)
def test_invalid_widget_geometry_is_visible_without_losing_native_data(rect):
    def alter(pdf):
        widget = pdf.Root.AcroForm.Fields[0]
        if rect is None:
            del widget.Rect
        else:
            widget.Rect = pikepdf.Array(rect)

    record = named(rewrite(form_pdf(), alter), "duplicate")
    widget = record["widgets"][0]
    assert widget["page_occurrences"][0]["display_geometry"] == {
        "status": "invalid_native_rectangle"
    }
    assert widget["native_graph"]


def test_choice_inherits_options_indices_and_scroll_position_from_own_parent():
    def alter(pdf):
        root = pdf.Root.AcroForm.Fields[5]
        child = pdf.make_indirect(
            pikepdf.Dictionary(T=pikepdf.String("child"), Parent=root)
        )
        # A nonvisual child uses its native ancestor options without flattening them.
        root.Kids = pikepdf.Array([child])

    source = rewrite(form_pdf(), alter)
    parent, child = named(source, "choice"), named(source, "choice.child")
    for key in ("/Opt", "/I", "/TI", "/V", "/Ff"):
        assert (
            child["inherited_entries"][key]["native_graph"]
            == parent["inherited_entries"][key]["native_graph"]
        )
        assert child["inherited_entries"][key]["source"]["field"]["field_path"] == [5]
    assert "merged_widget_has_kids" in parent["issues"]


def test_detached_widgets_preserve_their_native_appearance_and_missing_page_issue():
    def alter(pdf):
        widget = pdf.Root.AcroForm.Fields[3].Kids[0]
        page = pdf.pages[0]
        page.obj.Annots = pikepdf.Array(
            [a for a in page.obj.Annots if a.objgen != widget.objgen]
        )

    source = rewrite(form_pdf(), alter)
    widget = named(source, "radio")["widgets"][0]
    assert widget["page_occurrences"] == []
    assert widget["issues"] == ["widget_not_found_in_page_annots"]
    assert widget["normal_appearance_states"] == ["/First", "/Off"]


def test_record_hash_covers_native_appearance_bytes_and_unknown_properties():
    source = form_pdf()
    before = named(source, "radio")

    def alter(pdf):
        field = pdf.Root.AcroForm.Fields[3]
        field.Kids[0].AP.N.First.write(b"q 1 0 0 rg 0 0 100 20 re f Q")
        field.PrivateProducerData = pikepdf.String("retain unknown field data")

    changed = named(rewrite(source, alter), "radio")
    assert graph_digest(changed) != graph_digest(before)
    assert changed["widgets"][0]["native_graph"] != before["widgets"][0]["native_graph"]
    assert "/PrivateProducerData" in str(changed["native_graph"])


def test_encrypted_pdf_with_empty_user_password_still_requires_explicit_workflow():
    with pikepdf.Pdf.open(io.BytesIO(form_pdf())) as pdf:
        output = io.BytesIO()
        pdf.save(output, encryption=pikepdf.Encryption(owner="fixture-owner", user=""))
    with pytest.raises(ValueError, match="Encrypted PDF"):
        inspect_fields(output.getvalue())


def test_field_tree_count_and_depth_are_bounded_before_record_expansion(monkeypatch):
    from src.infrastructure import native_pdf_field_tree as tree

    with pikepdf.Pdf.new() as pdf:
        pdf.add_blank_page()
        root = pdf.make_indirect(pikepdf.Dictionary(T=pikepdf.String("root")))
        child = pdf.make_indirect(
            pikepdf.Dictionary(T=pikepdf.String("child"), Parent=root)
        )
        root.Kids = pikepdf.Array([child])
        child.Kids = pikepdf.Array(
            [
                pdf.make_indirect(
                    pikepdf.Dictionary(
                        T=pikepdf.String("leaf"), FT=pikepdf.Name.Tx, Parent=child
                    )
                )
            ]
        )
        pdf.Root.AcroForm = pikepdf.Dictionary(Fields=pikepdf.Array([root]))
        stream = io.BytesIO()
        pdf.save(stream)
    source = stream.getvalue()
    monkeypatch.setattr(tree, "MAX_FIELD_DEPTH", 2)
    with pytest.raises(ValueError, match="count or depth"):
        inspect_fields(source)
    monkeypatch.setattr(tree, "MAX_FIELD_DEPTH", 64)
    monkeypatch.setattr(tree, "MAX_PDF_FIELDS", 2)
    with pytest.raises(ValueError, match="count or depth"):
        inspect_fields(source)


def test_representation_budgets_include_all_field_records(monkeypatch):
    from src.infrastructure import native_pdf_fields as fields

    source = form_pdf()
    # Each record fits on its own; the complete discovery inventory must also fit.
    record_sizes = [len(canonical(record)) for record in records(source)]
    monkeypatch.setattr(fields, "MAX_NATIVE_RESULT_BYTES", max(record_sizes) + 100)
    with pytest.raises(ValueError, match="aggregate representation"):
        inspect_fields(source)
    monkeypatch.setattr(fields, "MAX_FIELD_RECORD_BYTES", 100)
    with pytest.raises(ValueError, match="field representation"):
        named(source, "across")


@pytest.mark.parametrize("path", [[], [-1], [True], [20000], [0] * 65])
def test_field_locator_rejects_invalid_physical_paths(path):
    with pytest.raises(ValueError):
        PdfFieldLocator(field_path=path, object_id=1, generation=0)


def test_field_path_alone_does_not_authorize_another_same_named_field():
    source = form_pdf()
    first = named(source, "duplicate")
    locator = PdfFieldLocator.model_validate(first["locator"])
    with pytest.raises(ValueError, match="locator"):
        read_field(source, locator.model_copy(update={"field_path": [1]}))
