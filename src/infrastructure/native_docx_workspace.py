"""Private DFM workspaces with bounded DOCX input and package preservation checks."""

from __future__ import annotations

import hashlib
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from src.domain.native_assets import MAX_NATIVE_BYTES, NativeEditResult
from src.infrastructure.file_storage import FileStorage
from src.infrastructure.native_file_io import _read_file
from src.infrastructure.native_ooxml import (
    DOC_REL_NS,
    TYPE_NS,
    NativeOOXMLPackage,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from src.domain.native_docx import NativeDocxWorkspace
    from src.domain.repositories import DocumentRepository

WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
MAIN_PART = "word/document.xml"
MAIN_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
)


def checked_docx(data: bytes, *, for_edit: bool = False) -> NativeOOXMLPackage:
    package = NativeOOXMLPackage(data)
    main = [
        target
        for kind, target in package.relationships("").values()
        if kind == f"{DOC_REL_NS}/officeDocument"
    ]
    if main != [MAIN_PART] or package.xml(MAIN_PART).tag != f"{{{WORD_NS}}}document":
        raise ValueError("Only transitional DOCX with word/document.xml is supported")
    types = package.xml("[Content_Types].xml")
    declared = [
        item.get("ContentType")
        for item in types.findall(f"{{{TYPE_NS}}}Override")
        if item.get("PartName") == "/" + MAIN_PART
    ]
    if declared != [MAIN_TYPE]:
        raise ValueError(
            "Expected DOCX content type; DOCM and templates are unsupported"
        )
    for name in package.parts:
        if name.endswith((".xml", ".rels")):
            package.xml(name)
    if for_edit:
        _check_editable(package)
    return package


def _check_editable(package: NativeOOXMLPackage) -> None:
    signed = any(name.startswith("_xmlsignatures/") for name in package.parts)
    signed |= any(
        ".digital-signature-" in item.get("ContentType", "")
        for item in package.xml("[Content_Types].xml")
    )
    signed |= any(
        "/digital-signature/" in item.get("Type", "")
        for name in package.parts
        if name.endswith(".rels")
        for item in package.xml(name)
    )
    if signed:
        raise ValueError(
            "Digitally signed DOCX requires a signature-aware edit workflow"
        )
    settings_parts = {"word/settings.xml"} & package.parts.keys()
    if "word/_rels/document.xml.rels" in package.parts:
        settings_parts.update(
            target
            for kind, target in package.relationships(MAIN_PART).values()
            if kind == f"{DOC_REL_NS}/settings"
        )
    for part in settings_parts:
        settings = package.xml(part)
        if settings.find(f"{{{WORD_NS}}}documentProtection") is not None:
            raise ValueError(
                "Protected DOCX requires an explicit supported editing workflow"
            )


class _Workspace:
    def __init__(self, root: Path, package: NativeOOXMLPackage):
        self.root = root
        self.package = package
        self.repository: DocumentRepository = FileStorage(root / "data")
        source = root / "source.docx"
        source.write_bytes(package.original)
        self.source_path = str(source)

    def read_result(
        self, path: str, changed_blocks: list[str], track_changes: bool
    ) -> tuple[bytes, NativeEditResult]:
        _check_editable(self.package)
        target = Path(path)
        if target.is_symlink() or not target.resolve().is_relative_to(self.root):
            raise ValueError("DOCX result must remain inside its private workspace")
        data, _ = _read_file(target, MAX_NATIVE_BYTES)
        after = checked_docx(data)
        before = self.package.parts
        if after.parts.keys() != before.keys():
            raise ValueError("DFM save changed the DOCX member inventory")
        changed = sorted(name for name in before if before[name] != after.parts[name])
        allowed = {MAIN_PART, "word/settings.xml"} if track_changes else {MAIN_PART}
        if set(changed) - allowed:
            raise ValueError("DFM save modified unrelated DOCX parts")
        if not changed_blocks and changed:
            raise ValueError("DFM save changed a DOCX with no intended block edits")
        result = NativeEditResult(
            changed_parts=changed,
            preserved_parts=len(before) - len(changed),
            changes=[{"block_id": block} for block in changed_blocks]
            + [
                {
                    "part": name,
                    "before_sha256": hashlib.sha256(before[name]).hexdigest(),
                    "after_sha256": hashlib.sha256(after.parts[name]).hexdigest(),
                }
                for name in changed
            ],
            checks=[
                "dfm_session_binding",
                "dfm_pre_save",
                "unedited_blocks",
                "dfm_post_save",
                "package_inventory",
                "unrelated_part_bytes",
            ],
            review_required=[
                "semantic_accuracy",
                "rendered_layout",
                "fields_and_revisions",
            ],
        )
        return data, result


class FileNativeDocxWorkspaces:
    @contextmanager
    def open(
        self, data: bytes, *, for_edit: bool = False
    ) -> Iterator[NativeDocxWorkspace]:
        package = checked_docx(data, for_edit=for_edit)
        with TemporaryDirectory(prefix="asset-aware-native-docx-") as directory:
            yield _Workspace(Path(directory).resolve(), package)
