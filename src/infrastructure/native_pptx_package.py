"""Presentation part/slide/shape identity resolved from checked OOXML relationships."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain.native_pptx import MAX_PPTX_COMPONENTS
from src.infrastructure.native_ooxml import (
    DOC_REL_NS,
    REL_NS,
    TYPE_NS,
    NativeOOXMLPackage,
    relationships_path,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from lxml import etree

    from src.domain.native_pptx import NativePptxShapeLocator

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS = {"p": P_NS, "a": A_NS, "r": DOC_REL_NS}
PPTX_MAIN_TYPE = (
    "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"
)
SHAPE_TAGS = {
    f"{{{P_NS}}}{name}" for name in ("sp", "pic", "graphicFrame", "grpSp", "cxnSp")
}


def native_id(value: str) -> str:
    if (
        not value.isascii()
        or not value.isdigit()
        or len(value) > 10
        or int(value) > 4294967295
    ):
        raise ValueError("Invalid native presentation identity")
    return str(int(value))


def shape_identity(shape: etree._Element) -> etree._Element:
    candidates = shape.xpath("./*/p:cNvPr", namespaces=NS)
    if len(candidates) != 1:
        raise ValueError("Presentation shape lacks an unambiguous native identity")
    return candidates[0]


class NativePptxPackage(NativeOOXMLPackage):
    def __init__(self, data: bytes):
        super().__init__(data)
        targets = [
            target
            for kind, target in self.relationships("").values()
            if kind == f"{DOC_REL_NS}/officeDocument"
        ]
        if len(targets) != 1 or not targets[0]:
            raise ValueError("Expected one internal presentation relationship")
        self.main_part = targets[0]
        self.presentation = self.xml(self.main_part)
        if self.presentation.tag != f"{{{P_NS}}}presentation":
            raise ValueError("Only transitional PresentationML is supported")
        types = self.xml("[Content_Types].xml")
        matches = [
            item.get("ContentType")
            for item in types
            if item.tag == f"{{{TYPE_NS}}}Override"
            and item.get("PartName") == "/" + self.main_part
        ]
        if matches != [PPTX_MAIN_TYPE]:
            raise ValueError("Expected a PPTX presentation main content type")
        self.slides = self._slides()
        self.roots: dict[str, etree._Element] = {}
        self.component_count = 0

    def _slides(self) -> list[dict[str, str]]:
        rels = self.relationships(self.main_part)
        slides = []
        ids: set[str] = set()
        parts: set[str] = set()
        for item in self.presentation.findall("p:sldIdLst/p:sldId", NS):
            identity = native_id(item.get("id", ""))
            kind, target = rels.get(item.get(f"{{{DOC_REL_NS}}}id", ""), ("", ""))
            if (
                not identity.isascii()
                or not identity.isdigit()
                or int(identity) < 1
                or len(identity) > 10
                or identity.startswith("0")
                or identity in ids
                or target in parts
                or not target
                or kind != f"{DOC_REL_NS}/slide"
            ):
                raise ValueError(
                    "Invalid, missing or duplicate presentation slide identity"
                )
            ids.add(identity)
            parts.add(target)
            slides.append({"slide_id": identity, "part": target})
        if len(slides) > MAX_PPTX_COMPONENTS:
            raise ValueError("Presentation exceeds slide limit")
        return slides

    def slide_regions(self, slide: dict[str, str]) -> list[tuple[str, str]]:
        result = [("slide", slide["part"])]
        if relationships_path(slide["part"]) in self.parts:
            notes = [
                target
                for kind, target in self.relationships(slide["part"]).values()
                if kind == f"{DOC_REL_NS}/notesSlide"
            ]
            if len(notes) > 1 or (notes and not notes[0]):
                raise ValueError("Ambiguous or external notes slide relationship")
            if notes:
                result.append(("notes", notes[0]))
        return result

    def shape_root(self, part: str, region: str) -> etree._Element:
        if part not in self.roots:
            root = self.xml(part)
            expected = "sld" if region == "slide" else "notes"
            if root.tag != f"{{{P_NS}}}{expected}":
                raise ValueError("Presentation part has an unexpected root")
            ids = [
                native_id(item.get("id", "")) for item in root.findall(".//p:cNvPr", NS)
            ]
            if len(ids) != len(set(ids)):
                raise ValueError("Invalid or duplicate presentation shape identity")
            self.component_count += len(ids)
            if self.component_count > MAX_PPTX_COMPONENTS:
                raise ValueError("Presentation exceeds shape limit")
            self.roots[part] = root
        expected = "sld" if region == "slide" else "notes"
        if self.roots[part].tag != f"{{{P_NS}}}{expected}":
            raise ValueError("Presentation part has an unexpected root")
        return self.roots[part]

    def shapes(self) -> Iterator[tuple[dict[str, str], etree._Element, list[str]]]:
        for slide in self.slides:
            for region, part in self.slide_regions(slide):
                root = self.shape_root(part, region)
                tree = root.find("p:cSld/p:spTree", NS)
                if tree is None:
                    raise ValueError("Missing presentation shape tree")
                for shape in self._shape_tree(tree):
                    parents = [
                        native_id(shape_identity(parent).get("id", ""))
                        for parent in shape.iterancestors()
                        if parent.tag == f"{{{P_NS}}}grpSp"
                    ]
                    locator = {
                        "slide_id": slide["slide_id"],
                        "part": part,
                        "region": region,
                        "shape_id": native_id(shape_identity(shape).get("id", "")),
                    }
                    yield locator, shape, list(reversed(parents))

    def _shape_tree(self, tree: etree._Element) -> Iterator[etree._Element]:
        for child in tree:
            if child.tag in SHAPE_TAGS:
                yield child
                if child.tag == f"{{{P_NS}}}grpSp":
                    yield from self._shape_tree(child)

    def locate(self, locator: NativePptxShapeLocator) -> etree._Element:
        target = locator.model_dump(include={"slide_id", "part", "region", "shape_id"})
        for candidate, shape, _ in self.shapes():
            if candidate == target:
                return shape
        raise ValueError("Presentation shape locator does not resolve in this revision")

    def check_editable(self) -> None:
        if self.presentation.find(".//p:modifyVerifier", NS) is not None:
            raise ValueError(
                "Protected presentations require a protection-aware workflow"
            )
        for name in self.parts:
            if name.startswith("_xmlsignatures/"):
                raise ValueError(
                    "Digitally signed presentations cannot use scoped text edits"
                )
            if name.endswith(".rels"):
                for relation in self.xml(name):
                    if relation.get("Type", "").startswith(
                        f"{REL_NS}/digital-signature/"
                    ):
                        raise ValueError(
                            "Digitally signed presentations cannot use scoped text edits"
                        )
