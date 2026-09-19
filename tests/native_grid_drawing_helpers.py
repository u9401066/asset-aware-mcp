"""Real DrawingML/VML workbook fixtures, preserving their original ZIP parts."""

import io

import xlsxwriter
from PIL import Image

from src.domain.native_grid import GridTransform, NativeGridEdit, NativeGridUpdate
from src.infrastructure.native_grid_cells import shift_cells, shift_columns
from src.infrastructure.native_grid_drawings import shift_drawing
from src.infrastructure.native_grid_metrics import GridMetrics
from src.infrastructure.native_workbook_plan import WorkbookPlan
from tests.native_workbook_helpers import _replace

DRAWING_PART = "xl/drawings/drawing1.xml"
SHEET_PART = "xl/worksheets/sheet1.xml"


def drawing_workbook():
    image = io.BytesIO()
    Image.new("RGB", (64, 40), color="#228866").save(image, format="PNG")
    output = io.BytesIO()
    with xlsxwriter.Workbook(output, {"in_memory": True}) as book:
        sheet = book.add_worksheet("Data")
        sheet.set_row(1, 30)
        for position in (1, 2, 3):
            sheet.insert_image(
                "B2",
                "fixture.png",
                {
                    "image_data": io.BytesIO(image.getvalue()),
                    "object_position": position,
                    "x_offset": 5,
                    "y_offset": 3,
                },
            )
        sheet.write_column("A1", [1, 2, 3])
        sheet.write_comment("A1", "Retain rich note and author", {"author": "Eric"})
        sheet.write_comment("B2", "Remove only with its cell")
        chart = book.add_chart({"type": "column"})
        chart.add_series({"values": "=Data!$A$1:$A$3"})
        sheet.insert_chart("H1", chart, {"object_position": 1})
    return _replace(output.getvalue(), {"customXml/grid.xml": b"<keep> exact </keep>"})


def drawing_plan(source, **edit):
    plan = WorkbookPlan(source)
    request = NativeGridUpdate.model_validate(
        {
            "worksheet": {"sheet_id": "1", "part": SHEET_PART},
            "edits": [{"axis": "row", "operation": "insert", "at": 3, **edit}],
        }
    )
    transform = GridTransform(NativeGridEdit.model_validate(request.edits[0]))
    metrics = GridMetrics(plan, request)
    root = plan.roots[SHEET_PART]
    before, _ = metrics.axis(root, transform.edit.axis)
    shift_columns(root, transform)
    shift_cells(root, transform)
    after, _ = metrics.axis(root, transform.edit.axis)
    return plan, transform, before, after


def apply_drawing_grid(source, **edit):
    plan, transform, before, after = drawing_plan(source, **edit)
    changes = shift_drawing(plan.roots[DRAWING_PART], transform, before, after)
    data, result = plan.finish({"operation": "drawing_integration", "objects": changes})
    return data, result, before, after
