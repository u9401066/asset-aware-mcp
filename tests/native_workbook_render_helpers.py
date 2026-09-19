"""Workbook fixture distinguishing cached results, print areas and hidden sheets."""

import io

import xlsxwriter


def rendered_workbook() -> bytes:
    output = io.BytesIO()
    with xlsxwriter.Workbook(output, {"in_memory": True}) as book:
        first = book.add_worksheet("First")
        book.add_worksheet("Blank")
        hidden = book.add_worksheet("Hidden")
        last = book.add_worksheet("Last")
        red = book.add_format({"font_color": "#FF0000", "font_size": 24})
        blue = book.add_format({"font_color": "#0000FF", "font_size": 24})
        first.write("A1", "FIRST PRINT", red)
        first.write("A50", "OUTSIDE PRINT RANGE")
        first.write_formula("B2", "=1+2", None, 999)
        first.print_area("A1:C4")
        first.set_column("A:C", 20)
        hidden.write("A1", "HIDDEN CONTENT")
        hidden.hide()
        last.write("A1", "LAST PRINT", blue)
        last.print_area("A1:C4")
        last.set_column("A:C", 20)
    return output.getvalue()
