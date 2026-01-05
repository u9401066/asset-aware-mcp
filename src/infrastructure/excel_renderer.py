"""
Infrastructure Layer - Excel Renderer

Handles Excel file generation using XlsxWriter with professional styling.
"""

from datetime import datetime
from pathlib import Path

import xlsxwriter

from src.domain.table_entities import TableContext


class ExcelRenderer:
    """Renderer for professional Excel tables."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render(self, context: TableContext, filename: str) -> Path:
        """
        Render a TableContext to an Excel file.

        Args:
            context: The table context to render
            filename: Base filename (without extension)

        Returns:
            Path to the generated file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = self.output_dir / f"{filename}_{timestamp}.xlsx"

        workbook = xlsxwriter.Workbook(str(file_path))
        worksheet = workbook.add_worksheet("Data")

        # Define Formats
        header_format = workbook.add_format(
            {
                "bold": True,
                "font_color": "white",
                "bg_color": "#2C3E50",
                "border": 1,
                "align": "center",
                "valign": "vcenter",
            }
        )

        cell_format = workbook.add_format(
            {"border": 1, "valign": "top", "text_wrap": True}
        )

        # Write Title
        title_format = workbook.add_format({"bold": True, "font_size": 14})
        worksheet.write(0, 0, context.title, title_format)

        # Write Source Description if exists
        if context.source_description:
            worksheet.write(1, 0, f"Source: {context.source_description}")
            start_row = 3
        else:
            start_row = 2

        # Write Headers
        for col_idx, col in enumerate(context.columns):
            worksheet.write(start_row, col_idx, col.name, header_format)
            # Set initial column width
            worksheet.set_column(col_idx, col_idx, 15)

        # Write Data
        for row_idx, row_data in enumerate(context.rows):
            current_row = start_row + 1 + row_idx
            for col_idx, col in enumerate(context.columns):
                val = row_data.get(col.name, "")

                # Apply specific formatting based on intent and value
                fmt = cell_format

                # Comparison specific: highlight confidence
                if context.intent == "comparison" and col.name.lower() == "confidence":
                    if str(val).lower() == "high":
                        fmt = workbook.add_format(
                            {
                                "bg_color": "#C6EFCE",
                                "font_color": "#006100",
                                "border": 1,
                            }
                        )
                    elif str(val).lower() == "low":
                        fmt = workbook.add_format(
                            {
                                "bg_color": "#FFC7CE",
                                "font_color": "#9C0006",
                                "border": 1,
                            }
                        )

                # Write value
                if col.type == "number" and isinstance(val, int | float):
                    worksheet.write_number(current_row, col_idx, val, fmt)
                elif col.type == "url" and val:
                    worksheet.write_url(
                        current_row, col_idx, str(val), string=str(val), cell_format=fmt
                    )
                else:
                    worksheet.write(
                        current_row, col_idx, str(val) if val is not None else "", fmt
                    )

        # Add Data Bars for numeric columns in comparison mode
        if context.intent == "comparison":
            for col_idx, col in enumerate(context.columns):
                if col.type == "number":
                    worksheet.conditional_format(
                        start_row + 1,
                        col_idx,
                        start_row + len(context.rows),
                        col_idx,
                        {"type": "data_bar", "bar_color": "#3498DB"},
                    )

        # Auto-adjust column widths (basic implementation)
        for col_idx, col in enumerate(context.columns):
            max_len = len(col.name)
            for row in context.rows:
                val = row.get(col.name, "")
                max_len = max(max_len, len(str(val)))

            # Cap width at 50
            width = min(max_len + 2, 50)
            worksheet.set_column(col_idx, col_idx, width)

        workbook.close()
        return file_path
