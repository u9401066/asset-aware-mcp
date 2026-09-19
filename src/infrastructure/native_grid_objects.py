"""Bind worksheet notes/drawings to exact package relationships before moving them."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.domain.native_asset_models import cell_position
from src.infrastructure.native_grid_drawings import shift_drawing
from src.infrastructure.native_grid_metrics import GridMetrics
from src.infrastructure.native_grid_vml import VNS, note_location, shift_vml
from src.infrastructure.native_grid_xml import shift_cell, tag
from src.infrastructure.native_ooxml import DOC_REL_NS, relationships_path
from src.infrastructure.native_spreadsheet_reader import NS

if TYPE_CHECKING:
    from lxml import etree

    from src.domain.native_grid import GridTransform, NativeGridUpdate
    from src.domain.native_grid_geometry import GridAxisMetrics
    from src.infrastructure.native_workbook_plan import WorkbookPlan


class GridObjects:
    def __init__(self, plan: WorkbookPlan, worksheet: str, request: NativeGridUpdate):
        self.plan, self.root = plan, plan.roots[worksheet]
        self.metrics = GridMetrics(plan, request)
        self.drawings: dict[str, etree._Element] = {}
        self.vml: dict[str, etree._Element] = {}
        self.comments: dict[str, etree._Element] = {}
        relations = (
            plan.book.package.relationships(worksheet)
            if relationships_path(worksheet) in plan.book.package.parts
            else {}
        )
        used = set()
        for local, kind, destination in (
            ("drawing", "drawing", self.drawings),
            ("legacyDrawing", "vmlDrawing", self.vml),
        ):
            for node in self.root.findall("s:" + local, NS):
                rid = node.get(f"{{{DOC_REL_NS}}}id", "")
                relation = relations.get(rid)
                if (
                    rid in used
                    or relation is None
                    or relation[0] != DOC_REL_NS + "/" + kind
                    or not relation[1]
                ):
                    raise ValueError(
                        "Missing or ambiguous worksheet drawing relationship"
                    )
                used.add(rid)
                destination[relation[1]] = plan.part(relation[1])
        for kind, part in relations.values():
            if kind == DOC_REL_NS + "/comments":
                if not part:
                    raise ValueError("Native worksheet comments cannot be external")
                self.comments[part] = plan.part(part)
            if kind.endswith("/threadedComment"):
                raise ValueError(
                    "Threaded comments require identity-aware conversation relocation"
                )
        if len(self.comments) > 1:
            raise ValueError("Multiple worksheet comments parts are ambiguous")
        owned = set(self.drawings) | set(self.vml) | set(self.comments)
        for sheet in plan.book.entries:
            other = sheet["key"]["part"]
            if (
                other != worksheet
                and relationships_path(other) in plan.book.package.parts
                and any(
                    part in owned
                    for _, part in plan.book.package.relationships(other).values()
                )
            ):
                raise ValueError(
                    "Shared worksheet drawings/notes cannot be relocated independently"
                )
        self._check_notes()

    def _check_notes(self) -> None:
        locations: set[str] = set()
        for root in self.comments.values():
            if (
                root.tag != tag("comments")
                or len(root.findall("s:commentList", NS)) != 1
            ):
                raise ValueError("Invalid native comments structure")
            for node in root.findall("s:commentList/s:comment", NS):
                location = node.get("ref", "")
                cell_position(location)
                if location in locations or len(locations) >= 10_000:
                    raise ValueError(
                        "Duplicate comments or comment inspection budget exceeded"
                    )
                locations.add(location)
        shapes = set()
        for root in self.vml.values():
            for data in root.findall("v:shape/x:ClientData", VNS):
                location = note_location(data)
                if location is not None:
                    if location not in locations or location in shapes:
                        raise ValueError(
                            "Legacy note shape does not match a unique comment cell"
                        )
                    shapes.add(location)

    def before(
        self, transform: GridTransform
    ) -> tuple[GridAxisMetrics, dict[str, Any]] | None:
        if not self.drawings and not self.vml:
            return None
        return self.metrics.axis(self.root, transform.edit.axis)

    def apply(
        self,
        transform: GridTransform,
        before: tuple[GridAxisMetrics, dict[str, Any]] | None,
    ) -> dict[str, Any]:
        changes: dict[str, Any] = {"comments": [], "drawings": {}, "vml": {}}
        for part, root in self.comments.items():
            for node in root.findall("s:commentList/s:comment", NS):
                original = node.get("ref", "")
                moved = shift_cell(original, transform)
                if moved is None:
                    node.getparent().remove(node)
                elif moved != original:
                    node.set("ref", moved)
                if moved != original:
                    changes["comments"].append(
                        {"part": part, "before_cell": original, "after_cell": moved}
                    )
        if before is not None:
            after, metadata = self.metrics.axis(self.root, transform.edit.axis)
            changes["metrics"] = {"before": before[1], "after": metadata}
            for part, root in self.drawings.items():
                changes["drawings"][part] = shift_drawing(
                    root, transform, before[0], after
                )
            for part, root in self.vml.items():
                changes["vml"][part] = shift_vml(root, transform, before[0], after)
        self._check_notes()
        return changes
