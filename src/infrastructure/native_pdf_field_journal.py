"""Journal only planned native keys/arrays; reject shared containers and dangling refs."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Any

import pikepdf

if TYPE_CHECKING:
    from collections.abc import Iterable

MAX_DEPENDENCY_NODES = 500_000


def indirect_edges(pdf: pikepdf.Pdf) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    edges = []
    visited = 0

    def scan(value: Any, owner: tuple[int, int], depth: int = 0) -> None:
        nonlocal visited
        visited += 1
        if depth > 100 or visited > MAX_DEPENDENCY_NODES:
            raise ValueError("PDF form dependency scan exceeds its limit")
        children: Iterable[Any]
        if isinstance(value, (pikepdf.Dictionary, pikepdf.Stream)):
            children = (child for _, child in value.items())
        elif isinstance(value, pikepdf.Array):
            children = value
        else:
            return
        for child in children:
            if isinstance(child, pikepdf.Object) and child.is_indirect:
                visited += 1
                if visited > MAX_DEPENDENCY_NODES:
                    raise ValueError("PDF form dependency scan exceeds its limit")
                edges.append((owner, child.objgen))
            else:
                scan(child, owner, depth + 1)

    for obj in pdf.objects:
        scan(obj, obj.objgen)
    scan(pdf.trailer, (-1, -1))
    return edges


class FieldJournal:
    def __init__(self, pdf: pikepdf.Pdf):
        self.pdf = pdf
        self.incoming = Counter(target for _, target in indirect_edges(pdf))
        self.entries: list[tuple[pikepdf.Object, str | None, Any, bool]] = []

    def set_key(self, obj: pikepdf.Object, key: str, value: Any) -> None:
        self.entries.append((obj, key, obj.get(key), key in obj))
        if value is None:
            if key in obj:
                del obj[key]
        else:
            obj[key] = value

    def array(self, obj: pikepdf.Object, values: list[pikepdf.Object]) -> None:
        if obj.is_indirect and self.incoming.get(obj.objgen, 1) != 1:
            raise ValueError("PDF form array has shared or external ownership")
        self.entries.append((obj, None, list(obj), True))
        self._replace(obj, values)

    @staticmethod
    def _replace(obj: pikepdf.Object, values: list[pikepdf.Object]) -> None:
        for index in range(len(obj) - 1, -1, -1):
            del obj[index]
        obj.extend(values)

    def check_deleted(self, identities: set[tuple[int, int]]) -> None:
        for owner, target in indirect_edges(self.pdf):
            if target in identities and owner not in identities:
                raise ValueError(
                    "PDF field deletion leaves an incoming native dependency"
                )

    def undo(self) -> None:
        for obj, key, value, present in reversed(self.entries):
            if key is None:
                self._replace(obj, value)
            elif present:
                obj[key] = value
            elif key in obj:
                del obj[key]
