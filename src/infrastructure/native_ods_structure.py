"""Native ODS structural transactions, preserving exact untouched package members."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lxml import etree

from src.domain.native_asset_models import NativeEditResult
from src.domain.native_ods_references import ODSSheetRename
from src.infrastructure.native_odf_package import NS, q, xml_bytes
from src.infrastructure.native_ods_dependencies import ODSDependencies
from src.infrastructure.native_ods_editor import _invalidate_caches, _read_cache_changes
from src.infrastructure.native_ods_reader import NativeODSReader

if TYPE_CHECKING:
    from src.domain.native_ods import NativeODSTableRename


def rename_ods_table(
    data: bytes, request: NativeODSTableRename
) -> tuple[bytes, NativeEditResult]:
    book = NativeODSReader(data)
    if request.table_index >= len(book.tables):
        raise ValueError("ODS table index is absent")
    table = book.tables[request.table_index]
    if table.get(q("table", "name")) != request.table_name:
        raise ValueError("ODS table name does not match its original index")
    dependencies = ODSDependencies(book)
    if dependencies.catalog()["inventory_sha256"] != request.dependencies_sha256:
        raise ValueError(
            "ODS dependency inventory changed; read it completely before editing"
        )
    if book.package.signed:
        raise ValueError("Signed ODS packages require a signature-aware workflow")
    if request.new_name == request.table_name:
        return data, NativeEditResult(
            changed_parts=[],
            preserved_parts=len(book.package.parts),
            changes=[],
            checks=[
                "original_table_identity_verified",
                "original_dependency_inventory_verified",
                "no_op_original_bytes_retained",
            ],
            review_required=[],
        )
    if any(
        name.casefold() == request.new_name.casefold()
        for name in dependencies.sheet_names
        if name != request.table_name
    ):
        raise ValueError("Renamed ODS table collides with an existing table identity")
    if book.body.get(q("table", "structure-protected")) in {"true", "1"} or table.get(
        q("table", "protected")
    ) in {"true", "1"}:
        raise ValueError(
            "Protected ODS structure requires an explicit protection workflow"
        )
    if book.body.find(".//table:tracked-changes", NS) is not None:
        raise ValueError("Tracked ODS changes require a revision-aware transaction")
    plan = dependencies.plan(ODSSheetRename(request.table_name, request.new_name))
    if plan.unresolved:
        first = plan.unresolved[0]
        target = first.get("dependency", first)
        raise ValueError(
            f"ODS rename has {len(plan.unresolved)} unresolved dependency owner(s): "
            f"{target.get('part', '')} {target.get('path', '')}: {first['reason']}; "
            "read_ods_dependencies retains the full native inventory"
        )
    for change in plan.changes:
        node = dependencies.nodes[change.dependency.key]
        if any(
            current.get(q("table", "protected")) in {"true", "1"}
            for current in (node, *node.iterancestors())
        ):
            raise ValueError(
                "Protected ODS dependency requires a protection-aware transaction"
            )
    before_attributes = dict(table.attrib)
    dependency_changes = dependencies.apply(plan)
    table.set(q("table", "name"), request.new_name)
    cache_changes = _invalidate_caches(book)
    for cache_change in cache_changes:
        # Cache records describe the intermediate native cell AFTER reference
        # mapping and table rename, not an original-revision evidence reference.
        cache_change["record_scope"] = "after_dependency_mapping_and_table_rename"
    replacements = {**dependencies.replacements(), "content.xml": xml_bytes(book.root)}
    result = book.package.replace(replacements)
    checked = NativeODSReader(result)
    for part, root in {**dependencies.roots, "content.xml": book.root}.items():
        if etree.tostring(checked.package.xml(part), method="c14n") != etree.tostring(
            root, method="c14n"
        ):
            raise ValueError("ODS output XML differs from the structural edit plan")
    if checked.tables[request.table_index].get(q("table", "name")) != request.new_name:
        raise ValueError("ODS renamed table failed native read-back")
    if cache_changes:
        _read_cache_changes(checked, cache_changes)
    current_dependencies = ODSDependencies(checked)
    if current_dependencies.plan(
        ODSSheetRename(request.new_name, request.new_name)
    ).unresolved:
        raise ValueError("ODS renamed dependencies failed native read-back")
    return result, NativeEditResult(
        changed_parts=sorted(replacements),
        preserved_parts=len(book.package.parts) - len(replacements),
        changes=[
            {
                "operation": "rename_ods_table",
                "table_index": request.table_index,
                "before_attributes": before_attributes,
                "after_attributes": dict(checked.tables[request.table_index].attrib),
                "dependencies_before_sha256": request.dependencies_sha256,
                "dependencies_after_sha256": current_dependencies.catalog()[
                    "inventory_sha256"
                ],
            },
            *dependency_changes,
            *cache_changes,
        ],
        checks=[
            "original_table_identity_verified",
            "original_dependency_inventory_verified",
            "all_planned_native_dependencies_read_back",
            "output_xml_matches_edit_plan",
            "untouched_package_members_byte_identical",
            "repetition_not_expanded",
        ],
        repairs=["invalidated_typed_formula_caches"] if cache_changes else [],
        review_required=[
            "semantic_accuracy",
            "rendered_layout",
            "formula_recalculation_and_results",
            "literal_and_dynamic_formula_references",
            "chart_data_and_cached_appearance",
        ],
    )
