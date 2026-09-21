"""ODS variant: native fixture, MCP instructions and independent XML/read audit."""

import io
import zipfile

from lxml import etree

from tests.codex_delimited.audit import read_chunk
from tests.codex_native_ods_audit import NS, attr, parts
from tests.codex_native_pdf.trace import canonical, digest, payload
from tests.codex_pdf.trace import require


def formula_cell(root):
    table = root.find("office:body/office:spreadsheet/table:table", NS)
    require(
        table is not None and table.get(attr("table", "name")) == "First",
        "Wrong fixture table",
    )
    cells = [n for n in table.iter() if attr("table", "formula") in n.attrib]
    require(len(cells) == 1, "Unexpected fixture formulas")
    return cells[0]


def prepare_source(xlsx, output):
    from tests.integration.test_native_ods_calc import convert

    imported = convert(xlsx, output / "fixture-import", "ods")
    package = parts(imported.read_bytes())
    root = etree.fromstring(package["content.xml"])
    cell = formula_cell(root)
    # Calc may recalculate unstyled cells to resolve a number format. An explicit
    # authored style makes cached999 vs recomputed3 visible in this fixture.
    cell.set(attr("table", "style-name"), "Default")
    cell.set(attr("office", "value"), "999")
    for paragraph in cell.findall("text:p", NS):
        paragraph.text = "999"
    package["content.xml"] = etree.tostring(
        root, xml_declaration=True, encoding="UTF-8"
    )
    source = xlsx.with_suffix(".ods")
    with (
        zipfile.ZipFile(io.BytesIO(imported.read_bytes())) as original,
        zipfile.ZipFile(source, "w") as archive,
    ):
        for info in original.infolist():
            archive.writestr(info, package[info.filename])
    xlsx.rename(output / "fixture.xlsx")
    return source


def ods_prompt(text):
    start = text.index("1. Discover")
    end = text.index("2. Create")
    text = (
        text[:start]
        + """1. Discover the COMPLETE contract and schemas for every needed operation,
following contract_details/schema continuations at their hashes; no preview_json.
Register the ODS. read_ods with explicit asset_id/revision and text_limit=4000;
assemble all text chunks at one text_sha256, sending ods_text_sha256 on text
continuations. Follow next_offset for physical ranges, resetting text_offset and
hash per listing. Read complete read_ods_cell for First!B2 using ods_locator
{part:content.xml,table_index:0,table_name:First,row:1,column:1}; keep its full ref.
Native indices are zero based. Read full original cache and formula records.
"""
        + text[end:]
    )
    start = text.index("3. Change")
    end = text.index("4. Re-read")
    text = (
        text[:start]
        + """3. Change only managed First!B2 to formula =2+3 with update_ods, current
expected_revision and ods_update.cells containing its full current reference,
value={kind:formula,value:'=2+3'} and explicit
display_policy=replace_paragraphs_preserve_cell_style. Read complete read_ods
operation receipt/review_request and the new read_ods_cell record. Source formula
caches are unverified. Create updated.pdf in whole_sheet/recalculate at the new
revision. Read its COMPLETE receipt, every page record and every actual PNG.
Review the changed formula result, native style and surrounding content.
"""
        + text[end:]
    )
    return (
        text.replace(".xlsx", ".ods")
        .replace("XLSX", "ODS")
        .replace("Excel fidelity", "cross-reader fidelity")
    )


def check_native_xml(original, updated):
    roots = [
        etree.fromstring(parts(data)["content.xml"]) for data in (original, updated)
    ]
    old, new = [formula_cell(root) for root in roots]
    require(
        old.get(attr("table", "formula")) == "of:=1+2"
        # NativeODSUpdate authors the requested unprefixed expression verbatim;
        # the independently imported original retains Calc's namespace prefix.
        and new.get(attr("table", "formula")) == "=2+3",
        "Wrong native formula history",
    )
    require(
        old.get(attr("office", "value")) == "999"
        and new.get(attr("office", "value")) is None,
        "Wrong native cache invalidation",
    )
    require(
        old.get(attr("table", "style-name"))
        == new.get(attr("table", "style-name"))
        == "Default",
        "Lost formula style",
    )
    for cell in (old, new):
        replacement = etree.Element("fixture-target")
        replacement.tail = cell.tail
        cell.getparent().replace(cell, replacement)
    require(
        etree.tostring(roots[0], method="c14n")
        == etree.tostring(roots[1], method="c14n"),
        "Unrelated native content changed",
    )
    return dict(old.attrib), dict(new.attrib)


def check_sources(original, updated, calls, source):
    old, new = check_native_xml(original, updated)
    buffers, reads, receipts = {}, set(), set()
    for call in calls:
        args, result = call["arguments"]["native_request"], payload(call)
        if args["op"] not in {"read_ods", "read_ods_cell"}:
            continue
        if args.get("text_offset", 0):
            require(
                args.get("ods_text_sha256") == result["text_sha256"],
                "Unpinned ODS continuation",
            )
        record = read_chunk(result, args, buffers)
        if record is None:
            continue
        revision = args["revision"]
        require(args["asset_id"] == source["asset_id"], "Wrong ODS source read")
        if args["op"] == "read_ods":
            history = next(h for h in source["history"] if h["sha256"] == revision)
            require(
                record["operation_result"] == history.get("result"),
                "Incomplete ODS receipt",
            )
            receipts.add(revision)
        else:
            cell = record["cell"]
            reference = cell["evidence"]
            require(
                reference["asset_id"] == source["asset_id"]
                and reference["revision"] == revision
                and reference["locator"] == args["ods_locator"],
                "Rebound ODS cell reference",
            )
            require(
                reference["value_sha256"]
                == digest(
                    canonical({k: v for k, v in cell.items() if k != "evidence"})
                ),
                "Wrong ODS cell hash",
            )
            loc = reference["locator"]
            if (loc["table_index"], loc["table_name"], loc["row"], loc["column"]) == (
                0,
                "First",
                1,
                1,
            ):
                require(
                    cell["attributes"]
                    == (old if revision == digest(original) else new),
                    "Cell read differs from independent XML",
                )
                reads.add(revision)
    require(
        not buffers and {digest(original), source["revision"]} <= reads & receipts,
        "Incomplete ODS native reads/receipts",
    )
