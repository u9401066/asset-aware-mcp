"""Native form CRUD preserves source content, complete widget coverage and history."""

from __future__ import annotations

import hashlib
import io

import pikepdf
import pymupdf
import pytest

from src.domain.native_pdf_fields import (
    PdfFieldLocator,
    PdfFieldReference,
    PdfFieldsUpdate,
)
from src.infrastructure.native_pdf_field_edits import edit_fields
from src.infrastructure.native_pdf_fields import (
    FieldCatalog,
    inspect_fields,
    read_field,
)
from src.infrastructure.native_pdf_graph import graph_digest
from src.infrastructure.native_pdf_package import NativePdfPackage
from tests.native_pdf_field_helpers import form_pdf
from tests.native_pdf_helpers import build_pdf, page_reference, pixels, rewrite


def field_records(source):
    with NativePdfPackage(source) as package:
        catalog = FieldCatalog(package)
        return [catalog.record(n.locator) for n in catalog.tree.nodes.values()]


def reference(source, name, occurrence=0):
    record = [r for r in field_records(source) if r["qualified_name"] == name][
        occurrence
    ]
    return PdfFieldReference(
        asset_id="file_" + "a" * 32,
        revision=hashlib.sha256(source).hexdigest(),
        locator=PdfFieldLocator.model_validate(record["locator"]),
        value_sha256=graph_digest(record),
    ).model_dump()


def apply(source, edits):
    return edit_fields(
        source,
        PdfFieldsUpdate.model_validate(
            {
                "expected_catalog_sha256": inspect_fields(source)["catalog_sha256"],
                "edits": edits,
            }
        ),
    )


def update(source, name, value, *, occurrence=0, style=None):
    ref = reference(source, name, occurrence)
    record = read_field(source, PdfFieldLocator.model_validate(ref["locator"]))
    policy = (
        "no_widgets"
        if not record["widgets"]
        else "preserve_native_button_states"
        if value["kind"] == "button"
        else "replace_all_widget_appearances"
    )
    return {
        "op": "update",
        "reference": ref,
        "value": value,
        "appearance_policy": policy,
        "widget_styles": [
            {"widget_path": w["tree_path"], "style": style or {"font_size": 8.0}}
            for w in record["widgets"]
        ]
        if policy == "replace_all_widget_appearances"
        else [],
    }


def create(
    source,
    *,
    kind="text",
    name="new",
    value=None,
    pages=(0,),
    options=None,
    multiselect=False,
):
    if value is None:
        value = (
            {"kind": "button", "state": "/Off"}
            if kind in {"checkbox", "radio"}
            else {"kind": "choice", "indices": [0]}
            if kind == "choice"
            else {"kind": "text", "text": "中文 007 µg α"}
        )
    return {
        "op": "create",
        "field": {
            "name": name,
            "kind": kind,
            "value": value,
            "options": options or [],
            "multiselect": multiselect,
            "widgets": [
                {
                    "page_reference": page_reference(source, page).model_dump(),
                    "rect": [0.1, 0.35, 0.8, 0.6],
                    **(
                        {
                            "on_state": f"/Choice{index}"
                            if kind == "radio"
                            else "/Accepted"
                        }
                        if kind in {"radio", "checkbox"}
                        else {}
                    ),
                }
                for index, page in enumerate(pages)
            ],
        },
    }


def delete(source, name):
    return {
        "op": "delete",
        "reference": reference(source, name),
        "scope": "field_subtree_and_all_widgets",
    }


