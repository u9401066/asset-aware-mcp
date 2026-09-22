"""Native ODS dependency inventory and checked, owner-aware reference plans.

A plan is not a structural transaction. The transaction also moves native grid
objects, handles unresolved owners, invalidates caches and reopens the package.
References in embedded chart data and references to the parent workbook belong
to different coordinate spaces even when their table names happen to coincide.
"""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import quote, unquote, urlsplit

from lxml import etree

from src.domain.native_ods_references import (
    MAX_REFERENCE_TEXT,
    OPENFORMULA,
    ODSAxisEdit,
    ODSReferenceChange,
    ODSSheetRename,
    map_ods_expression_references,
    ods_formula_start,
    parse_ods_reference,
    quoted_end,
    rewrite_ods_reference,
)
from src.infrastructure.native_odf_package import NS, ODF, q, xml_bytes

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.domain.native_ods_references import ODSReferenceEdit
    from src.infrastructure.native_ods_reader import NativeODSReader

CHART = ODF + "chart:1.0"
CALCEXT = "urn:org:documentfoundation:names:experimental:calc:xmlns:calcext:1.0"
XLINK = "http://www.w3.org/1999/xlink"
SVG_DESCRIPTIONS = {
    "{" + ODF + "svg-compatible:1.0}desc",
    "{http://www.w3.org/2000/svg}desc",
}
MAX_DEPENDENCIES = 40_000
MAX_DEPENDENCY_BYTES = 32 * 1024 * 1024
ADDRESS_NAMES = {
    "base-cell-address",
    "cell-address",
    "cell-range",
    "cell-range-address",
    "condition-source-range-address",
    "data-cell-range-address",
    "end-cell-address",
    "label-cell-range-address",
    "source-cell-range-address",
    "target-cell-address",
    "target-range-address",
}
ADDRESSES = (
    {q("table", name) for name in ADDRESS_NAMES}
    | {
        f"{{{CHART}}}{name}"
        for name in ("values-cell-range-address", "label-cell-address")
    }
    | {f"{{{CALCEXT}}}base-cell-address", q("style", "base-cell-address")}
)
ADDRESS_LISTS = {
    q("table", "print-ranges"),
    q("draw", "notify-on-update-of-ranges"),
    f"{{{CALCEXT}}}target-range-address",
}
EXPRESSIONS = {
    q("table", "expression"),
    q("table", "condition"),
    q("style", "condition"),
}
Kind = Literal[
    "formula", "expression", "address", "addresses", "sheet", "link", "unknown"
]


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class ODSDependency:
    part: str
    path: str
    element: str
    attribute: str | None
    value: str
    kind: Kind
    context_sheet: str | None
    scope: Literal["workbook", "embedded_local"]
    namespaces: dict[str | None, str]
    owner_attributes: dict[str, str]

    @property
    def key(self) -> tuple[str, str, str | None]:
        return self.part, self.path, self.attribute

    def record(self) -> dict[str, Any]:
        value = asdict(self)
        # JSON object keys cannot faithfully distinguish None from the string
        # 'null'. Retain the XML default prefix explicitly as an ordered record.
        value["namespaces"] = [
            {"prefix": key, "uri": uri}
            for key, uri in sorted(
                self.namespaces.items(), key=lambda item: item[0] or ""
            )
        ]
        return value


@dataclass(frozen=True)
class ODSDependencyChange:
    dependency: ODSDependency
    after: str
    spans: tuple[ODSReferenceChange, ...]

    def record(self) -> dict[str, Any]:
        return {
            "operation": "map_native_ods_dependency",
            "before": self.dependency.record(),
            "after": self.after,
            "original_unicode_spans": [asdict(span) for span in self.spans],
        }


@dataclass(frozen=True)
class ODSDependencyPlan:
    inventory_sha256: str
    edit: ODSReferenceEdit
    changes: tuple[ODSDependencyChange, ...]
    unresolved: tuple[dict[str, Any], ...]


