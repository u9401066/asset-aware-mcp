"""Atomic annotation edits with inverse native-graph and serialized-readback checks."""

from __future__ import annotations

import hashlib
import io
import uuid
from typing import TYPE_CHECKING, Any

import pikepdf
import pymupdf

from src.domain.native_asset_models import NativeEditResult
from src.domain.native_pdf_annotations import (
    ANNOTATION_REVIEW,
    PdfAnnotationCreate,
    PdfAnnotationDelete,
    PdfAnnotationLocator,
    PdfAnnotationMetadata,
    PdfAnnotationsUpdate,
    PdfAnnotationUpdate,
)
from src.infrastructure.native_pdf_annotation_dependencies import (
    owned_popup,
    require_unreferenced_deletions,
)
from src.infrastructure.native_pdf_annotation_factory import appearance_pdf
from src.infrastructure.native_pdf_annotations import METADATA_KEYS, AnnotationCatalog
from src.infrastructure.native_pdf_checks import (
    checked_serialization,
    document_graph,
    page_graph,
    render_fingerprint,
    verify_reference,
)
from src.infrastructure.native_pdf_graph import graph_digest
from src.infrastructure.native_pdf_package import NativePdfPackage, save_pdf

if TYPE_CHECKING:
    from src.domain.native_pdf_annotations import PdfAnnotationAppearance

APPEARANCE_KEYS = {
    "/Rect",
    "/AP",
    "/AS",
    "/C",
    "/IC",
    "/CA",
    "/BS",
    "/Border",
    "/BE",
    "/RD",
    "/QuadPoints",
    "/Vertices",
    "/L",
    "/LE",
    "/InkList",
    "/DA",
    "/DS",
    "/RC",
    "/Q",
    "/Rotate",
    "/Name",
    "/IT",
    "/CL",
}
KNOWN_KEYS = APPEARANCE_KEYS | {
    "/Type",
    "/Subtype",
    "/P",
    "/NM",
    "/Contents",
    "/T",
    "/Subj",
    "/M",
    "/CreationDate",
    "/F",
    "/Popup",
    "/Parent",
    "/IRT",
    "/RT",
    "/OC",
    "/StructParent",
    "/Lang",
    "/State",
    "/StateModel",
    "/ExData",
}
COMMENT_KINDS = {
    "/Text",
    "/FreeText",
    "/Highlight",
    "/Underline",
    "/StrikeOut",
    "/Squiggly",
    "/Square",
    "/Circle",
    "/Line",
    "/PolyLine",
    "/Polygon",
    "/Ink",
    "/Stamp",
    "/Caret",
    "/FileAttachment",
    "/Sound",
    "/Redact",
}


def _metadata(annotation: pikepdf.Object, metadata: PdfAnnotationMetadata) -> None:
    for name in metadata.model_fields_set:
        key = METADATA_KEYS[name]
        value = getattr(metadata, name)
        if value is None:
            if key in annotation:
                del annotation[key]
        elif not (
            isinstance(annotation.get(key), pikepdf.String)
            and str(annotation[key]) == value
        ):
            annotation[key] = pikepdf.String(value)


def _base_pixels(data: bytes) -> list[tuple[int, int, str]]:
    # annots=False can still let a Highlight's transparency change MuPDF's
    # page compositing by one color level. Remove annotations from a disposable
    # reader copy, never from the managed source or requested output. Native
    # inverse checks independently preserve every non-annotation object.
    with NativePdfPackage(data) as reader:
        for page in reader.pdf.pages:
            if "/Annots" in page.obj:
                del page.obj.Annots
        body = save_pdf(reader.pdf)
    with pymupdf.open(stream=body, filetype="pdf") as pdf:
        if pdf.is_repaired:
            raise ValueError("PDF annotation pixel readback required repair")
        result = []
        for page in pdf:
            scale = min(1.0, 512 / max(page.rect.width, page.rect.height))
            pix = page.get_pixmap(
                matrix=pymupdf.Matrix(scale, scale), alpha=False, annots=False
            )
            result.append(
                (pix.width, pix.height, hashlib.sha256(pix.samples).hexdigest())
            )
        return result


def _replace_contents(array: pikepdf.Object, items: list[pikepdf.Object]) -> None:
    for index in range(len(array) - 1, -1, -1):
        del array[index]
    for item in items:
        array.append(item)