def appearance_text(source, name, widget_index=0):
    """Independent renderer/text extractor sees the stored AP, not the native V."""
    with NativePdfPackage(source) as package:
        catalog = FieldCatalog(package)
        node = next(
            n
            for n in catalog.tree.nodes.values()
            if catalog.record(n.locator)["qualified_name"] == name
        )
        obj = node.widgets[widget_index].obj
        ap = obj.AP.N
        with pikepdf.Pdf.new() as viewer:
            page = viewer.add_blank_page(
                page_size=(float(ap.BBox[2]), float(ap.BBox[3]))
            )
            page.obj.Resources = pikepdf.Dictionary(
                XObject=pikepdf.Dictionary(Ap=viewer.copy_foreign(ap))
            )
            page.obj.Contents = viewer.make_stream(b"/Ap Do")
            output = io.BytesIO()
            viewer.save(output)
        with pymupdf.open(stream=output.getvalue(), filetype="pdf") as rendered:
            return rendered[0].get_text()


def test_unicode_text_create_update_delete_preserves_other_pages_and_source():
    source = build_pdf(links=True, labels=True)
    original = hashlib.sha256(source).hexdigest()
    created, receipt = apply(source, [create(source, pages=(0, 2))])
    assert inspect_fields(created)["field_count"] == 1
    assert inspect_fields(created)["page_widget_occurrence_count"] == 2
    assert "中文 007 µg α" in appearance_text(created, "new", 0)
    assert "中文 007 µg α" in appearance_text(created, "new", 1)
    assert pixels(created)[1] == pixels(source)[1]
    assert receipt.changes[-1]["affected_pages"] == [0, 2]
    old = reference(created, "new")
    changed, receipt = apply(
        created,
        [
            update(
                created,
                "new",
                {"kind": "text", "text": "更新 008 µg β"},
                style={"font_size": 12.0},
            )
        ],
    )
    assert "更新 008 µg β" in appearance_text(changed, "new", 0)
    assert "更新 008 µg β" in appearance_text(changed, "new", 1)
    assert (
        receipt.changes[0]["before"]["inherited_entries"]["/V"]["text"]
        == "中文 007 µg α"
    )
    with NativePdfPackage(changed) as package, pytest.raises(ValueError, match="Stale"):
        FieldCatalog(package).verify(PdfFieldReference.model_validate(old))
    removed, receipt = apply(changed, [delete(changed, "new")])
    assert inspect_fields(removed)["field_count"] == 0
    assert pixels(removed) == pixels(source)
    assert hashlib.sha256(source).hexdigest() == original
    assert receipt.changes[0]["secure_erasure"] is False


@pytest.mark.parametrize("kind", ["checkbox", "radio"])
def test_button_lifecycle_updates_every_widget_and_preserves_native_appearance_streams(
    kind,
):
    source = build_pdf()
    created, _ = apply(source, [create(source, kind=kind, pages=(0, 2))])
    state = "/Choice1" if kind == "radio" else "/Accepted"
    with NativePdfPackage(created) as package:
        before = [
            (
                w.obj.AP.N.Off.read_bytes(),
                [(key, value.read_bytes()) for key, value in w.obj.AP.N.items()],
            )
            for n in FieldCatalog(package).tree.nodes.values()
            for w in n.widgets
        ]
    changed, receipt = apply(
        created, [update(created, "new", {"kind": "button", "state": state})]
    )
    record = receipt.changes[0]["after"]
    assert record["inherited_entries"]["/V"]["text"] == state
    assert [w["appearance_state"] for w in record["widgets"]] == (
        ["/Off", state] if kind == "radio" else [state, state]
    )
    with NativePdfPackage(changed) as package:
        after = [
            (
                w.obj.AP.N.Off.read_bytes(),
                [(key, value.read_bytes()) for key, value in w.obj.AP.N.items()],
            )
            for n in FieldCatalog(package).tree.nodes.values()
            for w in n.widgets
        ]
    assert after == before
    noop, no_receipt = apply(
        changed, [update(changed, "new", {"kind": "button", "state": state})]
    )
    assert noop == changed and no_receipt.changed_parts == []
    assert (
        apply(changed, [delete(changed, "new")])[1].changes[0]["secure_erasure"]
        is False
    )


