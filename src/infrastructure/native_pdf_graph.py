"""Bounded PDF object graphs independent of serialized object numbering."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from typing import Any

import pikepdf

MAX_GRAPH_NODES = 50_000
MAX_GRAPH_BYTES = 64 * 1024 * 1024
MAX_GRAPH_DEPTH = 100


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def graph_digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


class PdfObjectGraph:
    """Page references use caller identities; cycles retain explicit local edges."""

    def __init__(self, pages: dict[tuple[int, int], str]):
        self.pages = pages
        self.seen: dict[tuple[int, int], int] = {}
        self.nodes: list[Any] = []
        self.size = 0

    def describe(
        self,
        value: Any,
        *,
        root_page: bool = False,
        ignore_root_keys: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        self.root_skips = set(ignore_root_keys)
        root = self._value(value, 0, root_page=root_page)
        result = {"root": root, "objects": self.nodes}
        if len(canonical(result)) > MAX_GRAPH_BYTES:
            raise ValueError("PDF object graph exceeds its representation limit")
        return result

    def _value(self, value: Any, depth: int, *, root_page: bool = False) -> Any:
        if depth > MAX_GRAPH_DEPTH:
            raise ValueError("PDF object graph exceeds its nesting limit")
        if isinstance(value, pikepdf.Object):
            if (
                isinstance(value, pikepdf.Dictionary)
                and value.get("/Type") == pikepdf.Name.Page
                and not root_page
            ):
                if value.objgen not in self.pages:
                    raise ValueError(
                        "PDF has a surviving reference to an unselected page"
                    )
                return {"page": self.pages[value.objgen]}
            if value.is_indirect:
                if value.objgen in self.seen:
                    return {"ref": self.seen[value.objgen]}
                if len(self.nodes) >= MAX_GRAPH_NODES:
                    raise ValueError("PDF object graph exceeds its object limit")
                index = len(self.nodes)
                self.seen[value.objgen] = index
                self.nodes.append(None)
                self.nodes[index] = self._content(value, depth + 1)
                return {"ref": index}
            return self._content(value, depth + 1)
        if isinstance(value, (Decimal, float, int)) and not isinstance(value, bool):
            return {"number": str(Decimal(str(value)).normalize())}
        if value is None or isinstance(value, (bool, int, str)):
            return value
        raise ValueError(f"Unsupported PDF object value: {type(value).__name__}")

    def _content(self, value: pikepdf.Object, depth: int) -> Any:
        if isinstance(value, pikepdf.Array):
            return [self._value(item, depth) for item in value]
        if isinstance(value, (pikepdf.Dictionary, pikepdf.Stream)):
            excluded = {"/Length"} if isinstance(value, pikepdf.Stream) else set()
            if depth == 1:
                excluded.update(self.root_skips)
            if value.get("/Type") == pikepdf.Name.Page:
                excluded.add("/Parent")
            result = {
                key: self._value(value[key], depth)
                for key in sorted(value.keys())
                if key not in excluded
            }
            if isinstance(value, pikepdf.Stream):
                raw = value.read_raw_bytes()
                self.size += len(raw)
                if self.size > MAX_GRAPH_BYTES:
                    raise ValueError("PDF object graph exceeds its stream byte limit")
                return {
                    "dictionary": result,
                    "raw_stream_sha256": hashlib.sha256(raw).hexdigest(),
                    "raw_size": len(raw),
                }
            return {"dictionary": result}
        if isinstance(value, pikepdf.Name):
            return {"name": str(value)}
        if isinstance(value, pikepdf.String):
            raw = bytes(value)
            self.size += len(raw)
            if self.size > MAX_GRAPH_BYTES:
                raise ValueError("PDF object graph exceeds its string byte limit")
            return {"string_hex": raw.hex()}
        raise ValueError("Unsupported PDF object type")