def _list_map(
    value: str, mapper: Callable[[str], str]
) -> tuple[str, list[ODSReferenceChange]]:
    """Preserve list whitespace; spaces inside a quoted sheet are not separators."""
    index, copied = 0, 0
    pieces: list[str] = []
    changes: list[ODSReferenceChange] = []
    while index < len(value):
        if value[index].isspace():
            index += 1
            continue
        start = index
        while index < len(value) and not value[index].isspace():
            index = quoted_end(value, index) if value[index] == "'" else index + 1
        before = value[start:index]
        after = mapper(before)
        if before != after:
            pieces.extend((value[copied:start], after))
            changes.append(ODSReferenceChange(start, index, before, after))
            copied = index
    pieces.append(value[copied:])
    result = "".join(pieces)
    if len(result) > MAX_REFERENCE_TEXT:
        raise ValueError("ODS dependency list exceeds its reference budget")
    return result, changes


def _context(
    node: etree._Element, *, embedded: bool, parent_data: bool
) -> tuple[str | None, str]:
    current: etree._Element | None = node
    while current is not None:
        if current.tag == q("table", "table"):
            return current.get(
                q("table", "name")
            ), "embedded_local" if embedded else "workbook"
        address = (
            current.get(q("table", "base-cell-address"))
            or current.get(f"{{{CALCEXT}}}base-cell-address")
            or current.get(q("style", "base-cell-address"))
        )
        if address:
            reference = parse_ods_reference(address)
            if reference.source is None and reference.start and reference.start.sheet:
                return (
                    reference.start.sheet,
                    "embedded_local" if embedded else "workbook",
                )
        current = current.getparent()
    return None, "workbook" if not embedded or parent_data else "embedded_local"


def _kind(node: etree._Element, attribute: str) -> Kind | None:
    if attribute == q("table", "formula"):
        return "formula"
    if attribute in EXPRESSIONS or (
        node.tag == f"{{{CALCEXT}}}condition" and attribute == f"{{{CALCEXT}}}value"
    ):
        return "expression"
    if attribute in ADDRESSES:
        return "address"
    if attribute in ADDRESS_LISTS:
        return "addresses"
    if attribute == q("table", "table-name"):
        return "sheet"
    if attribute == f"{{{XLINK}}}href" and node.get(attribute, "").startswith("#"):
        return "link"
    local = etree.QName(attribute).localname
    if local in ADDRESS_NAMES | {
        "formula",
        "expression",
        "condition",
        "print-ranges",
        "notify-on-update-of-ranges",
    }:
        return "unknown"
    return None


def _chart_cache_cell(node: etree._Element | None) -> bool:
    if node is None or node.tag != q("table", "table-cell"):
        return False
    for ancestor in node.iterancestors():
        if ancestor.tag == q("table", "table"):
            parent = ancestor.getparent()
            return parent is not None and parent.tag == f"{{{CHART}}}chart"
    return False


def _chart_parent_source(part: str, href: str) -> bool:
    if not href:
        return False
    uri = urlsplit(href)
    if uri.scheme or uri.netloc or uri.query or uri.fragment:
        raise ValueError("Chart data source requires identity resolution")
    path = unquote(uri.path, errors="strict")
    if not path or path.startswith("/") or "\\" in path or "\x00" in path:
        raise ValueError("Ambiguous chart data source path")
    owner = posixpath.dirname(part)
    target = posixpath.normpath(posixpath.join(owner, path))
    if target == ".":
        return True
    if target == owner:
        return False
    raise ValueError("Nested/foreign chart source requires its own dependency map")


