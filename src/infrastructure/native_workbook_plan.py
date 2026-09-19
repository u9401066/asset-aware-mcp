"""Commit and read back an explicit workbook structure patch."""

from __future__ import annotations

from typing import Any

from src.domain.native_asset_models import NativeEditResult
from src.infrastructure.native_ooxml import SHEET_NS, relationships_path, xml_bytes
from src.infrastructure.native_ooxml_additions import extend_package
from src.infrastructure.native_workbook_package import (
    WORKSHEET_REL,
    NativeWorkbookPackage,
)
from src.infrastructure.native_workbook_references import NativeWorkbookReferences
from src.infrastructure.native_workbook_repairs import (
    repair_caches,
    repair_calculation,
    repair_indices,
)


class WorkbookPlan:
    def __init__(self, data: bytes, removed: set[str] | None = None):
        self.book = book = NativeWorkbookPackage(data)
        book.check_editable()
        removed = removed or set()
        active = book.active_parts(removed)
        if any(
            item["key"]["part"] in active
            for item in book.entries
            if item["key"]["sheet_id"] in removed
        ):
            raise ValueError("Deleted worksheet has a surviving package relationship")
        self.refs = NativeWorkbookReferences(
            book,
            active,
            {
                item["index"]
                for item in book.entries
                if item["key"]["sheet_id"] in removed
            },
        )
        self.roots = self.refs.roots
        self.rel_path = relationships_path(book.workbook_path)
        self.roots[self.rel_path] = book.package.xml(self.rel_path)
        self.roots["[Content_Types].xml"] = book.package.xml("[Content_Types].xml")
        self.before_xml = {path: xml_bytes(root) for path, root in self.roots.items()}
        self.after = [
            dict(item)
            for item in book.entries
            if item["key"]["sheet_id"] not in removed
        ]
        self.repairs: list[str] = []

    def finish(self, change: dict[str, Any]) -> tuple[bytes, NativeEditResult]:
        book = self.book
        if not any(
            item["state"] == "visible" and item["kind"] == WORKSHEET_REL
            for item in self.after
        ):
            raise ValueError("At least one visible worksheet must remain")
        ordered = [book.nodes[item["key"]["sheet_id"]] for item in self.after]
        # Keep comments and non-element nodes while replacing the sheet slots.
        iterator = iter(ordered)
        children = []
        for node in book.sheet_list:
            if node.tag == f"{{{SHEET_NS}}}sheet":
                replacement = next(iterator, None)
                if replacement is not None:
                    children.append(replacement)
            else:
                children.append(node)
        children.extend(iterator)
        book.sheet_list[:] = children
        self.repairs.extend(repair_indices(book, self.after, self.roots))
        self.repairs.extend(repair_caches(book, self.after, self.roots))
        chains = repair_calculation(book, self.roots[self.rel_path])
        self.repairs.append("formula_recalculation_requested")
        if chains:
            self.repairs.append("stale_calculation_chain_detached")
        serialized = {path: xml_bytes(root) for path, root in self.roots.items()}
        replacements = {
            path: value
            for path, value in serialized.items()
            if path in self.before_xml and value != self.before_xml[path]
        }
        additions = {
            path: value
            for path, value in serialized.items()
            if path not in self.before_xml
        }
        data = extend_package(book.package, replacements, additions)
        checked = NativeWorkbookPackage(data)
        checked.active_parts()
        expected = [(item["key"], item["name"], item["state"]) for item in self.after]
        actual = [
            (item["key"], item["name"], item["state"]) for item in checked.entries
        ]
        if actual != expected:
            raise ValueError("Serialized workbook sheet registry failed read-back")
        return data, NativeEditResult(
            changed_parts=sorted(set(replacements) | set(additions)),
            preserved_parts=len(book.package.parts) - len(replacements),
            changes=[change],
            checks=[
                "exact_sheet_keys_checked",
                "active_package_graph_checked",
                "sheet_registry_read_back",
                "unmodified_package_parts_byte_identical",
            ],
            repairs=self.repairs,
            review_required=[
                "semantic_review",
                "rendered_layout_review",
                "recalculated_formula_results",
                "dynamic_string_references_and_unmodeled_dependencies",
            ],
        )
