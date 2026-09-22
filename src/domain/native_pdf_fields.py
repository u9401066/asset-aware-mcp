"""Physical PDF field identities; names are labels, never mutation selectors."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from src.domain.native_asset_models import ASSET_ID_PATTERN, SHA256_PATTERN, NativeModel
from src.domain.native_pdf import NativePdfReference  # noqa: TC001 -- runtime schema
from src.domain.native_pdf_annotations import (  # noqa: TC001 -- runtime schema
    Rectangle,
    Rgb,
)

MAX_PDF_FIELDS = 20_000
MAX_FIELD_DEPTH = 64
FIELD_REVIEW = [
    "actual_affected_page_images_and_value_appearance_consistency",
    "explicit_replacement_font_style_wrapping_and_offscreen_choices",
    "native_viewer_editing_and_appearance_regeneration",
    "preserved_actions_scripts_and_calculation_dependencies_not_executed",
    "historical_references_do_not_migrate; deletion_is_not_secure_erasure",
]
FieldIndex = Annotated[int, Field(ge=0, lt=MAX_PDF_FIELDS)]
Digest = Annotated[str, Field(pattern=SHA256_PATTERN)]


class PdfFieldLocator(NativeModel):
    """First index addresses AcroForm.Fields; subsequent indices address Kids."""

    field_path: list[FieldIndex] = Field(min_length=1, max_length=MAX_FIELD_DEPTH)
    object_id: int = Field(ge=0)
    generation: int = Field(ge=0)


class PdfFieldReference(NativeModel):
    schema_version: Literal["native-pdf-field-ref-v1"] = "native-pdf-field-ref-v1"
    asset_id: str = Field(pattern=ASSET_ID_PATTERN)
    revision: Digest
    locator: PdfFieldLocator
    value_sha256: Digest
    verification_scope: Literal["immutable_native_representation"] = (
        "immutable_native_representation"
    )


class PdfFieldStyle(NativeModel):
    """Explicit replacement style; embedded Unicode font, existing widget bounds."""

    font_size: float = Field(default=12.0, ge=1, le=144, allow_inf_nan=False)
    text_color: Rgb = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    fill_color: Rgb | None = None
    border_color: Rgb = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    border_width: float = Field(default=1.0, ge=0, le=20, allow_inf_nan=False)
    alignment: Literal[0, 1, 2] = 0


class PdfFieldTextValue(NativeModel):
    kind: Literal["text"]
    text: str = Field(max_length=65_536)

    @field_validator("text")
    @classmethod
    def valid_text(cls, value: str) -> str:
        if any(
            (ord(c) < 32 and c not in "\n\r\t") or 0xD800 <= ord(c) <= 0xDFFF
            for c in value
        ):
            raise ValueError("PDF field text contains unsupported control characters")
        return value


class PdfFieldButtonValue(NativeModel):
    kind: Literal["button"]
    state: str = Field(min_length=2, max_length=256, pattern=r"^/")

    @field_validator("state")
    @classmethod
    def valid_state(cls, value: str) -> str:
        if any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
            raise ValueError("Invalid PDF button state")
        return value


class PdfFieldChoiceValue(NativeModel):
    kind: Literal["choice"]
    indices: list[Annotated[int, Field(ge=0, lt=10_000)]] = Field(max_length=10_000)

    @model_validator(mode="after")
    def ordered(self) -> PdfFieldChoiceValue:
        if self.indices != sorted(set(self.indices)):
            raise ValueError("Choice indices must be unique and ascending")
        return self


PdfFieldValue = Annotated[
    PdfFieldTextValue | PdfFieldButtonValue | PdfFieldChoiceValue,
    Field(discriminator="kind"),
]


class PdfFieldOption(NativeModel):
    export: str = Field(max_length=4096)
    label: str = Field(max_length=4096)

    @field_validator("export", "label")
    @classmethod
    def valid_option(cls, value: str) -> str:
        return PdfFieldTextValue.valid_text(value)


class PdfFieldWidgetCreate(NativeModel):
    page_reference: NativePdfReference
    rect: Rectangle
    style: PdfFieldStyle = Field(default_factory=PdfFieldStyle)
    on_state: str | None = Field(
        default=None, min_length=2, max_length=256, pattern=r"^/"
    )

    @model_validator(mode="after")
    def geometry(self) -> PdfFieldWidgetCreate:
        if self.rect[0] >= self.rect[2] or self.rect[1] >= self.rect[3]:
            raise ValueError("Field widget rectangle must have positive area")
        if self.on_state is not None:
            PdfFieldButtonValue(kind="button", state=self.on_state)
            if self.on_state == "/Off":
                raise ValueError("Widget on_state cannot be /Off")
        return self


class PdfFieldDefinition(NativeModel):
    name: str = Field(min_length=1, max_length=4096)
    kind: Literal["text", "checkbox", "radio", "choice"]
    value: PdfFieldValue
    widgets: list[PdfFieldWidgetCreate] = Field(default_factory=list, max_length=32)
    multiline: bool = False
    multiselect: bool = False
    options: list[PdfFieldOption] = Field(default_factory=list, max_length=10_000)

    @model_validator(mode="after")
    def field_shape(self) -> PdfFieldDefinition:
        if (
            not self.name.strip()
            or "." in self.name
            or any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in self.name)
        ):
            raise ValueError(
                "New field requires one nonempty partial name without dots"
            )
        expected = "button" if self.kind in {"checkbox", "radio"} else self.kind
        if self.value.kind != expected:
            raise ValueError("Field type and value kind disagree")
        if self.kind != "text" and self.multiline:
            raise ValueError("Only text fields can be multiline")
        if self.kind != "choice" and (self.multiselect or self.options):
            raise ValueError("Only choice fields have options or multiselect")
        if self.kind == "choice" and not self.options:
            raise ValueError("Choice fields require options")
        if expected == "button":
            if not self.widgets or any(w.on_state is None for w in self.widgets):
                raise ValueError(
                    "Button fields require widgets with explicit on states"
                )
            states = [w.on_state for w in self.widgets]
            if self.kind == "checkbox" and len(set(states)) != 1:
                raise ValueError("Repeated checkbox widgets must share their on state")
            if self.kind == "radio" and len(set(states)) != len(states):
                raise ValueError("New radio widgets require distinct on states")
        elif any(w.on_state is not None for w in self.widgets):
            raise ValueError("Only button widgets have on_state")
        return self


class PdfFieldCreate(NativeModel):
    op: Literal["create"]
    field: PdfFieldDefinition
    parent_reference: PdfFieldReference | None = None
    new_groups: list[Annotated[str, Field(min_length=1, max_length=4096)]] = Field(
        default_factory=list, max_length=32
    )

    @field_validator("new_groups")
    @classmethod
    def group_names(cls, values: list[str]) -> list[str]:
        for value in values:
            if (
                not value.strip()
                or "." in value
                or any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value)
            ):
                raise ValueError(
                    "New group names must be nonempty partial names without dots"
                )
        return values


class PdfFieldWidgetStyle(NativeModel):
    widget_path: list[FieldIndex] = Field(min_length=1, max_length=MAX_FIELD_DEPTH)
    style: PdfFieldStyle


class PdfFieldUpdate(NativeModel):
    op: Literal["update"]
    reference: PdfFieldReference
    value: PdfFieldValue
    appearance_policy: Literal[
        "replace_all_widget_appearances", "preserve_native_button_states", "no_widgets"
    ]
    widget_styles: list[PdfFieldWidgetStyle] = Field(
        default_factory=list, max_length=32
    )

    @model_validator(mode="after")
    def appearance_shape(self) -> PdfFieldUpdate:
        if (
            self.appearance_policy != "replace_all_widget_appearances"
            and self.widget_styles
        ):
            raise ValueError("Widget styles require explicit appearance replacement")
        paths = [tuple(w.widget_path) for w in self.widget_styles]
        if len(set(paths)) != len(paths):
            raise ValueError("Each widget style must address one unique physical path")
        return self


class PdfFieldDelete(NativeModel):
    op: Literal["delete"]
    reference: PdfFieldReference
    scope: Literal["field_subtree_and_all_widgets"]


PdfFieldEdit = Annotated[
    PdfFieldCreate | PdfFieldUpdate | PdfFieldDelete, Field(discriminator="op")
]


class PdfFieldsUpdate(NativeModel):
    expected_catalog_sha256: Digest
    edits: list[PdfFieldEdit] = Field(min_length=1, max_length=32)
