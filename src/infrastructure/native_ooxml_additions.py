"""Explicit bounded package additions without resaving unrelated OOXML parts."""

from __future__ import annotations

import copy
import io
import zipfile

from src.infrastructure.native_ooxml import (
    MAX_PACKAGE_BYTES,
    MAX_PART_BYTES,
    NativeOOXMLPackage,
)


def extend_package(
    package: NativeOOXMLPackage,
    replacements: dict[str, bytes],
    additions: dict[str, bytes],
) -> bytes:
    if set(replacements) - set(package.parts) or set(additions) & set(package.parts):
        raise ValueError(
            "OOXML additions/replacements conflict with original inventory"
        )
    expected = {**package.parts, **replacements, **additions}
    if (
        len(expected) > 10_000
        or any(len(p) > MAX_PART_BYTES for p in expected.values())
        or sum(map(len, expected.values())) > MAX_PACKAGE_BYTES
    ):
        raise ValueError("OOXML additions exceed package resource limits")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.comment = package.comment
        for info in package.infos:
            archive.writestr(copy.copy(info), expected[info.filename])
        for name, content in sorted(additions.items()):
            info = zipfile.ZipInfo(name)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, content)
    data = output.getvalue()
    checked = NativeOOXMLPackage(data)
    if checked.parts != expected:
        raise ValueError("OOXML package bytes changed outside explicit additions")
    return data
