"""Atomic native form CRUD with source references, appearance updates and inverse checks."""

from __future__ import annotations

import math
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pikepdf
import pymupdf

from src.domain.native_asset_models import NativeEditResult
from src.domain.native_pdf_fields import (
    FIELD_REVIEW,
    PdfFieldButtonValue,
    PdfFieldCreate,
    PdfFieldDelete,
    PdfFieldsUpdate,
    PdfFieldUpdate,
)
from src.infrastructure.native_pdf_annotation_edits import _base_pixels
from src.infrastructure.native_pdf_annotation_geometry import display_transforms
from src.infrastructure.native_pdf_checks import (
    checked_serialization,
    document_graph,
    page_graph,
    render_fingerprint,
    verify_reference,
)
from src.infrastructure.native_pdf_field_appearance import FieldAppearanceFactory
from src.infrastructure.native_pdf_field_journal import FieldJournal
from src.infrastructure.native_pdf_field_values import field_flags, write_value
from src.infrastructure.native_pdf_fields import FieldCatalog
from src.infrastructure.native_pdf_package import NativePdfPackage

if TYPE_CHECKING:
    from src.domain.native_pdf_fields import PdfFieldStyle
    from src.infrastructure.native_pdf_field_tree import FieldNode, FieldWidget


class FieldMutation:
    def __init__(self, package: NativePdfPackage, request: PdfFieldsUpdate):
        self.package, self.request = package, request
        self.catalog = FieldCatalog(package)
        self.before_catalog = self.catalog.inspect()
        if self.before_catalog["catalog_sha256"] != request.expected_catalog_sha256:
            raise ValueError("Stale native PDF field catalog")
        if self.catalog.tree.form.get("/NeedAppearances", False):
            raise ValueError(
                "PDF requests viewer regeneration; explicit whole-form appearance reconciliation is required"
            )
        self.mapping = package.page_map()
        self.before_pages = [page_graph(p, self.mapping) for p in package.pdf.pages]
        self.before_document = document_graph(package.pdf, self.mapping)
        self.journal = FieldJournal(package.pdf)
        self.factory = FieldAppearanceFactory(package.pdf)
        self.targets: list[tuple[Any, FieldNode | None]] = []
        self.changes: list[dict[str, Any]] = []
        self.after_targets: list[tuple[dict[str, Any], pikepdf.Object]] = []
        self.affected: set[int] = set()
        self.deleted: set[tuple[int, int]] = set()
        self.before_records: dict[tuple[int, ...], dict[str, Any]] = {}
        occupied: list[tuple[int, ...]] = []
        parents: list[tuple[int, ...]] = []
        self.transforms = display_transforms(
            package.data, set(range(len(package.pdf.pages)))
        )
        for edit in request.edits:
            if isinstance(edit, PdfFieldCreate):
                parent = (
                    self.catalog.verify(edit.parent_reference)
                    if edit.parent_reference
                    else None
                )
                if parent:
                    self._check_node(parent)
                    self.before_records[tuple(parent.locator.field_path)] = (
                        self.catalog.record(parent.locator)
                    )
                    if parent.widgets or (
                        not parent.children and parent.inherited("/FT")[0] is not None
                    ):
                        raise ValueError(
                            "Creating children requires a native nonterminal field parent"
                        )
                    parents.append(tuple(parent.locator.field_path))
                for widget in edit.field.widgets:
                    verify_reference(package, widget.page_reference)
                self.targets.append((edit, parent))
            else:
                node = self.catalog.verify(edit.reference)
                self.before_records[tuple(node.locator.field_path)] = (
                    self.catalog.record(node.locator)
                )
                if isinstance(edit, PdfFieldDelete):
                    prefix = tuple(node.locator.field_path)
                    for path, descendant in self.catalog.tree.nodes.items():
                        if path[: len(prefix)] == prefix:
                            self.before_records[path] = self.catalog.record(
                                descendant.locator
                            )
                self._check_node(node)
                path = tuple(node.locator.field_path)
                if any(
                    path[: len(other)] == other or other[: len(path)] == path
                    for other in occupied
                ):
                    raise ValueError(
                        "PDF field batch targets overlap in the original field tree"
                    )
                occupied.append(path)
                if isinstance(edit, PdfFieldUpdate) and node.children:
                    raise ValueError(
                        "Update exact terminal field references, not a group value"
                    )
                self.targets.append((edit, node))
        deleted_paths = [
            tuple(node.locator.field_path)
            for edit, node in self.targets
            if isinstance(edit, PdfFieldDelete) and node is not None
        ]
        if any(
            parent[: len(path)] == path for parent in parents for path in deleted_paths
        ):
            raise ValueError("Cannot create a child beneath a deleted field")

    def _check_node(self, node: FieldNode) -> None:
        for ancestor in (*node.ancestors, node):
            if ancestor.issues or not ancestor.obj.is_indirect:
                raise ValueError(
                    "PDF field structure requires explicit repair before mutation"
                )
        if field_flags(node) & 1:
            raise ValueError("Read-only PDF field cannot be edited or deleted")
        for widget in node.widgets:
            if (
                widget.issues
                or len(widget.occurrences) != 1
                or not widget.obj.is_indirect
            ):
                raise ValueError("PDF field widget ownership requires explicit repair")
            flags = widget.obj.get("/F", 0)
            if (
                not isinstance(flags, int)
                or isinstance(flags, bool)
                or flags & (64 | 128 | 512)
            ):
                raise ValueError(
                    "PDF field widget is locked, read-only or has invalid flags"
                )
            if "/StructParent" in widget.obj or "/StructParent" in node.obj:
                raise ValueError(
                    "Tagged PDF field mutation requires structure-tree reconciliation"
                )

    def run(self) -> tuple[bytes, NativeEditResult]:
        for edit, node in self.targets:
            before = (
                self.before_records[tuple(node.locator.field_path)] if node else None
            )
            change = {
                "operation": edit.op + "_field",
                "before": before,
                "request": edit.model_dump(mode="json", exclude_unset=True),
            }
            if isinstance(edit, PdfFieldCreate):
                created = self._create(edit, node)
                self.after_targets.append((change, created))
            elif isinstance(edit, PdfFieldUpdate):
                assert node is not None
                self._update(edit, node, change)
                self.after_targets.append((change, node.obj))
            else:
                assert node is not None
                prefix = tuple(node.locator.field_path)
                change["deleted_fields"] = [
                    record
                    for path, record in self.before_records.items()
                    if path[: len(prefix)] == prefix
                ]
                self._delete(node)
                change["secure_erasure"] = False
            self.changes.append(change)
        self.journal.check_deleted(self.deleted)
        pages = [page_graph(p, self.mapping) for p in self.package.pdf.pages]
        if (
            pages == self.before_pages
            and document_graph(self.package.pdf, self.mapping) == self.before_document
        ):
            return self.package.data, self._report(False)
        after_tree = FieldCatalog(self.package).tree
        after_paths = {node.obj.objgen: path for path, node in after_tree.nodes.items()}
        planned = [
            (change, after_paths[obj.objgen]) for change, obj in self.after_targets
        ]
        data = checked_serialization(
            self.package.pdf, list(self.mapping.values()), self.package.pdf.pdf_version
        )
        self.journal.undo()
        if [
            page_graph(p, self.mapping) for p in self.package.pdf.pages
        ] != self.before_pages or document_graph(
            self.package.pdf, self.mapping
        ) != self.before_document:
            raise ValueError("PDF changed outside the explicit field edit plan")
        if _base_pixels(data) != _base_pixels(self.package.data):
            raise ValueError("PDF form edit changed underlying page pixels")
        for index in range(len(self.package.pdf.pages)):
            if index not in self.affected and render_fingerprint(
                data, index
            ) != render_fingerprint(self.package.data, index):
                raise ValueError("PDF form edit changed an untouched page")
        with NativePdfPackage(data) as reopened:
            final = FieldCatalog(reopened)
            for change, path in planned:
                change["after"] = final.record(final.tree.nodes[path].locator)
            after = final.inspect()
        result = self._report(True)
        result.changes.append(
            {
                "operation": "field_catalog_readback",
                "before_catalog_sha256": self.before_catalog["catalog_sha256"],
                "after_catalog": after,
                "affected_pages": sorted(self.affected),
                "action_policy": "preserved_without_execution",
            }
        )
        return data, result

    def _form(self) -> pikepdf.Object:
        form = self.package.pdf.Root.get("/AcroForm")
        if form is None:
            form = self.package.pdf.make_indirect(
                pikepdf.Dictionary(Fields=pikepdf.Array())
            )
            self.journal.set_key(self.package.pdf.Root, "/AcroForm", form)
        if "/Fields" not in form:
            self.journal.set_key(form, "/Fields", pikepdf.Array())
        return form

    def _create(self, edit: PdfFieldCreate, parent: FieldNode | None) -> pikepdf.Object:
        form = self._form()
        spec = edit.field
        parent_obj = parent.obj if parent else None
        if parent_obj is not None and "/Kids" not in parent_obj:
            self.journal.set_key(parent_obj, "/Kids", pikepdf.Array())
        siblings = parent_obj.Kids if parent_obj is not None else form.Fields
        for name in edit.new_groups:
            if any(
                isinstance(sibling.get("/T"), pikepdf.String) and str(sibling.T) == name
                for sibling in siblings
            ):
                raise ValueError("New PDF group name collides with an existing sibling")
            group = self.package.pdf.make_indirect(
                pikepdf.Dictionary(T=pikepdf.String(name), Kids=pikepdf.Array())
            )
            if parent_obj is not None:
                group.Parent = parent_obj
            self.journal.array(siblings, [*siblings, group])
            parent_obj, siblings = group, group.Kids
        if any(
            isinstance(obj.get("/T"), pikepdf.String) and str(obj.T) == spec.name
            for obj in siblings
        ):
            raise ValueError("New PDF field name collides with an existing sibling")
        obj = self.package.pdf.make_indirect(
            pikepdf.Dictionary(
                T=pikepdf.String(spec.name),
                FT=pikepdf.Name(
                    {
                        "text": "/Tx",
                        "choice": "/Ch",
                        "radio": "/Btn",
                        "checkbox": "/Btn",
                    }[spec.kind]
                ),
                Ff=(4096 if spec.multiline else 0)
                | (2097152 if spec.multiselect else 0)
                | (32768 if spec.kind == "radio" else 0),
            )
        )
        if spec.options:
            obj.Opt = pikepdf.Array(
                [pikepdf.Array([v.export, v.label]) for v in spec.options]
            )
        if parent_obj is not None:
            obj.Parent = parent_obj
        self.journal.array(siblings, [*siblings, obj])
        widgets = []
        styles = {}
        for specification in spec.widgets:
            index = specification.page_reference.locator.page_index
            page = self.package.pdf.pages[index]
            transform = self.transforms[index]
            matrix = ~pymupdf.Matrix(transform["matrix"])
            rect = specification.rect
            first = (
                pymupdf.Point(
                    rect[0] * transform["width"], rect[1] * transform["height"]
                )
                * matrix
            )
            second = (
                pymupdf.Point(
                    rect[2] * transform["width"], rect[3] * transform["height"]
                )
                * matrix
            )
            native = list(pymupdf.Rect(first, second).normalize())
            widget = self.package.pdf.make_indirect(
                pikepdf.Dictionary(
                    Type=pikepdf.Name.Annot,
                    Subtype=pikepdf.Name.Widget,
                    Parent=obj,
                    P=page.obj,
                    Rect=pikepdf.Array(native),
                    F=4,
                )
            )
            if "/Annots" not in page.obj:
                self.journal.set_key(page.obj, "/Annots", pikepdf.Array())
            self.journal.array(page.obj.Annots, [*page.obj.Annots, widget])
            if isinstance(spec.value, PdfFieldButtonValue):
                unit = float(page.obj.get("/UserUnit", 1))
                off, _ = self.factory.create(
                    native,
                    specification.style,
                    user_unit=unit,
                    checked=False,
                    radio=spec.kind == "radio",
                )
                on, _ = self.factory.create(
                    native,
                    specification.style,
                    user_unit=unit,
                    checked=True,
                    radio=spec.kind == "radio",
                )
                widget.AP = pikepdf.Dictionary(
                    N=pikepdf.Dictionary({"/Off": off, specification.on_state: on})
                )
                widget.AS = pikepdf.Name.Off
            widgets.append(widget)
            styles[widget.objgen] = specification.style
            self.affected.add(index)
        if widgets:
            obj.Kids = pikepdf.Array(widgets)
        current = FieldCatalog(self.package)
        node = next(
            n for n in current.tree.nodes.values() if n.obj.objgen == obj.objgen
        )
        layout = write_value(node, spec.value, self.journal)
        if not isinstance(spec.value, PdfFieldButtonValue):
            for field_widget in node.widgets:
                self._appearance(field_widget, styles[field_widget.obj.objgen], layout)
        return obj

    def _update(
        self, edit: PdfFieldUpdate, node: FieldNode, change: dict[str, Any]
    ) -> None:
        if not node.widgets:
            if edit.appearance_policy != "no_widgets":
                raise ValueError("Nonvisual field update requires no_widgets policy")
        elif isinstance(edit.value, PdfFieldButtonValue):
            if edit.appearance_policy != "preserve_native_button_states":
                raise ValueError("Button update must preserve native appearance states")
        elif edit.appearance_policy != "replace_all_widget_appearances":
            raise ValueError(
                "Visible text/choice values require explicit appearance replacement"
            )
        styles = {tuple(w.widget_path): w.style for w in edit.widget_styles}
        if edit.appearance_policy == "replace_all_widget_appearances" and set(
            styles
        ) != {w.path for w in node.widgets}:
            raise ValueError(
                "Appearance replacement must specify every original widget exactly once"
            )
        layout = write_value(node, edit.value, self.journal)
        change["value_layout"] = layout
        for widget in node.widgets:
            self.affected.add(widget.occurrences[0].page.page_index)
            if edit.appearance_policy == "replace_all_widget_appearances":
                self._appearance(widget, styles[widget.path], layout)

    def _appearance(
        self, widget: FieldWidget, style: PdfFieldStyle, layout: dict[str, Any]
    ) -> None:
        obj = widget.obj
        rectangle = obj.get("/Rect")
        if not isinstance(rectangle, pikepdf.Array) or len(rectangle) != 4:
            raise ValueError("PDF widget has invalid rectangle")
        if any(
            not isinstance(v, (int, float, Decimal)) or isinstance(v, bool)
            for v in rectangle
        ):
            raise ValueError("PDF widget rectangle contains nonnumeric native values")
        coordinates = [float(v) for v in rectangle]
        if not all(math.isfinite(v) for v in coordinates):
            raise ValueError("PDF widget has nonfinite rectangle")
        index = widget.occurrences[0].page.page_index
        page = self.package.pdf.pages[index]
        unit = float(page.obj.get("/UserUnit", 1))
        mk = obj.get("/MK", pikepdf.Dictionary())
        if not isinstance(mk, pikepdf.Dictionary):
            raise ValueError("PDF widget has invalid appearance characteristics")
        rotation = mk.get("/R", 0)
        if not isinstance(rotation, int) or isinstance(rotation, bool):
            raise ValueError("PDF widget has invalid appearance rotation")
        ap, font = self.factory.create(
            coordinates,
            style,
            user_unit=unit,
            rotation=rotation % 360,
            text=layout.get("text", ""),
            choices=layout.get("choices"),
            comb=layout.get("comb"),
            multiline=layout.get("multiline", False),
        )
        # Explicitly replace ALL appearance states, avoiding stale rollover/down text.
        self.journal.set_key(obj, "/AP", pikepdf.Dictionary(N=ap))
        self.journal.set_key(obj, "/AS", None)
        self.journal.set_key(obj, "/Q", style.alignment)
        characteristics = pikepdf.Dictionary(
            {key: value for key, value in mk.items() if value is not None}
        )
        characteristics.BC = pikepdf.Array(style.border_color)
        if style.fill_color is None:
            if "/BG" in characteristics:
                del characteristics.BG
        else:
            characteristics.BG = pikepdf.Array(style.fill_color)
        self.journal.set_key(obj, "/MK", characteristics)
        self.journal.set_key(
            obj,
            "/BS",
            pikepdf.Dictionary(W=style.border_width / unit, S=pikepdf.Name.S),
        )
        self.journal.set_key(obj, "/Border", None)
        if font is not None:
            form = self._form()
            resources = form.get("/DR", pikepdf.Dictionary())
            if not isinstance(resources, pikepdf.Dictionary) or not isinstance(
                resources.get("/Font", pikepdf.Dictionary()), pikepdf.Dictionary
            ):
                raise ValueError("PDF form has invalid font resources")
            dr = pikepdf.Dictionary(
                {key: value for key, value in resources.items() if value is not None}
            )
            fonts = pikepdf.Dictionary(
                {
                    key: value
                    for key, value in resources.get(
                        "/Font", pikepdf.Dictionary()
                    ).items()
                    if value is not None
                }
            )
            name = next(
                (
                    key
                    for key, existing in fonts.items()
                    if existing.is_indirect and existing.objgen == font.objgen
                ),
                None,
            )
            if name is None:
                serial = 0
                while f"/AAField{serial}" in fonts:
                    serial += 1
                name = f"/AAField{serial}"
                fonts[name] = font
                dr.Font = fonts
                self.journal.set_key(form, "/DR", dr)
            da = (
                f"{name} {style.font_size / unit:.10g} Tf "
                + " ".join(format(v, ".10g") for v in style.text_color)
                + " rg"
            )
            self.journal.set_key(obj, "/DA", pikepdf.String(da))

    def _delete(self, node: FieldNode) -> None:
        prefix = tuple(node.locator.field_path)
        deleting = [
            n
            for path, n in self.catalog.tree.nodes.items()
            if path[: len(prefix)] == prefix
        ]
        removed = set()
        for item in deleting:
            self._check_node(item)
            removed.add(item.obj.objgen)
            for widget in item.widgets:
                removed.add(widget.obj.objgen)
                self.affected.add(widget.occurrences[0].page.page_index)
        parent = node.ancestors[-1].obj if node.ancestors else self._form()
        key = "/Kids" if node.ancestors else "/Fields"
        self.journal.array(
            parent[key], [v for v in parent[key] if v.objgen not in removed]
        )
        for index in self.affected:
            page = self.package.pdf.pages[index]
            if "/Annots" in page.obj:
                survivors = [
                    obj for obj in page.obj.Annots if obj.objgen not in removed
                ]
                if len(survivors) != len(page.obj.Annots):
                    self.journal.array(page.obj.Annots, survivors)
        self.deleted.update(removed)

    def _report(self, changed: bool) -> NativeEditResult:
        return NativeEditResult(
            changed_parts=["pdf:explicit-fields-and-widgets"] if changed else [],
            preserved_parts=len(self.package.pdf.pages)
            - (len(self.affected) if changed else 0),
            changes=self.changes if changed else [],
            checks=[
                "full_revision_field_page_and_catalog_references",
                "field_widget_ownership_and_native_dependencies",
                "inverse_native_graph_preservation",
                "serialized_graph_readback",
                "independent_512_pixel_base_content_and_untouched_pages",
            ]
            if changed
            else [
                "full_revision_field_page_and_catalog_references",
                "unchanged_native_graph_no_serialization",
            ],
            repairs=["canonicalized_equal_duplicate_stream_lengths"]
            if changed and self.package.parser_checks
            else [],
            review_required=FIELD_REVIEW,
        )


def edit_fields(
    data: bytes, request: PdfFieldsUpdate
) -> tuple[bytes, NativeEditResult]:
    with NativePdfPackage(data) as package:
        package.check_editable()
        return FieldMutation(package, request).run()
