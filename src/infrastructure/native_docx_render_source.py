"""Bounded native Word inputs and known resource-loading dependencies for previews."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from src.infrastructure.native_docx_workspace import WORD_NS, checked_docx
from src.infrastructure.native_ooxml import DOC_REL_NS

if TYPE_CHECKING:
    from lxml import etree

W = "{" + WORD_NS + "}"
VML = "{urn:schemas-microsoft-com:vml}"
RESOURCE_FIELDS = {
    "INCLUDETEXT",
    "INCLUDEPICTURE",
    "DDE",
    "DDEAUTO",
    "LINK",
    "DATABASE",
    "RD",
}


def check_instruction(text: str) -> None:
    match = re.match(r"\s*([A-Za-z]+)", text)
    if match and match[1].upper() in RESOURCE_FIELDS:
        raise ValueError(
            "Resource-loading DOCX fields require a resource-aware preview"
        )


def check_fields(root: etree._Element) -> None:
    stack: list[list[str] | None] = []
    for node in root.iter():
        if node.tag == W + "fldSimple":
            check_instruction(node.get(W + "instr", ""))
        elif node.tag == W + "fldChar":
            kind = node.get(W + "fldCharType")
            if kind == "begin":
                stack.append([])
            elif kind in {"separate", "end"} and stack:
                parts = stack.pop()
                if parts is not None:
                    check_instruction("".join(parts))
                if kind == "separate":
                    if parts is None:
                        raise ValueError("DOCX preview field boundaries are ambiguous")
                    stack.append(None)
            else:
                raise ValueError("DOCX preview field boundaries are ambiguous")
        elif node.tag == W + "instrText":
            if not stack or stack[-1] is None:
                raise ValueError("DOCX preview has unbound field instructions")
            stack[-1].append(node.text or "")
    if stack:
        raise ValueError("DOCX preview has unclosed field instructions")


def rendering_source(data: bytes) -> None:
    package = checked_docx(data)
    for name in package.parts:
        if name.endswith(".rels"):
            path = PurePosixPath(name)
            if name == "_rels/.rels":
                owner = ""
            elif path.parent.name == "_rels":
                owner = str(path.parent.parent / path.name[:-5])
            else:
                raise ValueError("DOCX preview has ambiguous relationship parts")
            for item in package.xml(name):
                kind = item.get("Type", "")
                if (
                    item.get("TargetMode") == "External"
                    and kind != f"{DOC_REL_NS}/hyperlink"
                ):
                    raise ValueError(
                        "Linked external content is unsupported in DOCX previews"
                    )
                if kind.rsplit("/", 1)[-1] in {"oleObject", "package", "aFChunk"}:
                    raise ValueError(
                        "Embedded OLE/package/chunk content needs a resource-aware preview"
                    )
            for _, target in package.relationships(owner).values():
                if target and target not in package.parts:
                    raise ValueError("DOCX preview references a missing internal part")
        elif name.lower().endswith((".svg", ".svgz")):
            raise ValueError("SVG media requires a resource-aware rendering workflow")
        elif name.endswith((".xml", ".vml")):
            root = package.xml(name)
            check_fields(root)
            for node in root.iter():
                if node.tag in {
                    W + "altChunk",
                    W + "subDoc",
                    "{urn:schemas-microsoft-com:office:office}OLEObject",
                }:
                    raise ValueError(
                        "DOCX alternative/embedded content needs a resource-aware preview"
                    )
                if (
                    isinstance(node.tag, str)
                    and node.tag.startswith(VML)
                    and node.get("src")
                ):
                    raise ValueError(
                        "Linked VML content is unsupported in DOCX previews"
                    )