class ODSDependencies:
    """Inventory existing XML once; plans must match that exact inventory on apply."""

    def __init__(self, book: NativeODSReader):
        self.book = book
        self.roots: dict[str, etree._Element] = {"content.xml": book.root}
        self.nodes: dict[tuple[str, str, str | None], etree._Element] = {}
        self.dependencies: list[ODSDependency] = []
        self.issues: list[dict[str, str]] = []
        self.changed_parts: set[str] = set()
        self.sheet_names = [table.get(q("table", "name"), "") for table in book.tables]
        for part in book.package.parts:
            if (
                part != "content.xml"
                and part.endswith(".xml")
                and not part.startswith("META-INF/")
            ):
                self.roots[part] = book.package.xml(part)
        for part, root in self.roots.items():
            embedded = "/" in part
            chart = root.find("office:body/office:chart", NS)
            parent_data = False
            if chart is not None:
                models = chart.findall(f"{{{CHART}}}chart")
                if len(models) != 1:
                    self.issues.append(
                        {"part": part, "reason": "ambiguous_embedded_chart_identity"}
                    )
                else:
                    source = models[0].get(f"{{{XLINK}}}href", "")
                    try:
                        parent_data = _chart_parent_source(part, source)
                    except ValueError:
                        self.issues.append(
                            {
                                "part": part,
                                "reason": "embedded_chart_source_requires_identity_resolution",
                            }
                        )
                directory = posixpath.dirname(part) + "/"
                if (
                    book.package.manifest.get(directory)
                    != "application/vnd.oasis.opendocument.chart"
                ):
                    self.issues.append(
                        {
                            "part": part,
                            "reason": "embedded_chart_manifest_identity_mismatch",
                        }
                    )
            # An embedded ODF object can contain workbook links whose native
            # reference grammar differs. Its bytes alone cannot certify a map.
            if (
                embedded
                and chart is None
                and root.tag
                in {
                    q("office", "document-content"),
                    q("office", "document"),
                }
            ):
                self.issues.append(
                    {
                        "part": part,
                        "reason": "embedded_document_needs_its_own_dependency_map",
                    }
                )
            for node in root.iter():
                if not isinstance(node.tag, str):
                    continue
                if "{http://www.w3.org/XML/1998/namespace}base" in node.attrib:
                    self.issues.append(
                        {
                            "part": part,
                            "path": root.getroottree().getpath(node),
                            "reason": "xml_base_requires_source_identity_resolution",
                        }
                    )
                if node.tag in {
                    q("table", "tracked-changes"),
                    q("office", "script"),
                    q("draw", "object-ole"),
                } or (node.tag == q("office", "scripts") and len(node)):
                    self.issues.append(
                        {
                            "part": part,
                            "path": root.getroottree().getpath(node),
                            "reason": "opaque_or_revision_aware_dependencies",
                        }
                    )
                for attribute, value in node.attrib.items():
                    kind = _kind(node, attribute)
                    if kind is not None:
                        self._add(
                            part, node, attribute, value, kind, embedded, parent_data
                        )
                # Calc's chart cache stores ORIGINAL parent ranges in the
                # description of an otherwise empty draw:g inside a cache cell.
                # This is not the local table's coordinate space or an arbitrary
                # accessibility caption. See upstream SchXMLTableCellContext and
                # SchXMLRangeSomewhereContext in xmloff/source/chart/SchXMLTableContext.cxx.
                group = node.getparent()
                if (
                    parent_data
                    and node.tag in SVG_DESCRIPTIONS
                    and group is not None
                    and group.tag == q("draw", "g")
                    and not group.attrib
                    and len(group) == 1
                    and _chart_cache_cell(group.getparent())
                ):
                    if len(node):
                        self.issues.append(
                            {
                                "part": part,
                                "reason": "chart_source_range_description_requires_plain_text",
                            }
                        )
                    else:
                        self._add(
                            part,
                            node,
                            None,
                            node.text or "",
                            "address",
                            embedded,
                            parent_data,
                            parent_source=True,
                        )
                if (
                    parent_data
                    and node.tag == q("text", "p")
                    and _chart_cache_cell(node.getparent())
                    and q("text", "id") in node.attrib
                ):
                    # Older Calc exports used text:id for the same source range.
                    self._add(
                        part,
                        node,
                        q("text", "id"),
                        node.attrib[q("text", "id")],
                        "address",
                        embedded,
                        parent_data,
                        parent_source=True,
                    )
                if node.tag == q("config", "config-item-map-entry"):
                    parent = node.getparent()
                    if (
                        parent is not None
                        and parent.tag == q("config", "config-item-map-named")
                        and parent.get(q("config", "name"))
                        in {"Tables", "ScriptConfiguration"}
                    ):
                        attribute = q("config", "name")
                        self._add(
                            part,
                            node,
                            attribute,
                            node.get(attribute, ""),
                            "sheet",
                            False,
                            False,
                        )
                if (
                    node.tag == q("config", "config-item")
                    and node.get(q("config", "name")) == "ActiveTable"
                ):
                    self._add(part, node, None, node.text or "", "sheet", False, False)
        self.original_xml = {part: xml_bytes(root) for part, root in self.roots.items()}
        # Bound the serialized evidence itself, not merely its record count.
        if (
            len(json.dumps(self.catalog(), ensure_ascii=False).encode("utf-8"))
            > MAX_DEPENDENCY_BYTES
        ):
            raise ValueError("ODS dependency inventory exceeds its evidence budget")

    def _add(
        self,
        part: str,
        node: etree._Element,
        attribute: str | None,
        value: str,
        kind: Kind,
        embedded: bool,
        parent_data: bool,
        *,
        parent_source: bool = False,
    ) -> None:
        if (
            len(value) > MAX_REFERENCE_TEXT
            or len(self.dependencies) >= MAX_DEPENDENCIES
        ):
            raise ValueError("ODS dependency inventory exceeds its reference budget")
        context, scope = _context(node, embedded=embedded, parent_data=parent_data)
        if parent_source:
            context, scope = None, "workbook"
        dependency = ODSDependency(
            part,
            self.roots[part].getroottree().getpath(node),
            node.tag,
            attribute,
            value,
            kind,
            context,
            "embedded_local" if scope == "embedded_local" else "workbook",
            dict(node.nsmap),
            dict(node.attrib),
        )
        if dependency.key in self.nodes:
            raise ValueError("Ambiguous ODS dependency identity")
        self.nodes[dependency.key] = node
        self.dependencies.append(dependency)

    def catalog(self) -> dict[str, Any]:
        records = [dependency.record() for dependency in self.dependencies]
        body = {
            "schema_version": "native-ods-dependencies-v1",
            "sheets": self.sheet_names,
            "dependencies": records,
            "issues": self.issues,
            "parsed_parts_sha256": {
                part: hashlib.sha256(data).hexdigest()
                for part, data in self.original_xml.items()
            },
        }
        return {**body, "inventory_sha256": _digest(body)}

    def plan(self, edit: ODSReferenceEdit) -> ODSDependencyPlan:
        self._assert_snapshot()
        if edit.sheet not in self.sheet_names:
            raise ValueError(
                "ODS structural target table is absent from this inventory"
            )
        if (
            isinstance(edit, ODSSheetRename)
            and edit.new_name != edit.sheet
            and edit.new_name in self.sheet_names
        ):
            raise ValueError(
                "ODS renamed table would collide with an existing identity"
            )
        changes: list[ODSDependencyChange] = []
        unresolved: list[dict[str, Any]] = [dict(issue) for issue in self.issues]
        for dependency in self.dependencies:
            if dependency.scope == "embedded_local":
                continue
            try:
                after, spans = self._map(dependency, edit)
                if after != dependency.value:
                    changes.append(ODSDependencyChange(dependency, after, tuple(spans)))
            except ValueError as exc:
                unresolved.append(
                    {"dependency": dependency.record(), "reason": str(exc)}
                )
        return ODSDependencyPlan(
            self.catalog()["inventory_sha256"], edit, tuple(changes), tuple(unresolved)
        )

    def _map(
        self, dependency: ODSDependency, edit: ODSReferenceEdit
    ) -> tuple[str, list[ODSReferenceChange]]:
        value, kind = dependency.value, dependency.kind
        if kind == "unknown":
            raise ValueError(
                "Unknown dependency namespace/grammar needs an owner-specific map"
            )
        if kind == "sheet":
            if value != edit.sheet:
                return value, []
            if not isinstance(edit, ODSSheetRename):
                if isinstance(edit, ODSAxisEdit):
                    return value, []
                raise ValueError(
                    "Deleted sheet identity needs an owner-specific removal/rebinding policy"
                )
            return edit.new_name, [
                ODSReferenceChange(0, len(value), value, edit.new_name)
            ]

        def mapper(reference: str) -> str:
            parsed = parse_ods_reference(reference)
            if parsed.start is not None and parsed.source is None:
                if parsed.start.sheet is None and dependency.context_sheet is None:
                    raise ValueError(
                        "Relative ODS dependency requires an explicit base table"
                    )
                if (
                    parsed.start.sheet is None
                    and dependency.context_sheet not in self.sheet_names
                ):
                    raise ValueError(
                        "Relative ODS dependency belongs to a nested/unknown table"
                    )
                for endpoint in (parsed.start, parsed.end):
                    if (
                        endpoint
                        and endpoint.sheet is not None
                        and endpoint.sheet not in self.sheet_names
                    ):
                        raise ValueError(
                            "ODS dependency table alias/identity requires resolution"
                        )
                if (
                    isinstance(edit, ODSAxisEdit)
                    and dependency.element == q("table", "named-range")
                    and dependency.attribute == q("table", "cell-range-address")
                    and any(
                        endpoint
                        and (not endpoint.absolute_row or not endpoint.absolute_column)
                        for endpoint in (parsed.start, parsed.end)
                    )
                ):
                    raise ValueError(
                        "Relative named ranges require base/usage-aware axis mapping"
                    )
            return rewrite_ods_reference(
                reference,
                formula_sheet=dependency.context_sheet or "__unbound_context__",
                edit=edit,
            )

        if kind == "formula":
            start = ods_formula_start(value, namespaces=dependency.namespaces)
            return map_ods_expression_references(value, start=start, mapper=mapper)
        if kind == "expression":
            prefix, separator, _ = value.partition(":")
            # An unqualified native expression may itself contain a reference ':'
            # inside brackets or a quoted literal; only an initial QName is a prefix.
            qualified = bool(
                separator and re.fullmatch(r"[^\W\d][\w.-]*", prefix, re.UNICODE)
            )
            start = 0
            if qualified:
                if dependency.namespaces.get(prefix) != OPENFORMULA:
                    raise ValueError(
                        "ODS expression requires a known OpenFormula namespace"
                    )
                start = len(prefix) + 1
            return map_ods_expression_references(value, start=start, mapper=mapper)
        if kind == "link":
            decoded = unquote(value[1:], errors="strict")
            if decoded in self.sheet_names:
                if decoded != edit.sheet or isinstance(edit, ODSAxisEdit):
                    return value, []
                if not isinstance(edit, ODSSheetRename):
                    raise ValueError(
                        "Deleted hyperlink target needs an explicit link policy"
                    )
                mapped = edit.new_name
            else:
                mapped = mapper(decoded)
                if mapped == "#REF!":
                    raise ValueError(
                        "Deleted hyperlink range needs an explicit link policy"
                    )
            after = "#" + (quote(mapped, safe=".$:'![]") if "%" in value else mapped)
            return (
                (value, [])
                if mapped == decoded
                else (after, [ODSReferenceChange(0, len(value), value, after)])
            )
        if kind in {"address", "addresses"}:

            def address_mapper(reference: str) -> str:
                mapped = mapper(reference)
                if (
                    mapped == "#REF!"
                    and mapped != reference
                    and not (
                        dependency.element == q("table", "named-range")
                        and dependency.attribute == q("table", "cell-range-address")
                    )
                ):
                    raise ValueError(
                        "Deleted native address needs an owner-specific invalidation policy"
                    )
                return mapped

            if kind == "addresses":
                return _list_map(value, address_mapper)
            after = address_mapper(value)
            return (
                (value, [])
                if after == value
                else (after, [ODSReferenceChange(0, len(value), value, after)])
            )
        raise ValueError("Unsupported native dependency kind")

    def apply(self, plan: ODSDependencyPlan) -> list[dict[str, Any]]:
        if plan.unresolved:
            raise ValueError(
                "Resolve every ODS dependency owner before applying a structural plan"
            )
        if plan.inventory_sha256 != self.catalog()["inventory_sha256"]:
            raise ValueError("ODS dependency plan belongs to another inventory")
        self._assert_snapshot()
        if plan != self.plan(plan.edit):
            raise ValueError(
                "ODS dependency plan was modified or omits required changes"
            )
        keys = [change.dependency.key for change in plan.changes]
        if len(set(keys)) != len(keys):
            raise ValueError("ODS dependency plan contains duplicate targets")
        # Verify ALL native values before making even an in-memory partial edit.
        for change in plan.changes:
            node = self.nodes.get(change.dependency.key)
            if (
                node is None
                or (
                    node.text
                    if change.dependency.attribute is None
                    else node.get(change.dependency.attribute)
                )
                != change.dependency.value
            ):
                raise ValueError("ODS dependency changed after planning")
        for change in plan.changes:
            node = self.nodes[change.dependency.key]
            if change.dependency.attribute is None:
                node.text = change.after
            else:
                node.set(change.dependency.attribute, change.after)
            self.changed_parts.add(change.dependency.part)
        return [change.record() for change in plan.changes]

    def replacements(self) -> dict[str, bytes]:
        return {
            part: xml_bytes(self.roots[part]) for part in sorted(self.changed_parts)
        }

    def _assert_snapshot(self) -> None:
        if self.book.root is not self.roots["content.xml"] or any(
            xml_bytes(self.roots[part]) != value
            for part, value in self.original_xml.items()
        ):
            raise ValueError("ODS package XML changed after dependency planning")