def test_multiselect_choice_roundtrip_keeps_export_values_indices_and_visible_labels():
    source = build_pdf()
    created, _ = apply(
        source,
        [
            create(
                source,
                kind="choice",
                options=[
                    {"export": "a", "label": "甲 007"},
                    {"export": "same", "label": "乙 µg"},
                    {"export": "same", "label": "丙 α"},
                ],
                multiselect=True,
                value={"kind": "choice", "indices": [0, 2]},
            )
        ],
    )
    text = appearance_text(created, "new")
    assert all(label in text for label in ["甲 007", "乙 µg", "丙 α"])
    changed, receipt = apply(
        created,
        [
            update(
                created,
                "new",
                {"kind": "choice", "indices": [1, 2]},
                style={"font_size": 12.0},
            )
        ],
    )
    with NativePdfPackage(changed) as package:
        field = package.pdf.Root.AcroForm.Fields[0]
        assert list(field.I) == [1, 2]
        assert [str(v) for v in field.V] == ["same", "same"]
    assert receipt.changes[0]["after"]["inherited_entries"]["/I"]["native_graph"][
        "root"
    ] == [{"number": "1"}, {"number": "2"}]
    empty, _ = apply(
        changed, [update(changed, "new", {"kind": "choice", "indices": []})]
    )
    with NativePdfPackage(empty) as package:
        assert list(package.pdf.Root.AcroForm.Fields[0].V) == []
        assert list(package.pdf.Root.AcroForm.Fields[0].I) == []


def test_duplicate_name_edits_target_only_exact_original_object():
    source = form_pdf()
    changed, receipt = apply(
        source,
        [
            update(
                source,
                "duplicate",
                {"kind": "text", "text": "only second"},
                occurrence=1,
            )
        ],
    )
    records = [r for r in field_records(changed) if r["qualified_name"] == "duplicate"]
    assert [r["inherited_entries"]["/V"]["text"] for r in records] == [
        "第一筆 007 µg",
        "only second",
    ]
    assert receipt.changes[-1]["affected_pages"] == [1]
    assert pixels(changed)[0] == pixels(source)[0]


def test_hidden_value_and_group_deletion_keep_source_actions_and_other_fields():
    source = form_pdf()
    changed, receipt = apply(
        source, [update(source, "person.hidden", {"kind": "text", "text": "008"})]
    )
    assert pixels(changed) == pixels(source)
    assert receipt.changes[-1]["affected_pages"] == []
    assert (
        next(
            r for r in field_records(changed) if r["qualified_name"] == "person.hidden"
        )["inherited_entries"]["/V"]["text"]
        == "008"
    )
    removed, _ = apply(changed, [delete(changed, "person")])
    assert not any(
        r["qualified_name"].startswith("person") for r in field_records(removed)
    )
    assert pixels(removed) == pixels(source)


def test_batched_delete_then_update_uses_original_refs_and_original_before_records():
    source = form_pdf()
    old = next(r for r in field_records(source) if r["qualified_name"] == "across")
    changed, receipt = apply(
        source,
        [
            delete(source, "duplicate"),
            update(source, "across", {"kind": "text", "text": "008"}),
        ],
    )
    assert receipt.changes[1]["before"] == old
    assert receipt.changes[1]["after"]["locator"]["field_path"] == [3]
    assert "008" in appearance_text(changed, "across")


def test_new_child_is_created_beneath_exact_parent_and_native_inheritance_stays():
    source = form_pdf()
    edit = create(
        source, name="second", pages=(), value={"kind": "text", "text": "009"}
    )
    edit["parent_reference"] = reference(source, "person")
    changed, _ = apply(source, [edit])
    child = next(
        r for r in field_records(changed) if r["qualified_name"] == "person.second"
    )
    assert child["locator"]["field_path"] == [2, 1]
    assert child["inherited_entries"]["/MaxLen"]["value"] == 40


