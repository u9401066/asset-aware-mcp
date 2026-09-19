"""Migrate structured table references by stable column identity, not new names."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.infrastructure.native_grid_formulas import _ranges
from src.infrastructure.native_grid_selectors import one_column, rewrite_selector
from src.infrastructure.native_workbook_formulas import (
    _qualifier_spans,
    _range_operands,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from src.domain.native_grid_tables import GridTableChange


@dataclass
class _Operand:
    original: str
    change: GridTableChange | None
    spec: str | None
    spec_start: int
    external: bool

    def updated(self, forced_column: str | None = None) -> str:
        if self.change is None:
            return self.original
        if self.change.after is None:
            return "#REF!"
        if self.spec is None:
            return self.original
        spec = rewrite_selector(self.spec, self.change, forced_column=forced_column)
        if spec is None:
            return "#REF!"
        return (
            self.original[: self.spec_start]
            + spec
            + self.original[self.spec_start + len(self.spec) :]
        )


def _parse(
    text: str, changes: dict[str, GridTableChange], context: str | None, external: bool
) -> _Operand:
    start = int(text.startswith("@"))
    spans = _qualifier_spans(text[start:])
    if len(spans) > 1:
        raise ValueError("Ambiguous structured reference worksheet context")
    if spans:
        left, right = spans[0]
        prefix = text[start + left : start + right]
        external = "[" in prefix or "]" in prefix
        start += right + 1
    if external:
        return _Operand(text, None, None, 0, True)
    end = len(text) - int(text.endswith("#"))
    body = text[start:end]
    bracket = body.find("[")
    name = body[:bracket] if bracket >= 0 else body
    if not name and bracket == 0:
        if context is None and changes:
            raise ValueError(
                "Implicit structured reference needs an exact table context"
            )
        name = context or ""
    change = changes.get(name.casefold())
    spec = body[bracket:] if bracket >= 0 and change else None
    return _Operand(text, change, spec, start + max(0, bracket), False)


def rewrite_structured_formula(
    text: str, changes: Sequence[GridTableChange], *, table_context: str | None = None
) -> tuple[str, int]:
    lookup = {change.name.casefold(): change for change in changes}
    if len(lookup) != len(changes):
        raise ValueError("Duplicate table changes are ambiguous")
    replacements = []
    for start, end, value in _ranges(text):
        parts, positions = [], []
        cursor, external = 0, False
        for operand in _range_operands(value):
            position = value.index(operand, cursor)
            cursor = position + len(operand)
            parsed = _parse(operand, lookup, table_context, external)
            external = parsed.external
            parts.append(parsed)
            positions.append((position, cursor))
        if not any(part.change is not None for part in parts):
            continue
        forced: list[str | None] = [None] * len(parts)
        if (
            len(parts) == 2
            and parts[0].change is not None
            and parts[0].change is parts[1].change
        ):
            first = one_column(parts[0].spec) if parts[0].spec is not None else None
            last = one_column(parts[1].spec) if parts[1].spec is not None else None
            if first is not None and last is not None:
                interval = parts[0].change.interval(first, last)
                if interval is None:
                    replacements.append((start, end, "#REF!"))
                    continue
                forced = list(interval)
        elif len(parts) > 2:
            raise ValueError("Chained structured references require a range resolver")
        updated = [
            part.updated(column) for part, column in zip(parts, forced, strict=True)
        ]
        if "#REF!" in updated:
            result = "#REF!"
        else:
            result = value
            for (left, right), replacement in reversed(
                list(zip(positions, updated, strict=True))
            ):
                result = result[:left] + replacement + result[right:]
        if result != value:
            replacements.append((start, end, result))
    for start, end, value in reversed(replacements):
        text = text[:start] + value + text[end:]
    return text, len(replacements)
