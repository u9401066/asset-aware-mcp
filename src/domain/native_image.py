"""Revision-bound raster frames and visual regions, independent of decoding IO."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, Literal, Protocol

from pydantic import Field, field_validator, model_validator

from src.domain.native_asset_models import ASSET_ID_PATTERN, SHA256_PATTERN, NativeModel
from src.domain.native_file_reference import (
    NativeFileReference,  # noqa: TC001 -- Pydantic schema
)

if TYPE_CHECKING:
    from src.domain.native_asset_models import NativeEditResult

MAX_IMAGE_FRAMES = 128
MAX_FRAME_PIXELS = 32_000_000
MAX_DOCUMENT_PIXELS = 64_000_000
MAX_IMAGE_METADATA_BYTES = 1024 * 1024
IMAGE_FORMATS = ("PNG", "JPEG", "TIFF", "GIF", "WEBP", "BMP", "AVIF")
IMAGE_EXTENSIONS = frozenset(
    {"png", "jpg", "jpeg", "tif", "tiff", "gif", "webp", "bmp", "avif"}
)


class NativeImageFrameLocator(NativeModel):
    frame_index: int = Field(ge=0, lt=MAX_IMAGE_FRAMES)


class NativeImageFrameReference(NativeModel):
    schema_version: Literal["native-image-frame-ref-v1"] = "native-image-frame-ref-v1"
    asset_id: str = Field(pattern=ASSET_ID_PATTERN)
    revision: str = Field(pattern=SHA256_PATTERN)
    locator: NativeImageFrameLocator
    value_sha256: str = Field(pattern=SHA256_PATTERN)
    verification_scope: Literal["immutable_decoded_image_frame"] = (
        "immutable_decoded_image_frame"
    )


Fraction = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class NativeImageRegionSelector(NativeModel):
    coordinate_system: Literal["displayed_frame_fraction"] = "displayed_frame_fraction"
    rect: list[Fraction] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def ordered(self) -> NativeImageRegionSelector:
        x0, y0, x1, y1 = self.rect
        if x0 >= x1 or y0 >= y1:
            raise ValueError("Image region must be a nonempty ordered rectangle")
        return self


class NativeImageRegionReference(NativeModel):
    schema_version: Literal["native-image-region-ref-v1"] = "native-image-region-ref-v1"
    asset_id: str = Field(pattern=ASSET_ID_PATTERN)
    revision: str = Field(pattern=SHA256_PATTERN)
    parent: NativeImageFrameReference
    selector: NativeImageRegionSelector
    value_sha256: str = Field(pattern=SHA256_PATTERN)
    verification_scope: Literal["immutable_image_frame_region"] = (
        "immutable_image_frame_region"
    )

    @model_validator(mode="after")
    def identity(self) -> NativeImageRegionReference:
        if (self.asset_id, self.revision) != (
            self.parent.asset_id,
            self.parent.revision,
        ):
            raise ValueError(
                "Image region identity must match its complete frame reference"
            )
        return self


ImageColorPolicy = Literal["embedded_to_srgb", "unmanaged"]


class NativeImageBlank(NativeModel):
    name: str = Field(min_length=5, max_length=200)
    width: int = Field(ge=1, le=32_000)
    height: int = Field(ge=1, le=32_000)
    rgba: list[Annotated[int, Field(ge=0, le=255)]] = Field(min_length=4, max_length=4)

    @field_validator("name")
    @classmethod
    def basename(cls, value: str) -> str:
        if not value.lower().endswith(".png") or any(c in value for c in "/\\:\x00"):
            raise ValueError("Blank image name must be a PNG basename")
        return value

    @model_validator(mode="after")
    def area(self) -> NativeImageBlank:
        if self.width * self.height > MAX_FRAME_PIXELS:
            raise ValueError("Blank image exceeds its pixel limit")
        return self


class NativeImageExtract(NativeModel):
    name: str = Field(min_length=5, max_length=200)
    reference: NativeImageFrameReference
    region: NativeImageRegionSelector | None = None
    pixel_policy: Literal["preserve_decoded", "srgb_rgba8"]
    metadata_policy: Literal["pixels_only"]

    @field_validator("name")
    @classmethod
    def basename(cls, value: str) -> str:
        if not value.lower().endswith((".png", ".tif", ".tiff")) or any(
            c in value for c in "/\\:\x00"
        ):
            raise ValueError("Image extraction name must be a PNG/TIFF basename")
        return value


class NativeImageFrameInput(NativeModel):
    reference: NativeImageFrameReference
    region: NativeImageRegionSelector | None = None
    pixel_policy: Literal["preserve_decoded", "srgb_rgba8"]


class NativeImageCompose(NativeModel):
    name: str = Field(min_length=5, max_length=200)
    frames: list[NativeImageFrameInput] = Field(
        min_length=1, max_length=MAX_IMAGE_FRAMES
    )
    metadata_policy: Literal["pixels_only"]

    @field_validator("name")
    @classmethod
    def basename(cls, value: str) -> str:
        if not value.lower().endswith((".tif", ".tiff")) or any(
            c in value for c in "/\\:\x00"
        ):
            raise ValueError("Image composition name must be a TIFF basename")
        return value


class NativeImageFrameMap(NativeModel):
    op: Literal["map"] = "map"
    before: NativeImageFrameReference
    after: NativeImageFrameReference
    pixels: Literal["preserve_decoded", "replace"] = "preserve_decoded"
    metadata: Literal["preserve_decoder_metadata", "replace"] = (
        "preserve_decoder_metadata"
    )


class NativeImageFrameInsert(NativeModel):
    op: Literal["insert"] = "insert"
    after: NativeImageFrameReference


class NativeImageFrameDelete(NativeModel):
    op: Literal["delete"] = "delete"
    before: NativeImageFrameReference


NativeImageFrameChange = Annotated[
    NativeImageFrameMap | NativeImageFrameInsert | NativeImageFrameDelete,
    Field(discriminator="op"),
]


class NativeImageRevisionPlan(NativeModel):
    candidate: NativeFileReference
    expected_catalog_sha256: str = Field(pattern=SHA256_PATTERN)
    frames: list[NativeImageFrameChange] = Field(
        min_length=1, max_length=2 * MAX_IMAGE_FRAMES
    )
    container_policy: Literal["accept_exact_candidate_bytes"]


class NativeImageAdapter(Protocol):
    def records(self, data: bytes) -> list[dict[str, Any]]: ...
    def create(self, request: NativeImageBlank) -> tuple[bytes, NativeEditResult]: ...
    def compose(
        self, request: NativeImageCompose, sources: dict[str, bytes]
    ) -> tuple[bytes, NativeEditResult]: ...
    def extract(
        self, data: bytes, request: NativeImageExtract
    ) -> tuple[bytes, NativeEditResult]: ...
    def accept_candidate(
        self,
        data: bytes,
        candidate: bytes,
        request: NativeImageRevisionPlan,
        asset_id: str,
    ) -> tuple[bytes, NativeEditResult]: ...
    def inspect(self, data: bytes) -> dict[str, Any]: ...
    def read_frame(
        self, data: bytes, locator: NativeImageFrameLocator
    ) -> dict[str, Any]: ...
    def decompose(
        self, data: bytes, color_policy: ImageColorPolicy = "embedded_to_srgb"
    ) -> list[dict[str, Any]]: ...
    def render(
        self,
        data: bytes,
        locator: NativeImageFrameLocator,
        size: int,
        color_policy: ImageColorPolicy = "embedded_to_srgb",
    ) -> dict[str, Any]: ...
    def render_region(
        self,
        data: bytes,
        locator: NativeImageFrameLocator,
        selector: NativeImageRegionSelector,
        size: int,
        color_policy: ImageColorPolicy = "embedded_to_srgb",
    ) -> dict[str, Any]: ...
