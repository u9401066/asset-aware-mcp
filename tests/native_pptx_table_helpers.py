"""Typed table fixtures with direct formatting, exact strings and merged headers."""

from src.domain.native_pptx_table import NativePptxTableAddition
from tests.native_pptx_shape_helpers import addition


def table_addition(data, *, region="slide", grouped=False, merge="horizontal"):
    cells = [
        [{"paragraphs": [[{"text": value, "font_size_pt": 14}]]} for value in row]
        for row in [
            ["樣本 & 結果", "Count", "Value"],
            ["A101", "007", "-0.50"],
            ["A102", "12", "=SUM(A1:A2)"],
        ]
    ]
    cells[0][0].update(
        fill_rgb="204060",
        text_rgb="fFeEdD",
        alignment="center",
        vertical_anchor="top",
        margin=10000,
    )
    cells[1][2]["paragraphs"] = [
        [{"text": "-0.50", "italic": True, "bold": True}],
        [{"text": "mg/L", "font_size_pt": 10}],
    ]
    merges = []
    if merge:
        end_row, end_column = {
            "horizontal": (0, 1),
            "vertical": (1, 0),
            "rectangle": (1, 1),
        }[merge]
        merges = [{"row": 0, "column": 0, "end_row": end_row, "end_column": end_column}]
        for row in range(end_row + 1):
            for column in range(end_column + 1):
                if (row, column) != (0, 0):
                    cells[row][column] = {}
    return NativePptxTableAddition(
        container=addition(data, region=region, grouped=grouped).container,
        table={
            "left": 100000,
            "top": 200000,
            "column_widths": [1500000, 1000000, 2500000],
            "row_heights": [450000, 700000, 650000],
            "cells": cells,
            "merges": merges,
            "name": "原生表格",
            "description": "Exact displayed values",
            "first_column": True,
            "column_banding": True,
        },
    )
