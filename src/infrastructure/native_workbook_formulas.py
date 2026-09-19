"""Lossless local sheet qualifiers using openpyxl tokens, without evaluating formulas."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from openpyxl.formula.tokenizer import Token, Tokenizer, TokenizerError

if TYPE_CHECKING:
    from collections.abc import Iterator

MAX_FORMULA_CHARS = 65_536


@dataclass(frozen=True)
class NativeSheetToken:
    start: int
    end: int
    names: tuple[str, ...]


def _spill_shadow(text: str) -> str:
    # The tokenizer predates dynamic array spill postfixes. Replace only postfix
    # hashes with one identifier character for lexing; all output uses original
    # spans. Error literals and quoted strings/sheet names remain untouched.
    output = list(text)
    quote = None
    brackets = 0
    index = 0
    while index < len(text):
        char = text[index]
        if quote:
            if char == quote:
                if index + 1 < len(text) and text[index + 1] == quote:
                    index += 2
                    continue
                quote = None
        elif brackets:
            if char == "[":
                brackets += 1
            elif char == "]":
                brackets -= 1
        elif char == "[":
            brackets = 1
        elif char in {'"', "'"}:
            quote = char
        elif char in "\t\r":
            output[index] = " "
        elif (
            char == "#"
            and index
            and (text[index - 1].isalnum() or text[index - 1] in "_)]")
        ):
            output[index] = "_"
        index += 1
    if quote:
        raise ValueError("Unterminated quote in workbook formula")
    return "".join(output)


def formula_tokens(text: str) -> Iterator[tuple[int, int, str, str, str]]:
    if len(text) > MAX_FORMULA_CHARS:
        raise ValueError("Workbook formula exceeds the character budget")
    shadow = _spill_shadow("=" + text)
    try:
        tokens = Tokenizer(shadow).items
    except (TokenizerError, IndexError, ValueError) as exc:
        raise ValueError("Unsupported workbook formula syntax") from exc
    cursor = 1
    for token in tokens:
        if token.type == Token.WSPACE:
            matched = Tokenizer.WSPACE_RE.match(shadow[cursor:])
            if matched is None:
                raise ValueError("Formula whitespace cannot be located losslessly")
            end = cursor + matched.end()
        else:
            end = cursor + len(token.value)
            if shadow[cursor:end] != token.value:
                raise ValueError("Formula token cannot be located losslessly")
        yield cursor - 1, end - 1, text[cursor - 1 : end - 1], token.type, token.subtype
        cursor = end
    if cursor != len(shadow):
        raise ValueError("Formula tokenizer did not consume the complete input")


def _unquote(name: str) -> str:
    if name.startswith("'"):
        if not re.fullmatch(r"'(?:[^']|'')*'", name):
            raise ValueError("Ambiguous quoted worksheet qualifier")
        return name[1:-1].replace("''", "'")
    if not name or re.search(r"[\s'!]", name):
        raise ValueError("Ambiguous worksheet qualifier")
    return name


def _qualifier_spans(value: str) -> list[tuple[int, int]]:
    """Find bangs outside sheet quotes/table brackets, including range endpoints."""
    bangs, colons = [], []
    quoted, brackets, index = False, 0, 0
    while index < len(value):
        char = value[index]
        if quoted:
            if char == "'":
                if index + 1 < len(value) and value[index + 1] == "'":
                    index += 2
                    continue
                quoted = False
        elif brackets:
            if char == "[":
                brackets += 1
            elif char == "]":
                brackets -= 1
        elif char == "[":
            brackets = 1
        elif char == "'":
            quoted = True
        elif char == "!":
            bangs.append(index)
        elif char == ":":
            colons.append(index)
        index += 1
    spans, previous = [], None
    for bang in bangs:
        start = 0
        if previous is not None:
            boundaries = [at for at in colons if previous < at < bang]
            if len(boundaries) != 1:
                raise ValueError("Ambiguous qualified range endpoints")
            start = boundaries[0] + 1
        if bang == len(value) - 1:
            raise ValueError("Worksheet qualifier has no following reference")
        spans.append((start, bang))
        previous = bang
    return spans


def sheet_references(text: str) -> list[NativeSheetToken]:
    references = []
    for start, _end, value, kind, subtype in formula_tokens(text):
        if kind != Token.OPERAND or subtype != Token.RANGE or "!" not in value:
            continue
        for local_start, local_end in _qualifier_spans(value):
            prefix = value[local_start:local_end]
            if "[" in prefix or "]" in prefix or prefix == "#REF":
                continue  # External workbook qualifier.
            if prefix.startswith("@"):
                local_start += 1
                prefix = prefix[1:]
            if re.fullmatch(r"'(?:[^']|'')*'", prefix):
                names = tuple(_unquote(prefix).split(":"))
            else:
                names = tuple(_unquote(name) for name in prefix.split(":"))
            if not 1 <= len(names) <= 2 or not all(names):
                raise ValueError("Unsupported 3D worksheet qualifier")
            references.append(
                NativeSheetToken(start + local_start, start + local_end, names)
            )
    return references


def rename_sheet_references(text: str, old: str, new: str) -> tuple[str, int]:
    edits = []
    for reference in sheet_references(text):
        if any(name.casefold() == old.casefold() for name in reference.names):
            names = [
                new if name.casefold() == old.casefold() else name
                for name in reference.names
            ]
            prefix = "'" + ":".join(names).replace("'", "''") + "'"
            edits.append((reference.start, reference.end, prefix))
    for start, end, prefix in reversed(edits):
        text = text[:start] + prefix + text[end:]
    return text, len(edits)


def table_references(text: str) -> set[str]:
    names = set()
    for _start, _end, value, kind, subtype in formula_tokens(text):
        if kind != Token.OPERAND or subtype != Token.RANGE:
            continue
        spans = _qualifier_spans(value)
        if spans:
            start, end = spans[-1]
            if "[" in value[start:end] or "]" in value[start:end]:
                continue
            value = value[end + 1 :]
        if "[" in value and not value.startswith("["):
            names.add(value.split("[", 1)[0].removeprefix("@").casefold())
        elif re.fullmatch(r"[\w.\\]+", value.removeprefix("@")):
            # A whole table is also a valid operand: SUM(Table1).
            names.add(value.removeprefix("@").casefold())
    return names