def _set_annotations(page: pikepdf.Page, items: list[pikepdf.Object]) -> None:
    current = page.obj.get("/Annots")
    if current is None:
        page.obj.Annots = pikepdf.Array(items)
    else:
        _replace_contents(current, items)


class AnnotationMutation:
    def __init__(self, package: NativePdfPackage, request: PdfAnnotationsUpdate):
        self.package = package
        self.catalog = AnnotationCatalog(package)
        self.mapping = package.page_map()
        self.before_pages = [page_graph(p, self.mapping) for p in package.pdf.pages]
        self.before_document = document_graph(package.pdf, self.mapping)
        structural_pages = {
            edit.page_reference.locator.page_index
            if isinstance(edit, PdfAnnotationCreate)
            else edit.reference.locator.page.page_index
            for edit in request.edits
            if not isinstance(edit, PdfAnnotationUpdate)
        }
        self.page_arrays = [
            (p, p.obj.get("/Annots"), list(p.obj.get("/Annots", [])))
            for index, p in enumerate(package.pdf.pages)
            if index in structural_pages
        ]
        self.saved: list[tuple[pikepdf.Object, dict]] = []
        self.targets: list[tuple[Any, pikepdf.Page, pikepdf.Object | None]] = []
        self.deleting: list[pikepdf.Object] = []
        self.affected: set[int] = set()
        self.changes: list[dict[str, Any]] = []
        self.before_records: dict[str, dict[str, Any]] = {}
        identities = set()
        for edit in request.edits:
            if isinstance(edit, PdfAnnotationCreate):
                page = verify_reference(package, edit.page_reference)
                self.targets.append((edit, page, None))
                continue
            ref = edit.reference
            record = self.catalog.record(ref.locator)
            self.before_records[graph_digest(ref.locator.model_dump())] = record
            if (
                hashlib.sha256(package.data).hexdigest() != ref.revision
                or graph_digest(record) != ref.value_sha256
            ):
                raise ValueError("Stale native PDF annotation reference")
            annotation = self.catalog.locate(ref.locator)
            identity = (ref.locator.page.page_index, ref.locator.annotation_index)
            if identity in identities:
                raise ValueError(
                    "A batch must name each existing annotation at most once"
                )
            identities.add(identity)
            if (
                annotation.is_indirect
                and sum(
                    obj.objgen == annotation.objgen for _, obj in self.catalog.entries
                )
                != 1
            ):
                raise ValueError(
                    "Shared PDF annotation requires an explicit ownership workflow"
                )
            if annotation.get("/Subtype") in {pikepdf.Name.Widget, pikepdf.Name.Popup}:
                raise ValueError(
                    "Widget and standalone Popup edits require their owning structure"
                )
            if int(annotation.get("/F", 0)) & (64 | 128 | 512):
                raise ValueError("Read-only or locked PDF annotation cannot be edited")
            self.saved.append((annotation, dict(annotation.items())))
            self.targets.append((edit, package.locate(ref.locator.page), annotation))
            if isinstance(edit, PdfAnnotationDelete):
                self.deleting.append(annotation)
                popup = owned_popup(self.catalog, annotation)
                if popup is not None:
                    if int(popup.get("/F", 0)) & (64 | 128 | 512):
                        raise ValueError(
                            "Read-only or locked owned PDF popup cannot be deleted"
                        )
                    self.deleting.append(popup)
        require_unreferenced_deletions(self.catalog, self.deleting, structural_pages)

    def run(self) -> tuple[bytes, NativeEditResult]:
        for edit, page, annotation in self.targets:
            index = (
                edit.page_reference.locator.page_index
                if isinstance(edit, PdfAnnotationCreate)
                else edit.reference.locator.page.page_index
            )
            self.affected.add(index)
            before = (
                self.before_records[graph_digest(edit.reference.locator.model_dump())]
                if not isinstance(edit, PdfAnnotationCreate)
                else None
            )
            if isinstance(edit, PdfAnnotationCreate):
                created = self._generated(page, edit.appearance)
                _metadata(created, edit.metadata)
                if (
                    edit.appearance.kind == "FreeText"
                    and created.get("/Contents") != edit.appearance.text
                ):
                    raise ValueError(
                        "FreeText metadata contents must match the explicit appearance text"
                    )
                created.NM = pikepdf.String("asset-aware-" + uuid.uuid4().hex)
                created.P = page.obj
                additions = [created]
                if "/Popup" in created:
                    created.Popup.P = page.obj
                    additions.append(created.Popup)
                _set_annotations(page, [*page.obj.get("/Annots", []), *additions])
                self.changes.append(
                    {
                        "operation": "create_annotation",
                        "page_index": index,
                        "name": str(created.NM),
                        "request": edit.model_dump(mode="json", exclude_unset=True),
                    }
                )
            elif isinstance(edit, PdfAnnotationUpdate):
                assert annotation is not None
                self._update(page, annotation, edit)
                self.changes.append(
                    {
                        "operation": "update_annotation",
                        "before": before,
                        "request": edit.model_dump(mode="json", exclude_unset=True),
                    }
                )
            else:
                self.changes.append(
                    {
                        "operation": "delete_annotation",
                        "before": before,
                        "request": edit.model_dump(mode="json", exclude_unset=True),
                        "secure_erasure": False,
                    }
                )
        # Remove original slots after all references have been consumed.
        deleted_ids = {obj.objgen for obj in self.deleting if obj.is_indirect}
        direct_slots = {
            (
                edit.reference.locator.page.page_index,
                edit.reference.locator.annotation_index,
            )
            for edit, _, obj in self.targets
            if isinstance(edit, PdfAnnotationDelete)
            and obj is not None
            and not obj.is_indirect
        }
        surviving_slots = {}
        for index, page in enumerate(self.package.pdf.pages):
            if "/Annots" in page.obj:
                remaining: list[pikepdf.Object] = []
                for slot, obj in enumerate(page.obj.Annots):
                    if (
                        obj.objgen not in deleted_ids
                        and (index, slot) not in direct_slots
                    ):
                        surviving_slots[index, slot] = len(remaining)
                        remaining.append(obj)
                if len(remaining) != len(page.obj.Annots):
                    _set_annotations(page, remaining)
        final_catalog = AnnotationCatalog(self.package)
        after_pages = [page_graph(p, self.mapping) for p in self.package.pdf.pages]
        if (
            after_pages == self.before_pages
            and document_graph(self.package.pdf, self.mapping) == self.before_document
        ):
            return self.package.data, self._report(False)
        for change in self.changes:
            if change["operation"] == "delete_annotation":
                continue
            if change["operation"] == "create_annotation":
                candidates = [
                    loc
                    for loc, obj in final_catalog.entries
                    if str(obj.get("/NM", "")) == change["name"]
                ]
            else:
                old = change["before"]["locator"]
                target = next(
                    obj
                    for edit, _, obj in self.targets
                    if isinstance(edit, PdfAnnotationUpdate)
                    and edit.reference.locator.model_dump() == old
                )
                assert target is not None
                if target.is_indirect:
                    candidates = [
                        loc
                        for loc, obj in final_catalog.entries
                        if obj.is_indirect and obj.objgen == target.objgen
                    ]
                else:
                    updated_locator = dict(old)
                    updated_locator["annotation_index"] = surviving_slots[
                        old["page"]["page_index"], old["annotation_index"]
                    ]
                    candidates = [PdfAnnotationLocator.model_validate(updated_locator)]
            if len(candidates) != 1:
                raise ValueError("Cannot identify the resulting annotation uniquely")
            change["after_in_memory"] = final_catalog.record(candidates[0])
        data = checked_serialization(
            self.package.pdf, list(self.mapping.values()), self.package.pdf.pdf_version
        )
        self._restore_and_check()
        if _base_pixels(self.package.data) != _base_pixels(data):
            raise ValueError("PDF annotation edit changed underlying page pixels")
        for index in range(len(self.package.pdf.pages)):
            if index not in self.affected and render_fingerprint(
                self.package.data, index
            ) != render_fingerprint(data, index):
                raise ValueError("PDF annotation edit changed an untouched page")
        # Serialized object numbers can differ; return an authoritative new catalog.
        with NativePdfPackage(data) as final:
            result_catalog = AnnotationCatalog(final)
            for change in self.changes:
                if "after_in_memory" in change:
                    old = change.pop("after_in_memory")
                    page_index = old["locator"]["page"]["page_index"]
                    slot = old["locator"]["annotation_index"]
                    locator = next(
                        loc
                        for loc, _ in result_catalog.entries
                        if loc.page.page_index == page_index
                        and loc.annotation_index == slot
                    )
                    change["after"] = result_catalog.record(locator)
        return data, self._report(True)

    def _generated(
        self, page: pikepdf.Page, appearance: PdfAnnotationAppearance
    ) -> pikepdf.Object:
        data = appearance_pdf(page, appearance)
        with pikepdf.Pdf.open(io.BytesIO(data)) as generated:
            annotation = generated.pages[0].obj.Annots[0]
            for obj in (annotation, annotation.get("/Popup")):
                if obj is not None and "/P" in obj:
                    del obj.P
            return self.package.pdf.copy_foreign(annotation)

    def _update(
        self, page: pikepdf.Page, annotation: pikepdf.Object, edit: PdfAnnotationUpdate
    ) -> None:
        subtype = str(annotation.get("/Subtype", ""))
        if subtype not in COMMENT_KINDS:
            raise ValueError(
                "This annotation kind has no supported comment update contract"
            )
        appearance = edit.replace_appearance
        if appearance is not None:
            if subtype != "/" + appearance.kind:
                raise ValueError(
                    "Appearance replacement must keep the existing annotation kind"
                )
            if set(annotation.keys()) - KNOWN_KEYS or "/ExData" in annotation:
                raise ValueError(
                    "Unmodeled annotation appearance dependencies require review"
                )
            generated = self._generated(page, appearance)
            for key in APPEARANCE_KEYS:
                if key == "/RC" and subtype != "/FreeText":
                    continue
                if key in annotation:
                    del annotation[key]
                if key in generated:
                    annotation[key] = generated[key]
            if subtype == "/FreeText":
                annotation.Contents = generated.Contents
        if "contents" in edit.metadata.model_fields_set:
            contents = edit.metadata.contents
            old = annotation.get("/Contents")
            if not (isinstance(old, pikepdf.String) and str(old) == contents):
                if subtype == "/FreeText":
                    raise ValueError(
                        "FreeText contents require matching explicit appearance replacement"
                    )
                if "/RC" in annotation:
                    raise ValueError(
                        "Rich-text comment content requires a separate formatting-aware operation"
                    )
        _metadata(annotation, edit.metadata)

    def _restore_and_check(self) -> None:
        for annotation, fields in self.saved:
            for key in list(annotation.keys()):
                del annotation[key]
            for key, value in fields.items():
                annotation[key] = value
        for page, original_array, original_items in self.page_arrays:
            if original_array is None:
                if "/Annots" in page.obj:
                    del page.obj.Annots
            else:
                _replace_contents(original_array, original_items)
                page.obj.Annots = original_array
        if [
            page_graph(p, self.mapping) for p in self.package.pdf.pages
        ] != self.before_pages or document_graph(
            self.package.pdf, self.mapping
        ) != self.before_document:
            raise ValueError("PDF changed outside the explicit annotation edit plan")

    def _report(self, changed: bool) -> NativeEditResult:
        return NativeEditResult(
            changed_parts=["pdf:explicit-annotations"] if changed else [],
            preserved_parts=len(self.package.pdf.pages)
            - (len(self.affected) if changed else 0),
            changes=self.changes if changed else [],
            checks=[
                "revision_and_full_annotation_references",
                "annotation_dependencies",
                "inverse_native_graph_preservation",
                "serialized_graph_readback",
                "independent_512_pixel_base_content_and_untouched_pages",
            ]
            if changed
            else [
                "revision_and_full_annotation_references",
                "annotation_dependencies",
                "unchanged_native_graph_no_serialization",
            ],
            repairs=["canonicalized_equal_duplicate_stream_lengths"]
            if self.package.parser_checks and changed
            else [],
            review_required=ANNOTATION_REVIEW,
        )


def edit_annotations(
    data: bytes, request: PdfAnnotationsUpdate
) -> tuple[bytes, NativeEditResult]:
    with NativePdfPackage(data) as package:
        package.check_editable()
        return AnnotationMutation(package, request).run()
