"""Plan additive media/relationships without mutating shared image parts."""

from __future__ import annotations

import hashlib
import posixpath
from copy import deepcopy
from typing import TYPE_CHECKING, Any

from lxml import etree

from src.infrastructure.native_ooxml import (
    DOC_REL_NS,
    REL_NS,
    TYPE_NS,
    relationships_path,
    xml_bytes,
)
from src.infrastructure.native_ooxml_additions import extend_package

if TYPE_CHECKING:
    from src.infrastructure.native_pptx_package import NativePptxPackage


class PictureParts:
    def __init__(self, package: NativePptxPackage):
        self.package = package
        self.roots: dict[str, etree._Element] = {}
        self.additions: dict[str, bytes] = {}
        self.appended: dict[str, list[etree._Element]] = {}
        self.media: dict[str, str] = {}

    def _root(self, path: str) -> etree._Element:
        if path not in self.roots:
            self.roots[path] = (
                self.package.xml(path)
                if path in self.package.parts
                else etree.Element(f"{{{REL_NS}}}Relationships", nsmap={None: REL_NS})
            )
        expected = (
            f"{{{TYPE_NS}}}Types"
            if path == "[Content_Types].xml"
            else f"{{{REL_NS}}}Relationships"
        )
        if self.roots[path].tag != expected:
            raise ValueError("Unexpected picture relationship/content-type root")
        return self.roots[path]

    def _append(self, path: str, node: etree._Element) -> None:
        self._root(path).append(node)
        self.appended.setdefault(path, []).append(node)

    def embed(
        self, owner: str, data: bytes, metadata: dict[str, Any]
    ) -> tuple[str, str]:
        digest = hashlib.sha256(data).hexdigest()
        if digest not in self.media:
            stem = f"ppt/media/asset-{digest}"
            path = f"{stem}.{metadata['extension']}"
            counter = 0
            while path in self.package.parts or path in self.additions:
                counter += 1
                path = f"{stem}-{counter}.{metadata['extension']}"
            self.additions[path] = data
            self.media[digest] = path
            self._append(
                "[Content_Types].xml",
                etree.Element(
                    f"{{{TYPE_NS}}}Override",
                    PartName="/" + path,
                    ContentType=metadata["media_type"],
                ),
            )
        path = self.media[digest]
        relation_path = relationships_path(owner)
        if relation_path in self.package.parts:
            self.package.relationships(
                owner
            )  # Validate existing relationship identities.
        root = self._root(relation_path)
        used = {node.get("Id") for node in root}
        used.update(
            value
            for node in self.package.roots[owner].iter()
            for key, value in node.attrib.items()
            if key.startswith("{" + DOC_REL_NS + "}")
        )
        index = 1
        while f"rId{index}" in used:
            index += 1
        identity = f"rId{index}"
        self._append(
            relation_path,
            etree.Element(
                f"{{{REL_NS}}}Relationship",
                Id=identity,
                Type=f"{DOC_REL_NS}/image",
                Target=posixpath.relpath(path, posixpath.dirname(owner)),
            ),
        )
        return identity, path

    def serialize(self, changed_owners: set[str]) -> tuple[bytes, list[str]]:
        replacements = {p: xml_bytes(self.package.roots[p]) for p in changed_owners}
        for path, root in self.roots.items():
            restored = deepcopy(root)
            count = len(self.appended[path])
            for _ in range(count):
                restored.remove(restored[-1])
            if path in self.package.parts:
                if etree.tostring(restored, method="c14n") != etree.tostring(
                    self.package.xml(path), method="c14n"
                ):
                    raise ValueError(
                        "Picture insertion changed existing relationship/content-type XML"
                    )
                replacements[path] = xml_bytes(root)
            else:
                if len(restored) or restored.attrib or restored.text:
                    raise ValueError("Unexpected new relationship content")
                self.additions[path] = xml_bytes(root)
        return extend_package(self.package, replacements, self.additions), sorted(
            set(replacements) | set(self.additions)
        )
