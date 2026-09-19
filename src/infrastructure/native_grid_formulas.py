"""Lossless structural A1 rewriting and explicit shared-formula expansion."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from openpyxl.formula.tokenizer import Token

from src.domain.native_grid_address import transform_reference, translate_reference
from src.infrastructure.native_workbook_formulas import (
    _qualifier_spans,
    _unquote,
    formula_tokens,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from src.domain.native_grid import GridTransform


def _ranges(text: str) -> Iterator[tuple[int, int, str]]:
    tokens = list(formula_tokens(text))
    index = 0
    while index < len(tokens):
        start, end, value, kind, subtype = tokens[index]
        index += 1
        if (kind, subtype) != (Token.OPERAND, Token.RANGE):
            continue
        # Excel permits whitespace around the range operator. Preserve it while
        # treating both endpoints as one interval, including deleted endpoints.
        look = index
        while look < len(tokens) and tokens[look][3] == Token.WSPACE:
            look += 1
        if look < len(tokens) and tokens[look][2] == ":":
            look += 1
            while look < len(tokens) and tokens[look][3] == Token.WSPACE:
                look += 1
            if look < len(tokens) and tokens[look][3:] == (Token.OPERAND, Token.RANGE):
                end = tokens[look][1]
                value, index = text[start:end], look + 1
        elif (
            look < len(tokens)
            and tokens[look][3:] == (Token.OPERAND, Token.RANGE)
            and (value.endswith(":") or tokens[look][2].startswith(":"))
        ):
            # The lexer also emits `A1:` + ` A3` and `A1 ` + `:A3`.
            end = tokens[look][1]
            value, index = text[start:end], look + 1
        yield start, end, value


def _operand(value: str, mapper: Callable[[str, list[str]], str | None]) -> str:
    implicit, spill = value.startswith("@"), value.endswith("#")
    body = value[int(implicit) : len(value) - int(spill)]
    spans = _qualifier_spans(body)
    if len(spans) > 2:
        raise ValueError("Ambiguous qualified coordinate range")
    prefixes = [body[start:end] for start, end in spans]
    if len(spans) == 2:
        # The separator may contain spaces before the second qualifier.
        left = body[spans[0][1] + 1 : spans[1][0]]
        right = body[spans[1][1] + 1 :]
        leading = prefixes[1][: len(prefixes[1]) - len(prefixes[1].lstrip())]
        reference = left + leading + right
        prefixes[1] = prefixes[1].lstrip()
    else:
        reference = body[spans[0][1] + 1 :] if spans else body
    updated = mapper(reference, prefixes)
    if updated is None or updated == reference:
        return value
    if updated == "#REF!":
        return updated
    if len(spans) == 2:
        left, separator, right = re.split(r"(\s*:\s*)", updated)
        output = prefixes[0] + "!" + left + separator + prefixes[1] + "!" + right
    else:
        output = (prefixes[0] + "!" if prefixes else "") + updated
    return ("@" if implicit else "") + output + ("#" if spill else "")


def _rewrite(
    text: str, mapper: Callable[[str, list[str]], str | None]
) -> tuple[str, int]:
    replacements = []
    for start, end, value in _ranges(text):
        updated = _operand(value, mapper)
        if updated != value:
            replacements.append((start, end, updated))
    for start, end, value in reversed(replacements):
        text = text[:start] + value + text[end:]
    return text, len(replacements)


def _names(prefix: str) -> tuple[str, ...] | None:
    prefix = prefix.strip()
    if "[" in prefix or "]" in prefix or prefix == "#REF":
        return None  # External workbook, never the local grid's coordinate space.
    if prefix.startswith("'") and prefix.endswith("'"):
        # One quoted qualifier can contain the complete 3D sheet span.
        try:
            return tuple(_unquote(prefix).split(":"))
        except ValueError:
            pass  # Individually quoted 3D endpoints are handled below.
    return tuple(_unquote(name) for name in prefix.split(":"))


def _targets(prefix: str, target: str, sheets: list[str], changed: bool) -> bool:
    names = _names(prefix)
    if names is None:
        return False
    if len(names) == 1:
        return names[0].casefold() == target.casefold()
    if len(names) != 2:
        raise ValueError("Unsupported worksheet qualifier")
    indices = {name.casefold(): index for index, name in enumerate(sheets)}
    if any(name.casefold() not in indices for name in names):
        raise ValueError("3D reference has an unknown sheet boundary")
    first, last = sorted(indices[name.casefold()] for name in names)
    selected = first <= indices[target.casefold()] <= last
    if selected and first != last and changed:
        raise ValueError(
            "Grid edit would require different coordinates inside a 3D reference"
        )
    return selected


def rewrite_grid_formula(
    text: str,
    transform: GridTransform,
    *,
    owner: str | None,
    target: str,
    sheets: list[str],
) -> tuple[str, int]:
    def mapper(reference: str, prefixes: list[str]) -> str | None:
        if not prefixes and owner is not None and owner.casefold() != target.casefold():
            return None
        if prefixes and not any(
            _targets(prefix, target, sheets, False) for prefix in prefixes
        ):
            return None
        shifted = transform_reference(reference, transform)
        if shifted is None or shifted == reference:
            return None
        if not prefixes:
            if owner is None:
                raise ValueError(
                    "Unqualified workbook coordinate has no unambiguous worksheet context"
                )
            return shifted if owner.casefold() == target.casefold() else None
        selected = [_targets(prefix, target, sheets, True) for prefix in prefixes]
        if len(selected) == 2 and selected[0] != selected[1]:
            raise ValueError(
                "Qualified range endpoints span different coordinate spaces"
            )
        return shifted if all(selected) else None

    return _rewrite(text, mapper)


def translate_shared_formula(text: str, rows: int, columns: int) -> str:
    return _rewrite(
        text, lambda reference, _prefixes: translate_reference(reference, rows, columns)
    )[0]