def test_new_group_hierarchy_then_child_insertion_and_subtree_deletion():
    source = build_pdf()
    edit = create(source, name="value", pages=(), value={"kind": "text", "text": "007"})
    edit["new_groups"] = ["section", "patient"]
    created, _ = apply(source, [edit])
    assert [r["qualified_name"] for r in field_records(created)] == [
        "section",
        "section.patient",
        "section.patient.value",
    ]
    second = create(
        created, name="second", pages=(), value={"kind": "text", "text": "008"}
    )
    second["parent_reference"] = reference(created, "section.patient")
    expanded, _ = apply(created, [second])
    removed, receipt = apply(expanded, [delete(expanded, "section")])
    assert inspect_fields(removed)["field_count"] == 0
    assert len(receipt.changes[0]["deleted_fields"]) == 4
    assert pixels(removed) == pixels(source)


def test_single_line_text_must_not_silently_wrap_into_multiple_lines():
    source = build_pdf()
    edit = create(source, value={"kind": "text", "text": "word " * 60})
    with pytest.raises(ValueError, match=r"fit|bounds"):
        apply(source, [edit])


@pytest.mark.parametrize("rotation", [90, 180, 270])
def test_existing_widget_rotation_preserves_its_native_rectangle(rotation):
    source = build_pdf()
    created, _ = apply(source, [create(source, value={"kind": "text", "text": "007"})])

    def rotate(pdf):
        pdf.Root.AcroForm.Fields[0].Kids[0].MK.R = rotation

    rotated = rewrite(created, rotate)
    before = field_records(rotated)[0]["widgets"][0]["page_occurrences"][0][
        "display_geometry"
    ]
    changed, receipt = apply(
        rotated,
        [
            update(
                rotated,
                "new",
                {"kind": "text", "text": "008"},
                style={"font_size": 12.0},
            )
        ],
    )
    after = receipt.changes[0]["after"]["widgets"][0]["page_occurrences"][0][
        "display_geometry"
    ]
    assert after == before
    assert "008" in appearance_text(changed, "new")


@pytest.mark.parametrize("fault", ["catalog", "record", "revision", "page"])
def test_stale_references_and_catalog_fail_before_any_returned_candidate(fault):
    source = form_pdf()
    edit = update(source, "radio", {"kind": "button", "state": "/First"})
    payload = {
        "expected_catalog_sha256": inspect_fields(source)["catalog_sha256"],
        "edits": [edit],
    }
    if fault == "catalog":
        payload["expected_catalog_sha256"] = "0" * 64
    elif fault == "record":
        edit["reference"]["value_sha256"] = "0" * 64
    elif fault == "revision":
        edit["reference"]["revision"] = "0" * 64
    else:
        edit = create(source)
        edit["field"]["widgets"][0]["page_reference"]["value_sha256"] = "0" * 64
        payload["edits"] = [edit]
    with pytest.raises(ValueError, match="Stale"):
        edit_fields(source, PdfFieldsUpdate.model_validate(payload))


def test_all_widget_appearance_replacements_are_required_and_overflow_is_rejected():
    source = form_pdf()
    edit = update(source, "across", {"kind": "text", "text": "008"})
    edit["widget_styles"].pop()
    with pytest.raises(ValueError, match="every original widget"):
        apply(source, [edit])
    edit = update(
        source, "across", {"kind": "text", "text": "W" * 200}, style={"font_size": 30.0}
    )
    with pytest.raises(ValueError, match=r"fit|bounds"):
        apply(source, [edit])


