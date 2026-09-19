"""Parse structured column selectors while retaining exact header token spans."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.native_grid_tables import GridTableChange

ESCAPES = "[]#'@"
ITEMS = {"#all", "#data", "#headers", "#totals", "#this row"}


@dataclass(frozen=True)
class ColumnSelector:
    start: int
    end: int
    name: str | None


def _decode(text: str) -> str:
    result = []
    index = 0
    while index < len(text):
        if text[index] == "'" and index + 1 < len(text) and text[index + 1] in ESCAPES:
            index += 1
        result.append(text[index])
        index += 1
    return "".join(result)


def _encode(text: str) -> str:
    return "".join(("'" if char in ESCAPES else "") + char for char in text)


def selectors(text: str) -> list[ColumnSelector]:
    if not text.startswith("[") or not text.endswith("]"):
        raise ValueError("Malformed structured table selector")
    stack: list[tuple[int, bool]] = []
    leaves = []
    index = 0
    while index < len(text):
        char = text[index]
        if (
            stack
            and char == "'"
            and index + 1 < len(text)
            and text[index + 1] in ESCAPES
        ):
            index += 2
            continue
        if char == "[":
            if len(stack) >= 2:
                raise ValueError("Unsupported structured selector nesting")
            if stack:
                stack[-1] = (stack[-1][0], True)
            elif index:
                raise ValueError("Multiple outer structured selectors")
            stack.append((index, False))
        elif char == "]":
            if not stack:
                raise ValueError("Unbalanced structured selector brackets")
            start, has_children = stack.pop()
            if not stack and index != len(text) - 1:
                raise ValueError("Content after structured selector")
            if not has_children:
                leaves.append((start + 1, index))
        index += 1
    if stack or not leaves:
        raise ValueError("Unbalanced or empty structured selector")
    if leaves[0][0] != 1:
        # Some producers serialize [[#This Row],Column] with a bare column
        # alongside bracketed item selectors. It is a header, never an A1 token.
        chunks = []
        boundary = 1
        for left, right in leaves:
            chunks.append((boundary, left - 1))
            boundary = right + 1
        chunks.append((boundary, len(text) - 1))
        for left, right in chunks:
            start = index = left
            while index <= right:
                if (
                    index < right
                    and text[index] == "'"
                    and index + 1 < right
                    and text[index + 1] in ESCAPES
                ):
                    index += 2
                    continue
                if index == right or text[index] in ",:":
                    raw = text[start:index]
                    stripped = raw.strip()
                    if stripped and stripped != "@":
                        offset = len(raw) - len(raw.lstrip())
                        leaves.append((start + offset, start + offset + len(stripped)))
                    start = index + 1
                index += 1
        leaves.sort()
    result = []
    outside = list(text)
    for start, end in leaves:
        raw = text[start:end]
        outside[start:end] = " " * (end - start)
        if raw.startswith("@"):
            start += 1
            raw = raw[1:]
            if not raw:
                result.append(ColumnSelector(start, end, None))
                continue
        if raw.startswith("#"):
            if raw.casefold() not in ITEMS:
                raise ValueError("Unknown structured table item selector")
            result.append(ColumnSelector(start, end, None))
        elif not raw:
            raise ValueError("Empty structured column selector")
        else:
            result.append(ColumnSelector(start, end, _decode(raw)))
    if any(char not in "[],:@ \t\r\n" for char in outside):
        raise ValueError("Unsupported structured selector syntax")
    for left_token, right_token in pairwise(result):
        separator = text[left_token.end : right_token.start].strip("[]@ \t\r\n")
        if separator not in {",", ":"}:
            raise ValueError("Ambiguous structured column selector separator")
        if separator == ":" and (left_token.name is None or right_token.name is None):
            raise ValueError("Column intervals require two column endpoints")
    return result


def one_column(text: str) -> str | None:
    columns = [
        selector.name for selector in selectors(text) if selector.name is not None
    ]
    return columns[0] if len(columns) == 1 else None


def rewrite_selector(
    text: str, change: GridTableChange, *, forced_column: str | None = None
) -> str | None:
    """Return None for deleted references; otherwise retain all unchanged syntax."""
    if change.after is None:
        return None
    values = selectors(text)
    replacements: list[tuple[int, int, str]] = []
    index = 0
    while index < len(values):
        current = values[index]
        index += 1
        if current.name is None:
            continue
        if index < len(values) and ":" in text[current.end : values[index].start]:
            other = values[index]
            assert other.name is not None
            if (
                index + 1 < len(values)
                and ":" in text[other.end : values[index + 1].start]
            ):
                raise ValueError(
                    "Chained structured intervals require a range resolver"
                )
            interval = change.interval(current.name, other.name)
            if interval is None:
                return None
            updated = [(current, interval[0]), (other, interval[1])]
            index += 1
        else:
            renamed = (
                forced_column
                if forced_column is not None
                else change.renamed(current.name)
            )
            if renamed is None:
                return None
            updated = [(current, renamed)]
        for selector, name in updated:
            assert selector.name is not None
            original = change.column(selector.name).name
            if name != original:
                encoded = _encode(name)
                if text[selector.start - 1] not in "[@" and any(
                    not char.isalnum() for char in encoded
                ):
                    encoded = "[" + encoded + "]"
                replacements.append((selector.start, selector.end, encoded))
    if not replacements:
        return text
    # A renamed simple selector may now need nested brackets. Retain @ as the
    # current-row operator, escaping a literal @ inside the actual column name.
    if (
        len(values) == 1
        and values[0].start in {1, 2}
        and any(not char.isalnum() for char in replacements[0][2])
    ):
        return (
            "["
            + ("@" if text.startswith("[@") else "")
            + "["
            + replacements[0][2]
            + "]]"
        )
    for start, end, value in reversed(replacements):
        text = text[:start] + value + text[end:]
    return text
