"""Inspect native ODS resources before converting an unchanged private copy."""

from __future__ import annotations

import base64
import io
import posixpath
import struct
from typing import Any
from urllib.parse import unquote, urlsplit

from lxml import etree
from PIL import Image, UnidentifiedImageError

from src.infrastructure.native_odf_package import NS, ODF, q
from src.infrastructure.native_ods import NativeODS
from src.infrastructure.native_ods_render_formula import check_formula, check_reference

XLINK = "http://www.w3.org/1999/xlink"
XML_BASE = "{http://www.w3.org/XML/1998/namespace}base"
CHART_MIME = "application/vnd.oasis.opendocument.chart"
METAFILE_MIME = "application/x-openoffice-gdimetafile"
BLOCKED_ELEMENTS = (
    {q("draw", name) for name in ("applet", "plugin", "floating-frame", "object-ole")}
    | {
        q("table", name)
        for name in (
            "dde-link",
            "dde-links",
            "table-source",
            "cell-range-source",
            "database-source-sql",
            "database-source-table",
            "database-source-query",
        )
    }
    | {q("office", "script")}
)


def _image(data: bytes) -> None:
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format not in {
                "PNG",
                "JPEG",
                "GIF",
                "TIFF",
                "BMP",
                "WEBP",
                "AVIF",
            }:
                raise ValueError("ODS preview image needs a supported raster format")
            if image.width * image.height > 40_000_000:
                raise ValueError("ODS preview image exceeds its pixel budget")
            image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Invalid ODS preview raster resource") from exc


def _metafile(data: bytes) -> None:
    """Bound Calc's native chart fallback records; Calc decodes their drawing data.

    Record layout: LibreOffice vcl/source/filter/svm/SvmReader.cxx. This checks
    framing and the supported drawing subset, not graphic fidelity or a sandbox.
    """
    if len(data) < 61 or data[:8] != b"VCLMTF\x01\x00":
        raise ValueError("Invalid ODS chart metafile header")
    header_size = struct.unpack_from("<I", data, 8)[0]
    offset = 12 + header_size
    if header_size != 49 or offset > len(data):
        raise ValueError("Unsupported ODS chart metafile header")
    count = struct.unpack_from("<I", data, offset - 4)[0]
    if not 0 < count <= 100_000:
        raise ValueError("ODS chart metafile exceeds its record budget")
    comments = {
        b"XPATHSTROKE_SEQ_BEGIN",
        b"XPATHSTROKE_SEQ_END",
        b"XPATHFILL_SEQ_BEGIN",
        b"XPATHFILL_SEQ_END",
        b"XGRAD_SEQ_BEGIN",
        b"XGRAD_SEQ_END",
        b"XTEXT_PAINTSHAPE_BEGIN",
        b"XTEXT_PAINTSHAPE_END",
        b"XTEXT_EOC",
        b"XTEXT_EOW",
        b"XTEXT_EOL",
        b"XTEXT_EOP",
    }
    for _ in range(count):
        if offset + 8 > len(data):
            raise ValueError("Truncated ODS chart metafile record")
        action, version, size = struct.unpack_from("<HHI", data, offset)
        start, end = offset + 8, offset + 8 + size
        if end > len(data) or not version:
            raise ValueError("Invalid ODS chart metafile record size/version")
        if action == 512:
            if size < 10:
                raise ValueError("Truncated ODS chart metafile comment")
            length = struct.unpack_from("<H", data, start)[0]
            if (
                length + 10 > size
                or data[start + 2 : start + 2 + length] not in comments
            ):
                raise ValueError("ODS chart metafile comment needs a dedicated preview")
            payload = struct.unpack_from("<I", data, start + length + 6)[0]
            if length + 10 + payload != size:
                raise ValueError("Invalid ODS chart metafile comment size")
        elif not 100 <= action <= 151 or action in {143, 147}:
            raise ValueError("Nested or foreign ODS metafile needs a dedicated preview")
        offset = end
    if offset != len(data):
        raise ValueError("ODS chart metafile has trailing records")


