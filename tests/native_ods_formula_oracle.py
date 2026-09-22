"""Independent UNO author/edit/export oracle, run with the OS Python and pyuno.

No production ODS code is imported. Only generated fixture documents are edited.
The private office process and profile are owned by this invocation.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import time
import uuid
import zipfile
from contextlib import ExitStack
from pathlib import Path
from xml.dom import minidom
from xml.etree import ElementTree

TABLE_NS = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"


def read_formulas(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        # Only this invocation's independently authored Calc exports are parsed.
        root = ElementTree.fromstring(archive.read("content.xml"))  # noqa: S314
    return [
        cell.attrib[f"{{{TABLE_NS}}}formula"]
        for table in root.iter(f"{{{TABLE_NS}}}table")
        if table.get(f"{{{TABLE_NS}}}name") == "Observer"
        for cell in table.iter(f"{{{TABLE_NS}}}table-cell")
        if f"{{{TABLE_NS}}}formula" in cell.attrib
    ]


def column_name(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def candidate_document(source: Path, destination: Path, formulas: list[str]) -> None:
    """Replace only generated observer formulas, retaining namespace declarations."""
    # ExitStack also runs under the Python 3.8 bundled with the pinned Calc 24.2.
    with ExitStack() as stack:
        original = stack.enter_context(zipfile.ZipFile(source))
        target = stack.enter_context(zipfile.ZipFile(destination, "w"))
        # This XML comes only from this invocation's generated Calc workbook.
        tree = minidom.parseString(original.read("content.xml"))  # noqa: S318
        cells = [
            cell
            for table in tree.getElementsByTagNameNS(TABLE_NS, "table")
            if table.getAttributeNS(TABLE_NS, "name") == "Observer"
            for cell in table.getElementsByTagNameNS(TABLE_NS, "table-cell")
            if cell.hasAttributeNS(TABLE_NS, "formula")
        ]
        assert len(cells) == len(formulas)
        for index, cell in enumerate(cells):
            attribute = cell.getAttributeNodeNS(TABLE_NS, "formula")
            cell.setAttributeNS(TABLE_NS, attribute.name, formulas[index])
        target.comment = original.comment
        for info in original.infolist():
            target.writestr(
                info,
                tree.toxml(encoding="utf-8")
                if info.filename == "content.xml"
                else original.read(info.filename),
            )
    assert read_formulas(destination) == formulas


def collect(binary: str, output: Path, candidates: list | None = None) -> dict:
    import uno  # Provided by the matching OS or bundled LibreOffice Python.

    output.mkdir(parents=True, exist_ok=False)
    # pyuno can set bootstrap variables in the C environment without updating
    # os.environ. Copy the Python mapping explicitly so a private Calc installation
    # does not inherit the system installation's component registry.
    environment = dict(os.environ)
    version = subprocess.check_output(
        [binary, "--version"], text=True, env=environment, timeout=10
    ).strip()
    pipe = "asset_aware_ods_" + uuid.uuid4().hex

    def prop(name, value):
        item = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
        item.Name, item.Value = name, value
        return item

    with (output / "office.log").open("wb") as log:
        process = subprocess.Popen(
            [
                binary,
                "-env:UserInstallation=" + (output / "profile").as_uri(),
                "--headless",
                "--norestore",
                "--nodefault",
                "--nofirststartwizard",
                "--accept=pipe,name=" + pipe + ";urp;StarOffice.ServiceManager",
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
            env=environment,
            start_new_session=True,
        )
        try:
            local = uno.getComponentContext()
            resolver = local.ServiceManager.createInstanceWithContext(
                "com.sun.star.bridge.UnoUrlResolver", local
            )
            deadline = time.monotonic() + 20
            while True:
                try:
                    context = resolver.resolve(
                        "uno:pipe,name=" + pipe + ";urp;StarOffice.ComponentContext"
                    )
                    break
                except Exception:
                    if process.poll() is not None or time.monotonic() >= deadline:
                        raise
                    time.sleep(0.1)
            desktop = context.ServiceManager.createInstanceWithContext(
                "com.sun.star.frame.Desktop", context
            )
            cases = []
            for axis, operation, index, count in (
                ("rows", "insert", 0, 1),
                ("rows", "insert", 2, 2),
                ("rows", "insert", 5, 1),
                ("rows", "delete", 2, 1),
                ("rows", "delete", 0, 5),
                ("rows", "delete", 1, 3),
                ("rows", "delete", -2, 2),
                ("rows", "insert", -1, 1),
                ("columns", "insert", 0, 2),
                ("columns", "insert", 2, 1),
                ("columns", "delete", 0, 1),
                ("columns", "delete", 1, 2),
                ("columns", "delete", -2, 2),
                ("columns", "insert", -1, 1),
                ("sheet", "rename", 0, 0),
                ("sheet", "delete", 0, 0),
            ):
                document = desktop.loadComponentFromURL(
                    "private:factory/scalc",
                    "_blank",
                    0,
                    (prop("Hidden", True), prop("MacroExecutionMode", 0)),
                )
                try:
                    target = document.Sheets.getByIndex(0)
                    target.Name = "Source"
                    document.Sheets.insertNewByName("Observer", 1)
                    observer = document.Sheets.getByName("Observer")
                    row_limit, column_limit = target.Rows.Count, target.Columns.Count
                    if index < 0:
                        index += row_limit if axis == "rows" else column_limit
                    last_column = column_name(column_limit)
                    authored = [
                        "=Source.A1",
                        "=Source.$B$3",
                        "=SUM(Source.A1:A5)",
                        "=SUM(Source.A3:A5)",
                        "=SUM(Source.A1:A3)",
                        "=SUM(Source.A3:A3)",
                        "=SUM(Source.A:A)",
                        "=SUM(Source.1:3)",
                        "=SUM(Source.A5:A1)",
                        '=INDIRECT("Source.A3")',
                        '=Source.A1&"[Source.A3]"',
                        f"=Source.A{row_limit}",
                        f"=Source.{last_column}1",
                        f"=SUM(Source.A{row_limit - 1}:A{row_limit})",
                        f"=SUM(Source.A{row_limit - 2}:A{row_limit - 1})",
                        f"=SUM(Source.A{row_limit}:A{row_limit})",
                        f"=SUM(Source.A3:A{row_limit})",
                        f"=SUM(Source.B1:{last_column}2)",
                        f"=SUM(Source.A1:{last_column}2)",
                    ]
                    for row in range(8):
                        target.getCellByPosition(0, row).Value = row + 1
                    for row, formula in enumerate(authored):
                        observer.getCellByPosition(0, row).Formula = formula
                    name = f"{axis}-{operation}-{index}-{count}"
                    before = output / (name + "-before.ods")
                    after = output / (name + "-after.ods")
                    document.storeAsURL(before.as_uri(), (prop("FilterName", "calc8"),))
                    if axis == "sheet":
                        if operation == "rename":
                            target.Name = "New 中文 O'Brien"
                        else:
                            document.Sheets.removeByName("Source")
                    else:
                        collection = target.Rows if axis == "rows" else target.Columns
                        if operation == "insert":
                            collection.insertByIndex(index, count)
                        else:
                            collection.removeByIndex(index, count)
                    document.calculateAll()
                    document.storeAsURL(after.as_uri(), (prop("FilterName", "calc8"),))
                    record = {
                        "axis": axis,
                        "operation": operation,
                        "index": index,
                        "count": count,
                        "row_limit": row_limit,
                        "column_limit": column_limit,
                        "authored": authored,
                        "before": read_formulas(before),
                        "after": read_formulas(after),
                    }
                    if candidates is not None:
                        proposal = candidates[len(cases)]
                        assert proposal["before"] == record["before"]
                        assert proposal["operation"] == name
                        candidate = output / (name + "-candidate.ods")
                        normalized = output / (name + "-normalized.ods")
                        candidate_document(after, candidate, proposal["formulas"])
                        candidate_model = desktop.loadComponentFromURL(
                            candidate.as_uri(),
                            "_blank",
                            0,
                            (prop("Hidden", True), prop("MacroExecutionMode", 0)),
                        )
                        try:
                            candidate_model.calculateAll()
                            candidate_model.storeAsURL(
                                normalized.as_uri(), (prop("FilterName", "calc8"),)
                            )
                        finally:
                            candidate_model.close(True)
                        record["candidate_input"] = read_formulas(candidate)
                        record["candidate_output"] = read_formulas(normalized)
                        # Both sides must undergo the same import/export cycle.
                        # Calc can serialize an imported [#REF!] as scalar #REF!.
                        control = output / (name + "-control.ods")
                        control.write_bytes(after.read_bytes())
                        assert control.read_bytes() == after.read_bytes()
                        control_model = desktop.loadComponentFromURL(
                            control.as_uri(),
                            "_blank",
                            0,
                            (prop("Hidden", True), prop("MacroExecutionMode", 0)),
                        )
                        try:
                            control_model.calculateAll()
                            control_normalized = output / (
                                name + "-control-normalized.ods"
                            )
                            control_model.storeAsURL(
                                control_normalized.as_uri(),
                                (prop("FilterName", "calc8"),),
                            )
                        finally:
                            control_model.close(True)
                        record["control_input"] = read_formulas(control)
                        record["control_output"] = read_formulas(control_normalized)
                    cases.append(record)
                finally:
                    document.close(True)
            desktop.terminate()
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)
    result = {"renderer": version, "cases": cases}
    (output / "oracle.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--calc-bin", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidates", type=Path)
    args = parser.parse_args()
    result = collect(
        args.calc_bin,
        args.output.resolve(),
        json.loads(args.candidates.read_text(encoding="utf-8"))
        if args.candidates
        else None,
    )
    print(json.dumps({"renderer": result["renderer"], "cases": len(result["cases"])}))
