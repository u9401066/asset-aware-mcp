"""Bounded OOXML package IO; unrelated member contents remain byte-identical."""

from __future__ import annotations

import copy
import io
import posixpath
import zipfile
from pathlib import PurePosixPath

from lxml import etree

from src.domain.native_assets import MAX_NATIVE_BYTES

SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
TYPE_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
MAX_PACKAGE_BYTES = 128 * 1024 * 1024
MAX_PART_BYTES = 32 * 1024 * 1024


def xml_bytes(root: etree._Element) -> bytes:
    return bytes(etree.tostring(root, encoding="UTF-8", xml_declaration=True))


def relationship_target(owner: str, target: str) -> str:
    if (
        "\\" in target
        or ":" in target
        or "\x00" in target
        or "?" in target
        or "#" in target
    ):
        raise ValueError("Unsupported OOXML relationship target")
    path = posixpath.normpath(
        target.lstrip("/")
        if target.startswith("/")
        else posixpath.join(posixpath.dirname(owner), target)
    )
    if path in {".", ".."} or path.startswith("../"):
        raise ValueError("OOXML relationship escapes the package")
    return path


def relationships_path(owner: str) -> str:
    if not owner:
        return "_rels/.rels"
    return posixpath.join(
        posixpath.dirname(owner), "_rels", posixpath.basename(owner) + ".rels"
    )


class NativeOOXMLPackage:
    def __init__(self, data: bytes):
        if len(data) > MAX_NATIVE_BYTES:
            raise ValueError("Native document exceeds byte limit")
        self.original = data
        self.parts: dict[str, bytes] = {}
        self.infos: list[zipfile.ZipInfo] = []
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                self.comment = archive.comment
                infos = archive.infolist()
                if len(infos) > 10_000:
                    raise ValueError("OOXML package exceeds member limit")
                total = 0
                for info in infos:
                    name = info.filename
                    path = PurePosixPath(name)
                    if (
                        not name
                        or path.is_absolute()
                        or ".." in path.parts
                        or "\\" in name
                        or ":" in name
                        or "\x00" in name
                        or str(path) != name.rstrip("/")
                        or name in self.parts
                    ):
                        raise ValueError("Ambiguous or unsafe OOXML member name")
                    if info.flag_bits & 1:
                        raise ValueError("Encrypted OOXML members are unsupported")
                    total += info.file_size
                    if info.file_size > MAX_PART_BYTES or total > MAX_PACKAGE_BYTES:
                        raise ValueError("OOXML package exceeds decompression limits")
                    with archive.open(info) as handle:
                        content = handle.read(MAX_PART_BYTES + 1)
                    if len(content) != info.file_size:
                        raise ValueError("OOXML member size mismatch")
                    self.parts[name] = content
                    self.infos.append(info)
        except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
            raise ValueError("Invalid or unsupported OOXML ZIP package") from exc
        self.xml("[Content_Types].xml")

    def xml(self, name: str) -> etree._Element:
        if name not in self.parts:
            raise ValueError(f"Missing OOXML part: {name}")
        try:
            root = etree.fromstring(
                self.parts[name],
                etree.XMLParser(
                    resolve_entities=False, no_network=True, huge_tree=False
                ),
            )
        except etree.XMLSyntaxError as exc:
            raise ValueError(f"Invalid OOXML XML: {name}") from exc
        if root.getroottree().docinfo.doctype:
            raise ValueError("OOXML parts must not contain DTDs")
        return root

    def relationships(self, owner: str) -> dict[str, tuple[str, str]]:
        root = self.xml(relationships_path(owner))
        if root.tag != f"{{{REL_NS}}}Relationships":
            raise ValueError("Unsupported relationship namespace")
        result = {}
        for item in root:
            identity = item.get("Id")
            target = item.get("Target")
            kind = item.get("Type", "")
            if not identity or not target or identity in result:
                raise ValueError("Invalid or duplicate OOXML relationship")
            if item.get("TargetMode") == "External":
                result[identity] = (kind, "")
            else:
                result[identity] = (kind, relationship_target(owner, target))
        return result

    def workbook_path(self) -> str:
        matches = [
            target
            for kind, target in self.relationships("").values()
            if kind == f"{DOC_REL_NS}/officeDocument"
        ]
        if len(matches) != 1 or not matches[0]:
            raise ValueError("Expected one internal workbook relationship")
        path = matches[0]
        if self.xml(path).tag != f"{{{SHEET_NS}}}workbook":
            raise ValueError("Only transitional SpreadsheetML workbooks are supported")
        return path

    def replace(
        self, replacements: dict[str, bytes], removed: set[str] | None = None
    ) -> bytes:
        removed = removed or set()
        if not replacements and not removed:
            return self.original
        if any(name.startswith("_xmlsignatures/") for name in self.parts):
            raise ValueError(
                "Digitally signed workbooks require a signature-aware edit workflow"
            )
        if set(replacements) - set(self.parts) or removed - set(self.parts):
            raise ValueError("Replacement references an unknown OOXML part")
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.comment = self.comment
            for info in self.infos:
                if info.filename not in removed:
                    archive.writestr(
                        copy.copy(info),
                        replacements.get(info.filename, self.parts[info.filename]),
                    )
        result = output.getvalue()
        checked = NativeOOXMLPackage(result)
        if set(checked.parts) != set(self.parts) - removed:
            raise ValueError("OOXML inventory changed outside the edit plan")
        for name, content in self.parts.items():
            if name not in removed and checked.parts[name] != replacements.get(
                name, content
            ):
                raise ValueError(f"OOXML preservation check failed: {name}")
        return result
