"""Script-aware text diff rules shared by tracked write-back and revision sidecars."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

# Scripts written without spaces between words. Each character is its own diff
# token so a small edit does not delete and re-insert the whole sentence.
# Hangul is excluded because Korean separates words with spaces.
_CJK_CHAR_CLASS = (
    "\u2e80-\u2fdf"  # CJK and Kangxi radicals
    "\u2ff0-\u303f"  # ideographic description characters, CJK punctuation
    "\u3040-\u30ff"  # Hiragana, Katakana
    "\u3100-\u312f"  # Bopomofo
    "\u31a0-\u31ff"  # Bopomofo extended, CJK strokes, Katakana extensions
    "\u3200-\u4dbf"  # enclosed CJK, CJK compatibility, CJK extension A
    "\u4e00-\u9fff"  # CJK unified ideographs
    "\uf900-\ufaff"  # CJK compatibility ideographs
    "\ufe10-\ufe1f"  # vertical forms
    "\ufe30-\ufe4f"  # CJK compatibility forms
    "\uff00-\uffef"  # halfwidth and fullwidth forms
    "\U00020000-\U0003ffff"  # CJK extensions B and later
)
_REVISION_DIFF_TOKEN_RE = re.compile(
    rf"\s+|[{_CJK_CHAR_CLASS}]|[^\s{_CJK_CHAR_CLASS}]+"
)
_CJK_CHAR_RE = re.compile(rf"[{_CJK_CHAR_CLASS}]")

DiffOpcode = tuple[str, int, int, int, int]


def tokenize_revision_diff_text(text: str) -> list[str]:
    """Split text into diff tokens whose concatenation is exactly ``text``.

    Whitespace runs and space-delimited words stay single tokens; CJK
    characters and full-width punctuation become one token each.
    """
    if not text:
        return []
    return _REVISION_DIFF_TOKEN_RE.findall(text)


def revision_diff_opcodes(
    old_tokens: Sequence[str], new_tokens: Sequence[str]
) -> list[DiffOpcode]:
    """Return ``SequenceMatcher`` opcodes tuned for readable tracked changes.

    A single CJK character that matches only by coincidence inside a rewritten
    span (a ``replace`` on both sides, for example a shared ``的``) is folded
    into one replacement, so rewritten CJK clauses do not fragment into
    character-level confetti. Pure insertions and deletions are never widened,
    which keeps existing text (and its authorship) untouched.
    """
    opcodes = SequenceMatcher(
        None, list(old_tokens), list(new_tokens), autojunk=False
    ).get_opcodes()
    absorbed: list[DiffOpcode] = []
    for index, (opcode_tag, i1, i2, j1, j2) in enumerate(opcodes):
        tag: str = opcode_tag
        if (
            tag == "equal"
            and 0 < index < len(opcodes) - 1
            and opcodes[index - 1][0] == "replace"
            and opcodes[index + 1][0] == "replace"
            and i2 - i1 == 1
            and _CJK_CHAR_RE.fullmatch(old_tokens[i1]) is not None
        ):
            tag = "replace"
        absorbed.append((tag, i1, i2, j1, j2))

    merged: list[DiffOpcode] = []
    for change_tag, i1, i2, j1, j2 in absorbed:
        if merged and change_tag != "equal" and merged[-1][0] != "equal":
            _prev_tag, prev_i1, _prev_i2, prev_j1, _prev_j2 = merged[-1]
            merged[-1] = (
                _change_tag(prev_i1, i2, prev_j1, j2),
                prev_i1,
                i2,
                prev_j1,
                j2,
            )
            continue
        merged.append((change_tag, i1, i2, j1, j2))
    return merged


def _change_tag(i1: int, i2: int, j1: int, j2: int) -> str:
    if i1 == i2:
        return "insert"
    if j1 == j2:
        return "delete"
    return "replace"
