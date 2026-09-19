"""Rich typed Word content and native-body inspection fixtures."""

from __future__ import annotations

from src.domain.native_docx_structure import NativeDocxCreate


def paragraph(text, **options):
    return {"kind": "paragraph", "runs": [{"text": text, **options}]}


def creation():
    return NativeDocxCreate.model_validate(
        {
            "name": "native.docx",
            "author": "u9401066",
            "blocks": [
                {
                    **paragraph(
                        "研究 007\tµg\n測試",
                        bold=True,
                        italic=False,
                        underline=True,
                        font_size_pt=11.5,
                        font_name="Arial",
                        color_rgb="1122aa",
                    ),
                    "outline_level": 0,
                    "alignment": "center",
                    "space_before_twips": 120,
                    "space_after_twips": 80,
                    "keep_with_next": True,
                },
                {
                    "kind": "table",
                    "column_widths_twips": [1200, 1800, 2400],
                    "row_heights_twips": [300, 400, 400],
                    "repeat_header": True,
                    "cells": [
                        [
                            {
                                "paragraphs": [paragraph("Header", bold=True)],
                                "fill_rgb": "ddeeff",
                            },
                            {},
                            {},
                        ],
                        [
                            {"paragraphs": [paragraph("007", font_size_pt=12)]},
                            {
                                "paragraphs": [
                                    paragraph("-0.50", italic=True),
                                    paragraph("Second"),
                                ],
                                "vertical_alignment": "center",
                            },
                            {"paragraphs": [paragraph("mg/L")]},
                        ],
                        [
                            {},
                            {"paragraphs": [paragraph("1,234.50")]},
                            {"paragraphs": [paragraph("HIGH")]},
                        ],
                    ],
                    "merges": [
                        {"row": 0, "column": 0, "end_row": 0, "end_column": 2},
                        {"row": 1, "column": 0, "end_row": 2, "end_column": 0},
                    ],
                },
                paragraph("Last paragraph", font_size_pt=12),
            ],
        }
    )
