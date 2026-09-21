"""Bounded OpenDocument package IO with checked, explicit member replacements."""

from __future__ import annotations

import copy
import io
import stat
import struct
import zipfile
import zlib
from pathlib import PurePosixPath

from lxml import etree

from src.domain.native_asset_models import MAX_NATIVE_BYTES

ODF = "urn:oasis:names:tc:opendocument:xmlns:"
NS = {
    name: ODF + name + ":1.0"
    for name in ("office", "table", "text", "style", "manifest", "draw", "config")
}
NS["of"] = ODF + "of:1.2"
NS["draw"] = ODF + "drawing:1.0"
ODS_MIME = "application/vnd.oasis.opendocument.spreadsheet"
MAX_PART_BYTES = 32 * 1024 * 1024
MAX_PACKAGE_BYTES = 128 * 1024 * 1024


def q(prefix: str, name: str) -> str:
    return f"{{{NS[prefix]}}}{name}"


def xml_bytes(root: etree._Element) -> bytes:
    return bytes(etree.tostring(root, encoding="UTF-8", xml_declaration=True))


def safe_member(name: str) -> None:
    path = PurePosixPath(name)
    if (
        not name
        or path.is_absolute()
        or ".." in path.parts
        or "\\" in name
        or ":" in name
        or "\x00" in name
        or str(path) != name.rstrip("/")
    ):
        raise ValueError("Ambiguous or unsafe ODF member name")


class NativeODFPackage:
    def __init__(self, data: bytes):
        if len(data) > MAX_NATIVE_BYTES:
            raise ValueError("Native ODF document exceeds byte limit")
        self.original = data
        self.parts: dict[str, bytes] = {}
        self.infos: list[zipfile.ZipInfo] = []
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                self.comment = archive.comment
                infos = archive.infolist()
                if len(infos) > 10_000:
                    raise ValueError("ODF package exceeds member limit")
                total = 0
                for info in infos:
                    safe_member(info.orig_filename)
                    if info.filename in self.parts:
                        raise ValueError("Duplicate ODF member name")
                    if info.flag_bits & 1 or stat.S_ISLNK(info.external_attr >> 16):
                        raise ValueError(
                            "Encrypted or symlink ODF ZIP members are unsupported"
                        )
                    if info.compress_type not in {
                        zipfile.ZIP_STORED,
                        zipfile.ZIP_DEFLATED,
                    }:
                        raise ValueError("Unsupported ODF compression method")
                    total += info.file_size
                    if info.file_size > MAX_PART_BYTES or total > MAX_PACKAGE_BYTES:
                        raise ValueError("ODF package exceeds decompression limits")
                    with archive.open(info) as handle:
                        content = handle.read(MAX_PART_BYTES + 1)
                    if len(content) != info.file_size:
                        raise ValueError("ODF member size mismatch")
                    self.parts[info.filename] = content
                    self.infos.append(info)
        except (
            zipfile.BadZipFile,
            RuntimeError,
            NotImplementedError,
            zlib.error,
            EOFError,
        ) as exc:
            raise ValueError("Invalid or unsupported ODF ZIP package") from exc
        self._manifest()

    def xml(self, name: str) -> etree._Element:
        if name not in self.parts:
            raise ValueError(f"Missing ODF part: {name}")
        try:
            root = etree.fromstring(
                self.parts[name],
                etree.XMLParser(
                    resolve_entities=False, no_network=True, huge_tree=False
                ),
            )
        except etree.XMLSyntaxError as exc:
            raise ValueError(f"Invalid ODF XML: {name}") from exc
        if root.getroottree().docinfo.doctype:
            raise ValueError("ODF parts must not contain DTDs")
        if sum(1 for _ in root.iter()) > 200_000:
            raise ValueError("ODF XML exceeds node budget")
        return root

    def _manifest(self) -> None:
        root = self.xml("META-INF/manifest.xml")
        if root.tag != q("manifest", "manifest"):
            raise ValueError("Invalid ODF manifest namespace")
        if any(
            node.tag
            in {q("manifest", "encryption-data"), q("manifest", "encrypted-key")}
            for node in root.iter()
        ):
            raise ValueError("Encrypted ODF packages require a decryption workflow")
        entries: dict[str, str] = {}
        for item in root.findall(q("manifest", "file-entry")):
            name = item.get(q("manifest", "full-path"), "")
            if name != "/":
                safe_member(name)
            if name in entries:
                raise ValueError("Duplicate ODF manifest entry")
            entries[name] = item.get(q("manifest", "media-type"), "")
            if name != "/" and not name.endswith("/") and name not in self.parts:
                raise ValueError("ODF manifest references a missing member")
        mime = self.parts.get("mimetype")
        if mime != ODS_MIME.encode("ascii") or entries.get("/") != ODS_MIME:
            raise ValueError("ODS mimetype and root manifest must agree")
        first = self.infos[0]
        if (
            first.filename != "mimetype"
            or first.header_offset != 0
            or first.compress_type != zipfile.ZIP_STORED
            or first.extra
            or self.original[:4] != b"PK\x03\x04"
            or struct.unpack_from("<H", self.original, 28)[0] != 0
        ):
            raise ValueError(
                "ODF mimetype must be first, uncompressed and without extra fields"
            )
        for name in self.parts:
            if (
                name != "mimetype"
                and not name.startswith("META-INF/")
                and not name.endswith("/")
                and name not in entries
            ):
                raise ValueError("ODF member is absent from the manifest")
        self.manifest = entries
        self.signed = any(
            name.startswith("META-INF/") and "signatures" in name.lower()
            for name in self.parts
        )

    def replace(self, replacements: dict[str, bytes]) -> bytes:
        if not replacements:
            return self.original
        if self.signed:
            raise ValueError("Signed ODF packages require a signature-aware workflow")
        if set(replacements) - set(self.parts):
            raise ValueError("Replacement references an unknown ODF member")
        if any(len(value) > MAX_PART_BYTES for value in replacements.values()):
            raise ValueError("ODF replacement exceeds member byte budget")
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.comment = self.comment
            for info in self.infos:
                archive.writestr(
                    copy.copy(info),
                    replacements.get(info.filename, self.parts[info.filename]),
                )
        result = output.getvalue()
        checked = NativeODFPackage(result)
        if set(checked.parts) != set(self.parts):
            raise ValueError("ODF package inventory changed outside replacements")
        for name, content in self.parts.items():
            if checked.parts[name] != replacements.get(name, content):
                raise ValueError(f"ODF member preservation failed: {name}")
        return result