@pytest.mark.parametrize(
    "dependency",
    [
        "object_ref",
        "shared_array",
        "tagged",
        "readonly",
        "locked",
        "regenerate",
        "xfa",
        "signature",
    ],
)
def test_native_dependencies_and_existing_protection_are_not_bypassed(dependency):
    def alter(pdf):
        field = pdf.Root.AcroForm.Fields[4]
        if dependency == "object_ref":
            pdf.Root.CustomFieldPointer = field
        elif dependency == "shared_array":
            annots = pdf.make_indirect(pdf.pages[0].obj.Annots)
            pdf.pages[0].obj.Annots = annots
            pdf.Root.CustomArrayPointer = annots
        elif dependency == "tagged":
            field.Kids[0].StructParent = 7
        elif dependency == "readonly":
            field.Ff = 1
        elif dependency == "locked":
            field.Kids[0].F = 128
        elif dependency == "regenerate":
            pdf.Root.AcroForm.NeedAppearances = True
        elif dependency == "xfa":
            pdf.Root.AcroForm.XFA = pdf.make_stream(b"<xfa/>")
        else:
            pdf.Root.AcroForm.Fields[0].FT = pikepdf.Name.Sig

    source = rewrite(form_pdf(), alter)
    with pytest.raises(ValueError):
        apply(source, [delete(source, "across")])


def test_failed_second_edit_returns_no_candidate_and_original_bytes_are_untouched():
    source = form_pdf()
    original = source
    with pytest.raises(ValueError, match="absent"):
        apply(
            source,
            [
                update(source, "person.hidden", {"kind": "text", "text": "changed"}),
                update(source, "radio", {"kind": "button", "state": "/Missing"}),
            ],
        )
    assert source == original
    assert (
        next(
            r for r in field_records(source) if r["qualified_name"] == "person.hidden"
        )["inherited_entries"]["/V"]["text"]
        == "007"
    )


def test_empty_visible_text_has_valid_default_appearance_font():
    source = build_pdf()
    changed, _ = apply(source, [create(source, value={"kind": "text", "text": ""})])
    with NativePdfPackage(changed) as package:
        widget = package.pdf.Root.AcroForm.Fields[0].Kids[0]
        assert "/DA" in widget
        assert package.pdf.Root.AcroForm.DR.Font


def test_repeated_unicode_updates_reuse_fonts_and_identical_update_is_byte_noop():
    source = build_pdf()
    first, _ = apply(source, [create(source)])
    second, _ = apply(
        first,
        [
            update(
                first,
                "new",
                {"kind": "text", "text": "更新 008 µg β"},
                style={"font_size": 12.0},
            )
        ],
    )
    assert len(second) < len(first) + 50_000
    same, result = apply(
        second,
        [
            update(
                second,
                "new",
                {"kind": "text", "text": "更新 008 µg β"},
                style={"font_size": 12.0},
            )
        ],
    )
    assert same == second and not result.changes


def test_semantically_absent_null_properties_do_not_break_style_resource_copy():
    def nulls(pdf):
        pdf.Root.AcroForm.Fields[0].MK = pikepdf.Object.parse(
            b"<< /BG null /BC [0 0 0] >>"
        )
        pdf.Root.AcroForm.DR.NullProperty = pikepdf.Object.parse(b"<< /unused null >>")
        # pikepdf keys() omits null entries, while items() retains them.
        fonts = pikepdf.Object.parse(b"<< /UnusedFont null >>")
        fonts.Helv = pdf.Root.AcroForm.DR.Font.Helv
        pdf.Root.AcroForm.DR.Font = fonts

    source = rewrite(form_pdf(), nulls)
    changed, _ = apply(
        source, [update(source, "duplicate", {"kind": "text", "text": "007"})]
    )
    assert "007" in appearance_text(changed, "duplicate")


def test_dependency_budget_counts_repeated_indirect_edges(monkeypatch):
    from src.infrastructure import native_pdf_field_journal as journal

    monkeypatch.setattr(journal, "MAX_DEPENDENCY_NODES", 64)
    with pikepdf.Pdf.new() as pdf:
        page = pdf.add_blank_page()
        pdf.Root.ManyReferences = pikepdf.Array([page.obj] * 200)
        with pytest.raises(ValueError, match="dependency scan exceeds"):
            journal.FieldJournal(pdf)


