"""The independent evaluator rejects location/context forgery after rehashing."""

from copy import deepcopy

import pytest

from tests.codex_native_pdf.trace import canonical, digest
from tests.codex_native_selection.records import verify_selected_record
from tests.native_derivation_helpers import service_at
from tests.native_workbook_helpers import _call
from tests.unit.test_native_selection_service import read


@pytest.mark.parametrize(
    "tamper", ["value", "context", "locator", "selector", "binding"]
)
def test_independent_selection_audit_rejects_rehashed_forgery(tmp_path, tamper):
    service = service_at(tmp_path)
    asset = _call(
        service,
        op="create",
        workbook={"edits": [{"sheet": "Sheet1", "cell": "B2", "value": "007"}]},
    )["asset"]
    ref = _call(
        service, op="read_cell", asset_id=asset["asset_id"], sheet="Sheet1", cell="B2"
    )["cell"]["evidence"]
    complete = read(service, ref)
    records = {canonical(complete["evidence"]): complete}
    verify_selected_record(complete, {})
    selection = read(
        service, ref, {"pointer": "/value", "char_range": {"start": 0, "end": 3}}
    )
    verify_selected_record(selection, records)
    bad = deepcopy(selection)
    if tamper == "value":
        bad["value"] = "008"
    elif tamper == "context":
        bad["text_context"]["utf8_byte_range"] = [1, 4]
    elif tamper == "locator":
        bad["parent"]["locator"]["cell"] = "B3"
        bad["evidence"]["parent"] = bad["parent"]
    elif tamper == "selector":
        bad["selector"]["pointer"] = "/other"
        bad["evidence"]["selector"] = bad["selector"]
    else:
        bad["evidence"]["revision"] = "f" * 64
    bad["evidence"]["value_sha256"] = digest(
        canonical({k: v for k, v in bad.items() if k != "evidence"})
    )
    with pytest.raises(ValueError):
        verify_selected_record(bad, records)
