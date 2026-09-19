"""Source-bound visual PDF regions, independent of OCR and preview resolution."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Annotated, Any, Literal

from pydantic import Field, model_validator

from src.domain.native_asset_models import ASSET_ID_PATTERN, SHA256_PATTERN, NativeModel
from src.domain.native_pdf import NativePdfReference  # noqa: TC001 -- Pydantic model

Fraction = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class NativePdfRegionSelector(NativeModel):
    coordinate_system: Literal["displayed_crop_fraction"] = "displayed_crop_fraction"
    rect: list[Fraction] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def nonempty(self) -> NativePdfRegionSelector:
        x0, y0, x1, y1 = self.rect
        if x0 >= x1 or y0 >= y1:
            raise ValueError("PDF region must be a nonempty ordered rectangle")
        return self


class NativePdfRegionReference(NativeModel):
    schema_version: Literal["native-pdf-region-ref-v1"] = "native-pdf-region-ref-v1"
    asset_id: str = Field(pattern=ASSET_ID_PATTERN)
    revision: str = Field(pattern=SHA256_PATTERN)
    parent: NativePdfReference
    selector: NativePdfRegionSelector
    value_sha256: str = Field(pattern=SHA256_PATTERN)
    verification_scope: Literal["immutable_pdf_page_region"] = (
        "immutable_pdf_page_region"
    )

    @model_validator(mode="after")
    def identity(self) -> NativePdfRegionReference:
        if (self.asset_id, self.revision) != (
            self.parent.asset_id,
            self.parent.revision,
        ):
            raise ValueError("PDF region identity must match its full page reference")
        return self


def region_record(
    parent: NativePdfReference, selector: NativePdfRegionSelector, page: dict[str, Any]
) -> dict[str, Any]:
    geometry = {
        key: page[key] for key in ("media_box", "crop_box", "rotation", "user_unit")
    }
    for name in ("media_box", "crop_box"):
        box = geometry[name]
        if (
            len(box) != 4
            or not all(math.isfinite(v) for v in box)
            or box[0] >= box[2]
            or box[1] >= box[3]
        ):
            raise ValueError("PDF region requires finite ordered page geometry")
    if (
        geometry["rotation"] not in {0, 90, 180, 270}
        or not math.isfinite(geometry["user_unit"])
        or geometry["user_unit"] <= 0
    ):
        raise ValueError(
            "PDF region requires a valid UserUnit and quarter-turn rotation"
        )
    record = {
        "schema_version": "native-pdf-region-v1",
        "parent": parent.model_dump(mode="json"),
        "selector": selector.model_dump(mode="json"),
        "source_geometry": geometry,
        "coordinate_definition": "Fractions of the displayed CropBox after page rotation; top-left origin, right/down positive. Not native PDF user units or unrotated text-block coordinates.",
        "verification_scope": "Source page identity and selected geometry; no OCR, semantic support or renderer-independent pixel identity.",
    }
    data = json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    record["evidence"] = NativePdfRegionReference(
        asset_id=parent.asset_id,
        revision=parent.revision,
        parent=parent,
        selector=selector,
        value_sha256=hashlib.sha256(data).hexdigest(),
    ).model_dump(mode="json")
    return record