def test_delete_group_receipt_contains_every_removed_field_not_only_group_definition():
    source = form_pdf()
    _, receipt = apply(source, [delete(source, "person")])
    removed = receipt.changes[0]["deleted_fields"]
    assert [r["qualified_name"] for r in removed] == ["person", "person.hidden"]
    assert removed[1]["inherited_entries"]["/V"]["text"] == "007"


def test_multiline_and_comb_fields_render_every_character_without_changing_the_value():
    source = build_pdf()
    edit = create(source, value={"kind": "text", "text": "第一行 007\n第二行 µg"})
    edit["field"]["multiline"] = True
    created, _ = apply(source, [edit])
    assert "第一行 007" in appearance_text(created, "new")
    assert "第二行 µg" in appearance_text(created, "new")

    def comb(pdf):
        field = pdf.Root.AcroForm.Fields[0]
        field.Ff = 16777216
        field.MaxLen = 5
        field.V = pikepdf.String("007")

    combed = rewrite(created, comb)
    changed, _ = apply(
        combed,
        [
            update(
                combed,
                "new",
                {"kind": "text", "text": "008µg"},
                style={"font_size": 12.0},
            )
        ],
    )
    assert "".join(appearance_text(changed, "new").split()) == "008µg"


def test_no_border_request_does_not_leave_a_hairline_border():
    source = build_pdf()
    edit = create(source, value={"kind": "text", "text": ""})
    edit["field"]["widgets"][0]["style"] = {"border_width": 0.0}
    changed, _ = apply(source, [edit])
    assert pixels(changed) == pixels(source)


def test_inverse_check_rejects_unplanned_source_content_change(monkeypatch):
    from src.infrastructure.native_pdf_field_appearance import FieldAppearanceFactory

    original = FieldAppearanceFactory.create

    def damaged(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        self.pdf.pages[0].obj.Contents = self.pdf.make_stream(
            b"q 1 0 0 rg 0 0 50 50 re f Q"
        )
        return result

    monkeypatch.setattr(FieldAppearanceFactory, "create", damaged)
    source = build_pdf()
    with pytest.raises(ValueError, match="outside the explicit"):
        apply(source, [create(source)])


def test_serialized_readback_rejects_writer_value_corruption(monkeypatch):
    from src.infrastructure import native_pdf_checks

    original = native_pdf_checks.save_pdf

    def damaged(pdf, *args, **kwargs):
        result = original(pdf, *args, **kwargs)

        def corrupt(candidate):
            candidate.Root.AcroForm.Fields[0].V = pikepdf.String(
                "wrong serialized value"
            )

        return rewrite(result, corrupt)

    monkeypatch.setattr(native_pdf_checks, "save_pdf", damaged)
    source = build_pdf()
    with pytest.raises(ValueError, match="changed during serialization"):
        apply(source, [create(source)])


@pytest.mark.parametrize("bad_value", ["\x00", "line\nbreak", "X" * 50])
def test_text_limits_reject_instead_of_stripping_or_truncating(bad_value):
    source = form_pdf()
    with pytest.raises(ValueError):
        apply(
            source,
            [update(source, "person.hidden", {"kind": "text", "text": bad_value})],
        )


@pytest.mark.parametrize("angle", [0, 90, 180, 270])
@pytest.mark.parametrize("unit", [1, 2])
def test_created_widget_display_geometry_matches_requested_rotated_crop(angle, unit):
    def alter(pdf):
        page = pdf.pages[0]
        page.obj.Rotate = angle
        page.obj.UserUnit = unit
        page.obj.CropBox = pikepdf.Array([10, 20, 390, 480])

    source = rewrite(build_pdf(), alter)
    created, receipt = apply(
        source, [create(source, value={"kind": "text", "text": "007"})]
    )
    geometry = receipt.changes[0]["after"]["widgets"][0]["page_occurrences"][0][
        "display_geometry"
    ]
    assert geometry["rect"] == pytest.approx([0.1, 0.35, 0.8, 0.6], abs=1e-6)
    assert "007" in appearance_text(created, "new")
