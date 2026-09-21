"""Complete native annotation records, including unknown kinds and dependencies."""

from __future__ import annotations

from typing import Any

import pikepdf

from src.domain.native_pdf_annotations import PdfAnnotationLocator
from src.infrastructure.native_pdf_annotation_geometry import (
    display_geometry,
    display_transforms,
)
from src.infrastructure.native_pdf_graph import PdfObjectGraph, graph_digest
from src.infrastructure.native_pdf_package import NativePdfPackage

METADATA_KEYS = {
    "contents": "/Contents",
    "author": "/T",
    "subject": "/Subj",
    "modified": "/M",
}


class AnnotationCatalog:
    def __init__(self, package: NativePdfPackage):
        self.package = package
        self.entries: list[tuple[PdfAnnotationLocator, pikepdf.Object]] = []
        for page_index, page in enumerate(package.pdf.pages):
            annotations = page.obj.get("/Annots", pikepdf.Array())
            if not isinstance(annotations, pikepdf.Array):
                raise ValueError("PDF annotation inventory is not an array")
            for index, annotation in enumerate(annotations):
                if not isinstance(annotation, pikepdf.Dictionary):
                    raise ValueError(
                        "PDF annotation inventory contains a non-dictionary"
                    )
                self.entries.append(
                    (
                        PdfAnnotationLocator.model_validate(
                            {
                                "page": {
                                    "page_index": page_index,
                                    "object_id": page.obj.objgen[0],
                                    "generation": page.obj.objgen[1],
                                },
                                "annotation_index": index,
                                "object_id": annotation.objgen[0],
                                "generation": annotation.objgen[1],
                            }
                        ),
                        annotation,
                    )
                )
                if len(self.entries) > 20_000:
                    raise ValueError("PDF exceeds the annotation catalog limit")
        self.transforms = display_transforms(
            package.data, {loc.page.page_index for loc, _ in self.entries}
        )

    def locate(self, locator: PdfAnnotationLocator) -> pikepdf.Object:
        page = self.package.locate(locator.page)
        annotations: Any = page.obj.get("/Annots", [])
        if locator.annotation_index >= len(annotations):
            raise ValueError("PDF annotation index does not resolve")
        annotation: pikepdf.Object = annotations[locator.annotation_index]
        if annotation.objgen != (locator.object_id, locator.generation):
            raise ValueError("PDF annotation object locator does not match revision")
        return annotation

    def record(self, locator: PdfAnnotationLocator) -> dict[str, Any]:
        annotation = self.locate(locator)
        rectangle = annotation.get("/Rect")
        return {
            "schema_version": "native-pdf-annotation-v1",
            "locator": locator.model_dump(),
            "subtype": str(annotation.get("/Subtype", "")),
            "name": self._string(annotation.get("/NM")),
            **{
                name: self._string(annotation.get(key))
                for name, key in METADATA_KEYS.items()
            },
            "rectangle": [float(v) for v in rectangle]
            if isinstance(rectangle, pikepdf.Array)
            else None,
            "coordinate_system": "native PDF default user space; bottom-left, before page rotation; not displayed fractions",
            "display_geometry": display_geometry(
                annotation, self.transforms[locator.page.page_index]
            ),
            "rich_text": self._string(annotation.get("/RC")),
            "relations": {
                key[1:]: [
                    other.model_dump()
                    for other, obj in self.entries
                    if isinstance(annotation.get(key), pikepdf.Dictionary)
                    and obj.is_indirect
                    and obj.objgen == annotation[key].objgen
                ]
                for key in ("/Popup", "/Parent", "/IRT")
                if key in annotation
            },
            "unresolved_relations": [
                key[1:]
                for key in ("/Popup", "/Parent", "/IRT")
                if key in annotation
                and (
                    not isinstance(annotation[key], pikepdf.Dictionary)
                    or not any(
                        obj.is_indirect and obj.objgen == annotation[key].objgen
                        for _, obj in self.entries
                    )
                )
            ],
            "native_graph": PdfObjectGraph(self.package.page_map()).describe(
                annotation
            ),
            "text_scope": "Annotation Contents is a comment or FreeText text, not extracted text beneath a highlight",
        }

    @staticmethod
    def _string(value: Any) -> str | None:
        return str(value) if isinstance(value, pikepdf.String) else None

    def inspect(self) -> dict[str, Any]:
        records = [self.record(locator) for locator, _ in self.entries]
        return {
            "schema_version": "native-pdf-annotation-catalog-v1",
            "annotations": [
                {
                    "locator": r["locator"],
                    "subtype": r["subtype"],
                    "name": r["name"],
                    "record_sha256": graph_digest(r),
                    "relations": r["relations"],
                }
                for r in records
            ],
            "annotation_count": len(records),
            "parser_checks": self.package.parser_checks,
        }


def inspect_annotations(data: bytes) -> dict[str, Any]:
    with NativePdfPackage(data) as package:
        return AnnotationCatalog(package).inspect()


def read_annotation(data: bytes, locator: PdfAnnotationLocator) -> dict[str, Any]:
    with NativePdfPackage(data) as package:
        return AnnotationCatalog(package).record(locator)


def decompose_annotations(data: bytes) -> list[dict[str, Any]]:
    with NativePdfPackage(data) as package:
        catalog = AnnotationCatalog(package)
        return [catalog.record(locator) for locator, _ in catalog.entries]
