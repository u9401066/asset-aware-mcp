"""Compact native ODS fixtures, with explicit package inventory."""

import io
import zipfile

from lxml import etree

from src.domain.native_ods import (
    NativeODSCellEdit,
    NativeODSCellLocator,
    NativeODSCreate,
    NativeODSValue,
)
from src.infrastructure.native_odf_package import NS, NativeODFPackage, q, xml_bytes
from src.infrastructure.native_ods import create_native_ods


def locator(row=0, column=0, name="Sheet1", index=0):
    return NativeODSCellLocator(
        table_index=index, table_name=name, row=row, column=column
    )


def edit(row=0, column=0, value="changed", kind="string", name="Sheet1", **kwargs):
    return NativeODSCellEdit(
        locator=locator(row, column, name),
        value=NativeODSValue(kind=kind, value=value, **kwargs),
        display_policy="replace_paragraphs_preserve_cell_style",
    )


def repack(parts, *, comment=b"fixture", order=None):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.comment = comment
        for name in order or parts:
            info = zipfile.ZipInfo(name, (2001, 2, 3, 4, 5, 6))
            info.compress_type = (
                zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED
            )
            archive.writestr(info, parts[name])
    return output.getvalue()


def fixture(rows_xml, *, table_attributes="", extras=None):
    book = NativeODFPackage(create_native_ods(NativeODSCreate()))
    root = book.xml("content.xml")
    table = root.find("office:body/office:spreadsheet/table:table", NS)
    assert table is not None
    parent = table.getparent()
    assert parent is not None
    parent.remove(table)
    declarations = " ".join(f'xmlns:{key}="{value}"' for key, value in NS.items())
    # Reparenting can drop aliases used only inside attribute values. Parse the
    # complete fixture later, just as a real package is read from source bytes.
    table_xml = f'<table:table {declarations} table:name="Sheet1" {table_attributes}>{rows_xml}</table:table>'.encode()
    content = xml_bytes(root).replace(
        b"<office:spreadsheet/>",
        b"<office:spreadsheet>" + table_xml + b"</office:spreadsheet>",
    )
    parts = {**book.parts, "content.xml": content, **(extras or {})}
    manifest = book.xml("META-INF/manifest.xml")
    for name in extras or {}:
        item = etree.SubElement(manifest, q("manifest", "file-entry"))
        item.set(q("manifest", "full-path"), name)
        item.set(q("manifest", "media-type"), "application/octet-stream")
    parts["META-INF/manifest.xml"] = xml_bytes(manifest)
    return repack(parts)
