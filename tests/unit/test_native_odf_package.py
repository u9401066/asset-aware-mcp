"""ODF package integrity and exact preservation of members outside the edit."""

import io
import zipfile

import pytest
from lxml import etree

from src.domain.native_ods import NativeODSCreate
from src.infrastructure.native_odf_package import NativeODFPackage, q, xml_bytes
from src.infrastructure.native_ods import NativeODS, create_native_ods
from tests.native_ods_helpers import edit, repack


def parts():
    return NativeODFPackage(create_native_ods(NativeODSCreate())).parts


@pytest.mark.parametrize(
    "case",
    [
        "duplicate",
        "traversal",
        "missing",
        "mimetype",
        "mime_order",
        "manifest_root",
        "dtd",
        "encryption",
        "unlisted",
    ],
)
def test_invalid_packages_fail_explicitly(case):
    data = parts()
    if case == "traversal":
        data["../outside"] = b"x"
    elif case == "missing":
        data.pop("content.xml")
    elif case == "mimetype":
        data["mimetype"] = b"application/zip"
    elif case == "manifest_root":
        data["META-INF/manifest.xml"] = b"<not-manifest/>"
    elif case == "dtd":
        data["META-INF/manifest.xml"] = (
            b'<!DOCTYPE manifest [<!ENTITY a "x">]>'
            + data["META-INF/manifest.xml"].split(b"?>", 1)[1]
        )
    elif case == "encryption":
        root = etree.fromstring(data["META-INF/manifest.xml"])
        etree.SubElement(root[1], q("manifest", "encryption-data"))
        data["META-INF/manifest.xml"] = xml_bytes(root)
    elif case == "unlisted":
        data["unknown.bin"] = b"x"
    order = list(data)
    if case == "mime_order":
        order.reverse()
    result = repack(data, order=order)
    if case == "duplicate":
        output = io.BytesIO(result)
        with zipfile.ZipFile(output, "a") as archive, pytest.warns(UserWarning):
            archive.writestr("content.xml", data["content.xml"])
        result = output.getvalue()
    with pytest.raises(ValueError):
        NativeODFPackage(result)


def test_signature_is_readable_but_prevents_edit_and_replacement():
    data = parts()
    data["META-INF/documentsignatures.xml"] = b"<signature/>"
    source = repack(data)
    package = NativeODFPackage(source)
    assert package.signed and package.replace({}) == source
    assert NativeODS(source).inspect()["format"] == "ods"
    with pytest.raises(ValueError, match="Signed"):
        NativeODS(source).edit([edit()])


def test_zip_metadata_and_unmodified_member_bytes_survive():
    source = repack(parts(), comment=b"keep package comment")
    changed, _ = NativeODS(source).edit([edit()])
    before, after = NativeODFPackage(source), NativeODFPackage(changed)
    assert before.comment == after.comment
    assert [
        (i.filename, i.date_time, i.compress_type, i.external_attr)
        for i in before.infos
    ] == [
        (i.filename, i.date_time, i.compress_type, i.external_attr) for i in after.infos
    ]
    for name in before.parts:
        if name != "content.xml":
            assert before.parts[name] == after.parts[name]


def test_compressed_mimetype_is_not_silently_repaired():
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in parts().items():
            archive.writestr(name, content)
    with pytest.raises(ValueError, match="uncompressed"):
        NativeODFPackage(output.getvalue())


def test_decompression_and_replacement_budgets(monkeypatch):
    import src.infrastructure.native_odf_package as module

    source = create_native_ods(NativeODSCreate())
    package = NativeODFPackage(source)
    monkeypatch.setattr(module, "MAX_PART_BYTES", 100)
    with pytest.raises(ValueError, match="decompression"):
        NativeODFPackage(source)
    with pytest.raises(ValueError, match="byte budget"):
        package.replace({"content.xml": b"x" * 101})
