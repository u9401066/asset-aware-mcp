"""Independent Calc fixture/reimport; OS or matching bundled Python with pyuno.

Only generated documents are authored. No production dependency mapper is used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import time
import uuid
from pathlib import Path


def generate(desktop, uno, prop, output):
    doc = desktop.loadComponentFromURL(
        "private:factory/scalc",
        "_blank",
        0,
        (prop("Hidden", True), prop("MacroExecutionMode", 0)),
    )
    try:
        source = doc.Sheets.getByIndex(0)
        source.Name = "Source"
        doc.Sheets.insertNewByName("Observer", 1)
        observer = doc.Sheets.getByName("Observer")
        source.getCellRangeByName("A1:B4").setDataArray(
            (("Label", "Value"), ("A", 1), ("B", 2), ("C", 3))
        )
        base = observer.getCellRangeByName("C3").CellAddress
        for name, content in (
            ("DataRange", "$Source.$A$2:$B$4"),
            ("RelativeRange", "Source.A2:B4"),
            ("TotalExpr", "SUM($Source.$B$2:$B$4)"),
            ("SinglePoint", "$Source.$A$2"),
        ):
            doc.NamedRanges.addNewByName(name, content, base, 0)
        if source.getPropertySetInfo().hasPropertyByName("NamedRanges"):
            source.NamedRanges.addNewByName(
                "LocalRange",
                "$Source.$A$2:$B$4",
                source.getCellRangeByName("A1").CellAddress,
                0,
            )
        for row, formula in enumerate(
            (
                "=SUM(DataRange)",
                "=SUM(Source.B2:B4)",
                "=Source.A2",
                '=INDIRECT("Source.B2")',
            )
        ):
            observer.getCellByPosition(0, row).Formula = formula
        valcell = observer.getCellRangeByName("D1")
        validation = valcell.Validation
        validation.Type = uno.Enum("com.sun.star.sheet.ValidationType", "LIST")
        validation.Formula1 = "Source.$A$2:$A$4"
        validation.SourcePosition = valcell.CellAddress
        valcell.Validation = validation
        cellrange = observer.getCellRangeByName("A1:A4")
        condition = cellrange.ConditionalFormat
        condition.addNew(
            (
                prop(
                    "Operator",
                    uno.Enum("com.sun.star.sheet.ConditionOperator", "FORMULA"),
                ),
                prop("Formula1", "Source.B2>0"),
                prop("SourcePosition", observer.getCellRangeByName("A1").CellAddress),
                prop("StyleName", "Default"),
            )
        )
        cellrange.ConditionalFormat = condition
        source.setPrintAreas((source.getCellRangeByName("A1:B4").RangeAddress,))
        rectangle = uno.createUnoStruct("com.sun.star.awt.Rectangle")
        rectangle.X, rectangle.Y = 1000, 5000
        rectangle.Width, rectangle.Height = 10000, 6000
        observer.Charts.addNewByName(
            "ChartEvidence",
            rectangle,
            (source.getCellRangeByName("A1:B4").RangeAddress,),
            True,
            True,
        )
        doc.CurrentController.setActiveSheet(source)
        doc.storeAsURL((output / "source.ods").as_uri(), (prop("FilterName", "calc8"),))
        source.Name = "New 中文 O'Brien"
        doc.calculateAll()
        doc.storeAsURL(
            (output / "control.ods").as_uri(), (prop("FilterName", "calc8"),)
        )
        observer.getCellByPosition(
            0, 3
        ).Formula = "=INDIRECT(\"'New 中文 O''Brien'.B2\")"
        doc.calculateAll()
        assert observer.getCellByPosition(0, 3).Value == 1
        assert observer.getCellByPosition(0, 3).Error == 0
        doc.storeAsURL(
            (output / "corrected-control.ods").as_uri(), (prop("FilterName", "calc8"),)
        )
    finally:
        doc.close(True)


def collect(binary, output, candidate=None, control=None):
    import uno

    output.mkdir(parents=True, exist_ok=False)
    environment = dict(os.environ)
    renderer = subprocess.check_output(
        [binary, "--version"],
        text=True,
        env=environment,
        timeout=10,
    ).strip()
    inputs = {
        label: {
            "path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "mtime_ns": path.stat().st_mtime_ns,
        }
        for label, path in (("candidate", candidate), ("control", control))
        if path is not None
    }

    def prop(name, value):
        item = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
        item.Name, item.Value = name, value
        return item

    pipe = "asset_aware_ods_rename_" + uuid.uuid4().hex
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
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            local = uno.getComponentContext()
            resolver = local.ServiceManager.createInstanceWithContext(
                "com.sun.star.bridge.UnoUrlResolver",
                local,
            )
            deadline = time.monotonic() + 20
            while True:
                try:
                    context = resolver.resolve(
                        "uno:pipe,name=" + pipe + ";urp;StarOffice.ComponentContext"
                    )
                    break
                except Exception:
                    if process.poll() is not None or time.monotonic() > deadline:
                        raise
                    time.sleep(0.1)
            desktop = context.ServiceManager.createInstanceWithContext(
                "com.sun.star.frame.Desktop",
                context,
            )
            if candidate is None:
                generate(desktop, uno, prop, output)
            else:
                for label, path in (("candidate", candidate), ("control", control)):
                    doc = desktop.loadComponentFromURL(
                        path.as_uri(),
                        "_blank",
                        0,
                        (
                            prop("Hidden", True),
                            prop("MacroExecutionMode", 0),
                            prop("UpdateDocMode", 0),
                        ),
                    )
                    try:
                        doc.calculateAll()
                        doc.storeAsURL(
                            (output / (label + ".ods")).as_uri(),
                            (prop("FilterName", "calc8"),),
                        )
                        options = (
                            prop("SinglePageSheets", False),
                            prop("UseTaggedPDF", True),
                        )
                        doc.storeToURL(
                            (output / (label + ".pdf")).as_uri(),
                            (
                                prop("FilterName", "calc_pdf_Export"),
                                prop(
                                    "FilterData",
                                    uno.Any(
                                        "[]com.sun.star.beans.PropertyValue", options
                                    ),
                                ),
                            ),
                        )
                    finally:
                        doc.close(True)
            desktop.terminate()
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)
    for item in inputs.values():
        path = Path(item["path"])
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        assert path.stat().st_mtime_ns == item["mtime_ns"]
    result = {
        "renderer": renderer,
        "inputs": inputs,
        "files": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in output.iterdir()
            if p.is_file()
        },
    }
    (output / "oracle.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calc-bin", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--control", type=Path)
    args = parser.parse_args()
    if (args.candidate is None) != (args.control is None):
        parser.error("Candidate and independent control must be supplied together")
    print(
        json.dumps(
            collect(args.calc_bin, args.output.resolve(), args.candidate, args.control)
        )
    )
