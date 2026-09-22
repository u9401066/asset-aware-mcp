"""Typed values preserve native button states and choice option indices."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pikepdf

from src.domain.native_pdf_fields import (
    PdfFieldButtonValue,
    PdfFieldChoiceValue,
    PdfFieldTextValue,
)

if TYPE_CHECKING:
    from src.domain.native_pdf_fields import PdfFieldValue
    from src.infrastructure.native_pdf_field_journal import FieldJournal
    from src.infrastructure.native_pdf_field_tree import FieldNode


def field_flags(node: FieldNode) -> int:
    flags, _ = node.inherited("/Ff")
    if flags is None:
        return 0
    if not isinstance(flags, int) or isinstance(flags, bool) or flags < 0:
        raise ValueError("PDF field has invalid native flags")
    return flags


def choice_options(node: FieldNode) -> list[tuple[str, str]]:
    value, _ = node.inherited("/Opt")
    if not isinstance(value, pikepdf.Array) or len(value) > 10_000:
        raise ValueError("PDF choice field needs bounded native options")
    options = []
    for option in value:
        if isinstance(option, pikepdf.String):
            options.append((str(option), str(option)))
        elif (
            isinstance(option, pikepdf.Array)
            and len(option) == 2
            and all(isinstance(v, pikepdf.String) for v in option)
        ):
            options.append((str(option[0]), str(option[1])))
        else:
            raise ValueError(
                "PDF choice field has an unsupported option representation"
            )
    return options


def write_value(
    node: FieldNode, value: PdfFieldValue, journal: FieldJournal
) -> dict[str, Any]:
    kind, _ = node.inherited("/FT")
    flags = field_flags(node)
    if flags & 1:
        raise ValueError("Read-only PDF field cannot be changed")
    if isinstance(value, PdfFieldTextValue):
        if kind != pikepdf.Name.Tx:
            raise ValueError("Text value requires a native text field")
        if flags & (8192 | 1048576 | 33554432) or "/RV" in node.obj:
            raise ValueError(
                "Password, file-select and rich-text fields need their own value/appearance workflow"
            )
        if not flags & 4096 and any(c in value.text for c in "\r\n"):
            raise ValueError("Single-line PDF field cannot receive line breaks")
        maximum, _ = node.inherited("/MaxLen")
        if maximum is not None and (
            not isinstance(maximum, int)
            or isinstance(maximum, bool)
            or maximum < 1
            or len(value.text) > maximum
        ):
            raise ValueError("PDF field value exceeds or has invalid MaxLen")
        journal.set_key(node.obj, "/V", pikepdf.String(value.text))
        return {
            "text": value.text,
            "comb": maximum if flags & 16777216 else None,
            "multiline": bool(flags & 4096),
        }
    if isinstance(value, PdfFieldChoiceValue):
        if kind != pikepdf.Name.Ch:
            raise ValueError("Choice indices require a native choice field")
        options = choice_options(node)
        if (len(value.indices) > 1 and not flags & 2097152) or any(
            i >= len(options) for i in value.indices
        ):
            raise ValueError(
                "PDF choice selection exceeds the native options or selection mode"
            )
        selected = [options[i][0] for i in value.indices]
        if not selected and any("/V" in n.obj for n in node.ancestors):
            raise ValueError(
                "Clearing an inherited choice value requires an explicit inheritance rewrite"
            )
        native = (
            pikepdf.Array(selected)
            if flags & 2097152
            else pikepdf.String(selected[0])
            if selected
            else None
        )
        journal.set_key(node.obj, "/V", native)
        journal.set_key(node.obj, "/I", pikepdf.Array(value.indices))
        top, _ = node.inherited("/TI")
        top = 0 if top is None else top
        if (
            not isinstance(top, int)
            or isinstance(top, bool)
            or not 0 <= top < max(1, len(options))
        ):
            raise ValueError("PDF choice field has invalid top index")
        return {
            "text": options[value.indices[0]][1] if value.indices else "",
            "choices": None
            if flags & 131072
            else [
                (label, i in value.indices)
                for i, (_, label) in enumerate(options)
                if i >= top
            ],
            "offscreen_selection_requires_review": any(i < top for i in value.indices),
        }
    assert isinstance(value, PdfFieldButtonValue)
    if kind != pikepdf.Name.Btn or flags & 65536:
        raise ValueError("Button state requires a native checkbox or radio field")
    if value.state == "/Off" and flags & 16384:
        raise ValueError("PDF radio field prohibits turning off its selection")
    matched = 0
    for widget in node.widgets:
        appearances = widget.obj.get("/AP")
        if not isinstance(appearances, pikepdf.Dictionary):
            raise ValueError("PDF button requires native appearance states")
        for key in ("/N", "/D", "/R"):
            states = appearances.get(key)
            if states is None and key != "/N":
                continue
            if (
                not isinstance(states, pikepdf.Dictionary)
                or not isinstance(states.get("/Off"), pikepdf.Stream)
                or any(not isinstance(s, pikepdf.Stream) for _, s in states.items())
            ):
                raise ValueError("PDF button appearance states are incomplete")
            if key != "/N" and set(states.keys()) != set(appearances.N.keys()):
                raise ValueError("PDF button normal/rollover/down state names disagree")
        state = value.state if value.state in appearances.N else "/Off"
        matched += int(state != "/Off")
        journal.set_key(widget.obj, "/AS", pikepdf.Name(state))
    if node.widgets and value.state != "/Off" and not matched:
        raise ValueError("Requested PDF button state is absent from every widget")
    if flags & 32768 and matched > 1 and not flags & 33554432:
        raise ValueError(
            "Radio widgets share an on state without RadiosInUnison; selection needs an explicit widget workflow"
        )
    journal.set_key(node.obj, "/V", pikepdf.Name(value.state))
    return {"state": value.state}
