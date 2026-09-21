"""Revision-bound PDF annotations and explicit appearance replacement intent."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import ConfigDict, Field, model_validator

from src.domain.native_asset_models import ASSET_ID_PATTERN, SHA256_PATTERN, NativeModel
from src.domain.native_pdf import (  # noqa: TC001 -- Pydantic runtime schema
    NativePdfPageLocator,
    NativePdfReference,
)

Fraction = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
Point = Annotated[list[Fraction], Field(min_length=2, max_length=2)]
Rectangle = Annotated[list[Fraction], Field(min_length=4, max_length=4)]
Rgb = Annotated[list[Fraction], Field(min_length=3, max_length=3)]
Quad = Annotated[list[Fraction], Field(min_length=8, max_length=8)]
Digest = Annotated[str, Field(pattern=SHA256_PATTERN)]
ANNOTATION_REVIEW = [
    "semantic_accuracy",
    "actual_page_rendering_and_annotation_appearance",
    "popup_reply_and_viewer_behavior",
    "highlight_geometry_is_not_a_text_transcription",
    "historical_references_do_not_migrate",
]


class PdfAnnotationLocator(NativeModel):
    page: NativePdfPageLocator
    annotation_index: int = Field(ge=0, lt=20_000)
    object_id: int = Field(ge=0)
    generation: int = Field(ge=0)


class PdfAnnotationReference(NativeModel):
    schema_version: Literal["native-pdf-annotation-ref-v1"] = (
        "native-pdf-annotation-ref-v1"
    )
    asset_id: str = Field(pattern=ASSET_ID_PATTERN)
    revision: Digest
    locator: PdfAnnotationLocator
    value_sha256: Digest
    verification_scope: Literal["immutable_native_representation"] = (
        "immutable_native_representation"
    )


class PdfAnnotationMetadata(NativeModel):
    """Omitted keys stay untouched; explicit null removes the native key."""

    contents: str | None = Field(default=None, max_length=65_536)
    author: str | None = Field(default=None, max_length=4096)
    subject: str | None = Field(default=None, max_length=4096)
    modified: str | None = Field(default=None, max_length=256)


def appearance_fields(kind: str) -> tuple[str, set[str]]:
    geometry = {
        "Text": "point",
        "FreeText": "rect",
        "Square": "rect",
        "Circle": "rect",
        "Line": "vertices",
        "PolyLine": "vertices",
        "Polygon": "vertices",
        "Ink": "strokes",
    }.get(kind, "quads")
    allowed = {"kind", geometry, "opacity", "stroke_color"}
    if kind == "Text":
        allowed.add("icon")
    if kind in {"FreeText", "Square", "Circle", "Polygon"}:
        allowed.add("fill_color")
    if kind in {"FreeText", "Square", "Circle", "Polygon", "PolyLine", "Line", "Ink"}:
        allowed.add("border_width")
    if kind == "FreeText":
        allowed.update({"text", "font_size", "text_color"})
    return geometry, allowed


def appearance_schema(schema: dict[str, Any]) -> None:
    branches = []
    for kind in schema["properties"]["kind"]["enum"]:
        geometry, allowed = appearance_fields(kind)
        positions: dict[str, Any] = {"not": {"type": "null"}, "minItems": 1}
        if geometry == "vertices":
            positions["minItems"] = 3 if kind == "Polygon" else 2
        if kind == "Line":
            positions["maxItems"] = 2
        branches.append(
            {
                "required": [geometry],
                "properties": {"kind": {"const": kind}, geometry: positions},
                "not": {
                    "anyOf": [
                        {"required": [name]}
                        for name in schema["properties"]
                        if name not in allowed
                    ]
                },
            }
        )
    schema["oneOf"] = branches


class PdfAnnotationAppearance(NativeModel):
    """Coordinates are fractions of the displayed, rotated CropBox."""

    model_config = ConfigDict(json_schema_extra=appearance_schema)

    kind: Literal[
        "Text",
        "FreeText",
        "Highlight",
        "Underline",
        "StrikeOut",
        "Squiggly",
        "Square",
        "Circle",
        "Line",
        "PolyLine",
        "Polygon",
        "Ink",
    ]
    point: Point | None = None
    rect: Rectangle | None = None
    vertices: list[Point] = Field(default_factory=list, max_length=2000)
    quads: list[Quad] = Field(default_factory=list, max_length=1000)
    strokes: list[Annotated[list[Point], Field(min_length=2, max_length=2000)]] = Field(
        default_factory=list, max_length=100
    )
    text: str = Field(default="", max_length=65_536)
    font_size: float = Field(default=12.0, ge=1, le=144, allow_inf_nan=False)
    text_color: Rgb = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    stroke_color: Rgb = Field(default_factory=lambda: [1.0, 0.0, 0.0])
    fill_color: Rgb | None = None
    opacity: Fraction = 1.0
    border_width: float = Field(default=1.0, ge=0, le=100, allow_inf_nan=False)
    icon: Literal[
        "Note",
        "Comment",
        "Key",
        "Help",
        "NewParagraph",
        "Paragraph",
        "Insert",
        "Cross",
        "Circle",
    ] = "Note"

    @model_validator(mode="after")
    def geometry_and_scope(self) -> PdfAnnotationAppearance:
        geometry, allowed = appearance_fields(self.kind)
        if not getattr(self, geometry):
            raise ValueError(f"{self.kind} requires {geometry}")
        if self.model_fields_set - allowed:
            raise ValueError("Appearance fields are not used by this annotation kind")
        if self.rect and (self.rect[0] >= self.rect[2] or self.rect[1] >= self.rect[3]):
            raise ValueError("Annotation rectangle must have positive area")
        if self.kind == "Line" and len(self.vertices) != 2:
            raise ValueError("Line requires exactly two vertices")
        if self.kind in {"PolyLine", "Polygon"} and len(self.vertices) < (
            3 if self.kind == "Polygon" else 2
        ):
            raise ValueError("Annotation has insufficient vertices")
        if sum(len(stroke) for stroke in self.strokes) > 20_000:
            raise ValueError("Ink annotation exceeds the aggregate point limit")
        return self


class PdfAnnotationCreate(NativeModel):
    op: Literal["create"]
    page_reference: NativePdfReference
    appearance: PdfAnnotationAppearance
    metadata: PdfAnnotationMetadata = Field(default_factory=PdfAnnotationMetadata)


class PdfAnnotationUpdate(NativeModel):
    op: Literal["update"]
    reference: PdfAnnotationReference
    metadata: PdfAnnotationMetadata = Field(default_factory=PdfAnnotationMetadata)
    replace_appearance: PdfAnnotationAppearance | None = None

    @model_validator(mode="after")
    def nonempty(self) -> PdfAnnotationUpdate:
        if not self.metadata.model_fields_set and self.replace_appearance is None:
            raise ValueError(
                "Annotation update requires metadata or explicit appearance"
            )
        return self


class PdfAnnotationDelete(NativeModel):
    op: Literal["delete"]
    reference: PdfAnnotationReference
    scope: Literal["annotation_and_owned_popup"]


PdfAnnotationEdit = Annotated[
    PdfAnnotationCreate | PdfAnnotationUpdate | PdfAnnotationDelete,
    Field(discriminator="op"),
]


class PdfAnnotationsUpdate(NativeModel):
    edits: list[PdfAnnotationEdit] = Field(min_length=1, max_length=32)
