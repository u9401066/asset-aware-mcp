"""Native ODS adapter; source documents are never converted to an intermediate format."""

from __future__ import annotations

import io
import zipfile
from typing import TYPE_CHECKING, Any

from lxml import etree

from src.domain.native_ods import NativeODSCellLocator
from src.infrastructure.native_odf_package import NS, ODS_MIME, q, xml_bytes
from src.infrastructure.native_ods_editor import edit_ods
from src.infrastructure.native_ods_reader import (
    NativeODSReader,
    cell_record,
    cells,
    rows,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from src.domain.native_asset_models import NativeEditResult
    from src.domain.native_ods import NativeODSCellEdit, NativeODSCreate


class NativeODS(NativeODSReader):
    def edit(self, edits: list[NativeODSCellEdit]) -> tuple[bytes, NativeEditResult]:
        return edit_ods(self.package.original, edits)


class NativeODSFileAdapter:
    def create(self, request: NativeODSCreate) -> bytes:
        return create_native_ods(request)

    def inspect(self, data: bytes, *, offset: int, limit: int) -> dict[str, Any]:
        return NativeODS(data).inspect(offset=offset, limit=limit)

    def read_cell(self, data: bytes, locator: NativeODSCellLocator) -> dict[str, Any]:
        return NativeODS(data).read_cell(locator)

    def edit(
        self, data: bytes, edits: list[NativeODSCellEdit]
    ) -> tuple[bytes, NativeEditResult]:
        return edit_ods(data, edits)

    def decompose(self, data: bytes) -> Iterator[dict[str, Any]]:
        book = NativeODS(data)
        for index, table in enumerate(book.tables):
            for row_start, row_count, row in rows(table):
                for column_start, column_count, cell in cells(row):
                    locator = NativeODSCellLocator(
                        table_index=index,
                        table_name=table.get(q("table", "name")),
                        row=row_start,
                        column=column_start,
                    )
                    yield cell_record(
                        locator,
                        cell,
                        {
                            "row_start": row_start,
                            "row_count": row_count,
                            "column_start": column_start,
                            "column_count": column_count,
                        },
                    )


def create_native_ods(request: NativeODSCreate) -> bytes:
    root = etree.Element(
        q("office", "document-content"),
        nsmap={k: v for k, v in NS.items() if k != "manifest"},
    )
    root.set(q("office", "version"), "1.3")
    etree.SubElement(root, q("office", "automatic-styles"))
    body = etree.SubElement(
        etree.SubElement(root, q("office", "body")), q("office", "spreadsheet")
    )
    for name in request.tables:
        table = etree.SubElement(body, q("table", "table"))
        table.set(q("table", "name"), name)
        etree.SubElement(table, q("table", "table-column"))
        row = etree.SubElement(table, q("table", "table-row"))
        etree.SubElement(row, q("table", "table-cell"))
    manifest = etree.Element(
        q("manifest", "manifest"), nsmap={"manifest": NS["manifest"]}
    )
    manifest.set(q("manifest", "version"), "1.3")
    for name, mime in (("/", ODS_MIME), ("content.xml", "text/xml")):
        item = etree.SubElement(manifest, q("manifest", "file-entry"))
        item.set(q("manifest", "full-path"), name)
        item.set(q("manifest", "media-type"), mime)
        if name == "/":
            item.set(q("manifest", "version"), "1.3")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, content in (
            ("mimetype", ODS_MIME.encode("ascii")),
            ("META-INF/manifest.xml", xml_bytes(manifest)),
            ("content.xml", xml_bytes(root)),
        ):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = (
                zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED
            )
            archive.writestr(info, content)
    result = output.getvalue()
    NativeODS(result)
    return result