def _resource(
    book: NativeODS,
    owner: str,
    node: etree._Element,
    href: str,
    inspected: set[tuple[str, str]],
) -> None:
    if node.tag in {q("text", "a"), q("draw", "a")}:
        return  # Authored hyperlinks are not renderer resource loads.
    if href.startswith("#"):
        return  # Same-document object reference; never a file/URL resource.
    uri = urlsplit(href)
    if uri.scheme or uri.netloc or uri.query or uri.fragment:
        raise ValueError("Linked ODS resources need a resource-aware preview")
    path = unquote(uri.path)
    if not path or path.startswith("/") or "\\" in path or "\x00" in path:
        raise ValueError("Ambiguous ODS preview resource path")
    target = posixpath.normpath(posixpath.join(posixpath.dirname(owner), path))
    if target == ".." or target.startswith("../"):
        raise ValueError("ODS preview resource escapes its package")
    if node.tag == f"{{{ODF}chart:1.0}}chart":
        # An embedded chart's '..' points at its containing spreadsheet; '.'
        # selects its own local data table. Neither names an image file.
        parent = posixpath.dirname(owner)
        if book.package.manifest.get(parent + "/") == CHART_MIME and target in {
            ".",
            parent,
        }:
            return
        raise ValueError("ODS chart data source needs a resource-aware preview")
    kind = (
        "chart"
        if node.tag == q("draw", "object")
        else ("font" if etree.QName(node).localname == "font-face-uri" else "image")
    )
    key = (target, kind)
    if key in inspected:
        return
    if node.tag == q("draw", "object"):
        if book.package.manifest.get(target.rstrip("/") + "/") != CHART_MIME:
            raise ValueError("ODS embedded object needs a dedicated preview")
        if target.rstrip("/") + "/content.xml" not in book.package.parts:
            raise ValueError("Missing embedded ODS chart content")
        chart = book.package.xml(target.rstrip("/") + "/content.xml")
        if (
            chart.tag != q("office", "document-content")
            or chart.find("office:body/office:chart", NS) is None
        ):
            raise ValueError("ODS embedded chart identity does not match its manifest")
        inspected.add(key)
        return
    if target not in book.package.parts:
        raise ValueError("ODS preview references a missing package resource")
    content = book.package.parts[target]
    if etree.QName(node).localname == "font-face-uri":
        if content[:4] not in {b"\x00\x01\x00\x00", b"OTTO", b"ttcf", b"wOFF", b"wOF2"}:
            raise ValueError("Unsupported embedded ODS font")
    else:
        mime = book.package.manifest.get(target, "").split(";", 1)[0]
        if mime == METAFILE_MIME and node.tag == q("draw", "image"):
            _metafile(content)
        else:
            _image(content)
    inspected.add(key)


def rendering_source(data: bytes) -> list[dict[str, Any]]:
    book = NativeODS(data)
    if len(book.tables) > 100:
        raise ValueError("ODS previews require 1..100 tables")
    if book.package.signed:
        raise ValueError("Signed ODS files need a signature-aware preview")
    inspected: set[tuple[str, str]] = set()
    for name in book.package.parts:
        if name.lower().startswith(("basic/", "scripts/")):
            raise ValueError("ODS scripts need a resource-aware preview")
        mime = book.package.manifest.get(name, "")
        if not (name.endswith((".xml", ".rdf")) or mime.endswith(("+xml", "/xml"))):
            continue
        root = book.root if name == "content.xml" else book.package.xml(name)
        for node in root.iter():
            if not isinstance(node.tag, str):
                continue
            tag = etree.QName(node)
            if (
                node.tag in BLOCKED_ELEMENTS
                or tag.namespace in {ODF + "script:1.0", ODF + "form:1.0"}
                or (
                    tag.localname in {"scripts", "event-listeners", "forms"}
                    and len(node)
                )
            ):
                raise ValueError(
                    "Active or linked ODS content needs a resource-aware preview"
                )
            if node.get(XML_BASE):
                raise ValueError(
                    "ODS XML base remapping needs a resource-aware preview"
                )
            if href := node.get(f"{{{XLINK}}}href"):
                _resource(book, name, node, href, inspected)
            if node.tag == q("office", "binary-data"):
                if node.getparent() is None or node.getparent().tag != q(
                    "draw", "image"
                ):
                    raise ValueError(
                        "Embedded ODS binary object needs a dedicated preview"
                    )
                try:
                    binary = base64.b64decode(
                        "".join("".join(node.itertext()).split()), validate=True
                    )
                except ValueError as exc:
                    raise ValueError("Invalid embedded ODS image encoding") from exc
                _image(binary)
            for attribute, value in node.attrib.items():
                local = etree.QName(attribute).localname
                if attribute == q("table", "formula"):
                    check_formula(value, node, qualified=True)
                elif local in {"condition", "formula", "expression"} or (
                    node.tag
                    == "{urn:org:documentfoundation:names:experimental:calc:xmlns:calcext:1.0}condition"
                    and attribute
                    == "{urn:org:documentfoundation:names:experimental:calc:xmlns:calcext:1.0}value"
                ):
                    check_formula(value, node, qualified=False)
                elif (
                    local.endswith(("cell-address", "cell-range-address"))
                    or local == "print-ranges"
                ):
                    check_reference(value)
    return [
        {
            "index": index,
            "key": {
                "part": "content.xml",
                "table_index": index,
                "table_name": table.get(q("table", "name")),
            },
            "name": table.get(q("table", "name")),
            "native_attributes": dict(table.attrib),
            "visibility": "Retained in native styles; actual print visibility requires rendered review",
        }
        for index, table in enumerate(book.tables)
    ]
