"""New paged discovery remains read-only in retained actual-agent workflows."""

import pytest

from tests.codex_docx_grid import audit as grid
from tests.codex_docx_layout import audit as layout
from tests.codex_docx_stories import audit as stories
from tests.codex_etl_csl.audit import native_arguments
from tests.unit.test_codex_docx_grid_audit import OPS, call


@pytest.mark.parametrize(
    "audit,operations",
    [(grid, OPS), (layout, layout.REQUIRED), (stories, stories.REQUIRED)],
)
def test_paged_contract_discovery_keeps_workflow_and_mutation_restrictions(
    audit, operations
):
    events = [
        {"type": "turn.completed"},
        *({"type": "item.completed", "item": call(op)} for op in operations),
    ]
    assert len(audit.calls_from(events)) == len(operations)
    pages = [
        {
            "type": "item.completed",
            "item": call("contract_details", contract_sha256="a" * 64, text_offset=i),
        }
        for i in (0, 4000)
    ]
    assert len(audit.calls_from([*events, *pages])) == len(operations) + 2
    with pytest.raises(ValueError):
        audit.calls_from(
            [*events, *pages, {"type": "item.completed", "item": call("writeback")}]
        )
    with pytest.raises(ValueError):
        audit.calls_from([events[0], *events[2:], *pages])


def test_etl_discovery_accepts_contract_pages_without_authorizing_writeback():
    request = {"op": "contract_details", "contract_sha256": "a" * 64}
    assert native_arguments({"native_request": request}) == request
    with pytest.raises(ValueError):
        native_arguments({"native_request": {"op": "writeback"}})
