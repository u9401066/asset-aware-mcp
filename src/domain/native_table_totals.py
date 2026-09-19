"""Explicit totals-role transitions without implicit worksheet axis movement."""

from typing import Annotated, Literal

from pydantic import Field

from src.domain.native_asset_models import NativeModel


class NativeTotalsRowAdd(NativeModel):
    action: Literal["add"]
    reuse_definitions: bool = True
    cell_styles: Literal["preserve", "last_data_row"] = "preserve"


class NativeTotalsRowRemove(NativeModel):
    action: Literal["remove"]
    cells: Literal["clear", "keep_cells"]
    retain_definitions: bool = True


NativeTotalsRowChange = Annotated[
    NativeTotalsRowAdd | NativeTotalsRowRemove, Field(discriminator="action")
]
