"""Workbook preview input checks without changing its source or formula strings."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from lxml import etree
from openpyxl.formula.tokenizer import Token

from src.infrastructure.native_ooxml import DOC_REL_NS, SHEET_NS
from src.infrastructure.native_workbook_formulas import (
    _qualifier_spans,
    formula_tokens,
    sheet_references,
)
from src.infrastructure.native_workbook_package import (
    WORKSHEET_REL,
    NativeWorkbookPackage,
)

RESOURCE_FUNCTIONS = {
    "DDE",
    "WEBSERVICE",
    "RTD",
    "IMAGE",
    "STOCKHISTORY",
    "IMPORTDATA",
    "IMPORTHTML",
    "IMPORTXML",
    "IMPORTRANGE",
    "IMPORTFEED",
    "CALL",
    "EXEC",
    "REGISTER",
    "REGISTER.ID",
    "EVALUATE",
    "RUN",
    "SQL.REQUEST",
}
RESOURCE_KINDS = {
    "oleobject",
    "package",
    "vbaproject",
    "activex",
    "externallink",
    "connections",
    "querytable",
    "xlmacrosheet",
    "xlintlmacrosheet",
    "control",
}
FORMULA_TAGS = {
    "f",
    "formula",
    "formula1",
    "formula2",
    "definedName",
    "calculatedColumnFormula",
    "totalsRowFormula",
}


def check_formula(text: str, sheet_names: set[str]) -> None:
    for _start, _end, value, kind, subtype in formula_tokens(text.removeprefix("=")):
        if kind == Token.FUNC and subtype == Token.OPEN:
            function = value[:-1].lstrip("@").upper()
            if function.startswith(("_XLL.", "_XLUDF.")) or any(
                c in function for c in "[]!"
            ):
                raise ValueError(
                    "Workbook add-in formulas need a resource-aware preview"
                )
            function = function.removeprefix("_XLFN.").removeprefix("_XLWS.")
            if function in RESOURCE_FUNCTIONS:
                raise ValueError(
                    "Resource-loading workbook formulas need a resource-aware preview"
                )
        if kind == Token.OPERAND and subtype == Token.RANGE:
            for start, end in _qualifier_spans(value):
                if any(char in value[start:end] for char in "[]"):
                    raise ValueError(
                        "External workbook operands need a resource-aware preview"
                    )
            # DDE uses a pipe inside the qualifier. A real local sheet name can
            # also contain a pipe, so resolve the parsed qualifier before rejecting.
            if any("|" in value[start:end] for start, end in _qualifier_spans(value)):
                references = sheet_references(value)
                if not references or any(
                    name.casefold() not in sheet_names
                    for reference in references
                    for name in reference.names
                ):
                    raise ValueError("Unresolved DDE-like workbook operand")


def rendering_source(data: bytes) -> list[dict[str, Any]]:
    book = NativeWorkbookPackage(data)
    if not 1 <= len(book.entries) <= 100 or any(
        item["kind"] != WORKSHEET_REL for item in book.entries
    ):
        raise ValueError("Workbook previews require 1..100 ordinary worksheets")
    book.active_parts()  # Detect missing active relationships before conversion.
    names = {item["name"].casefold() for item in book.entries}
    types = book.package.xml("[Content_Types].xml")
    for item in types:
        content_type = item.get("ContentType", "").lower()
        if any(
            word in content_type
            for word in (
                "macroenabled",
                "vbaproject",
                "activex",
                "oleobject",
                "connections",
                "querytable",
                "externallink",
                "macrosheet",
                "image/svg",
            )
        ):
            raise ValueError(
                "Active or linked workbook content needs a resource-aware preview"
            )
    for name in book.package.parts:
        if name.lower().endswith((".svg", ".svgz")):
            raise ValueError("SVG media needs a resource-aware workbook preview")
        if name.endswith(".rels"):
            path = PurePosixPath(name)
            if name == "_rels/.rels":
                owner = ""
            elif path.parent.name == "_rels":
                owner = str(path.parent.parent / path.name[:-5])
            else:
                raise ValueError("Ambiguous workbook relationship part")
            for node in book.package.xml(name):
                kind = node.get("Type", "")
                if (
                    node.get("TargetMode") == "External"
                    and kind != f"{DOC_REL_NS}/hyperlink"
                ) or kind.rsplit("/", 1)[-1].lower() in RESOURCE_KINDS:
                    raise ValueError(
                        "Linked or embedded workbook content needs a resource-aware preview"
                    )
            for _, target in book.package.relationships(owner).values():
                if target and target not in book.package.parts:
                    raise ValueError("Workbook preview references a missing part")
        elif name.endswith((".xml", ".vml")):
            root = book.package.xml(name)
            for node in root.iter():
                if not isinstance(node.tag, str):
                    continue
                tag = etree.QName(node)
                if tag.localname in FORMULA_TAGS and node.text:
                    check_formula(node.text, names)
                if tag.localname in {
                    "oleObject",
                    "OLEObject",
                    "connection",
                    "queryTable",
                    "externalBook",
                    "ddeLink",
                    "oleLink",
                } or (
                    tag.namespace == "urn:schemas-microsoft-com:vml" and node.get("src")
                ):
                    raise ValueError(
                        "Resource-loading workbook XML needs a dedicated preview"
                    )
    for item in book.entries:
        if book.package.xml(item["key"]["part"]).tag != f"{{{SHEET_NS}}}worksheet":
            raise ValueError(
                "Workbook preview worksheet identity does not match its part"
            )
    return [
        {key: item[key] for key in ("index", "key", "name", "state")}
        for item in book.entries
    ]
