"""Prove redundant direct stream lengths against original PDF bytes, not last-wins."""

from __future__ import annotations

import hashlib
import re
from typing import Any

import pikepdf

from src.infrastructure.native_pdf_graph import canonical

_SPACE = rb"[\x00\t\n\f\r ]"
_SKIP = re.compile(rb"(?:[\x00\t\n\f\r ]|%[^\r\n]*(?:\r\n|\r|\n|$))*")
_TOKEN = re.compile(
    rb"<<|>>|\[|\]|/[^\x00\t\n\f\r ()<>\[\]{}/%]+|[^\x00\t\n\f\r ()<>\[\]{}/%]+"
)
_WARNING = re.compile(
    r"\(object (\d+) (\d+), offset (\d+)\): dictionary has duplicated key /Length; last occurrence overrides earlier ones$"
)
_INTEGER = re.compile(rb"[+-]?\d{1,18}\Z")
_HEADER = re.compile(rb"(\d+)" + _SPACE + rb"+(\d+)" + _SPACE + rb"+obj\b")


def _name(raw: bytes) -> bytes:
    if re.search(rb"#(?![0-9a-fA-F]{2})", raw):
        raise ValueError("Malformed PDF name escape")
    return re.sub(rb"#([0-9a-fA-F]{2})", lambda m: bytes([int(m[1], 16)]), raw)


class _Dictionary:
    """Deliberately small grammar; unsupported strings require explicit repair."""

    def __init__(self, data: bytes, start: int):
        self.data = data[start : start + 65536]
        self.position = 0
        self.tokens = 0
        self.lengths: list[int] = []

    def token(self) -> bytes:
        skip = _SKIP.match(self.data, self.position)
        assert skip is not None
        match = _TOKEN.match(self.data, skip.end())
        self.tokens += 1
        if match is None or self.tokens > 16384:
            raise ValueError("Unsupported or oversized PDF stream dictionary")
        self.position = match.end()
        return match[0]

    def value(self, token: bytes, depth: int) -> tuple[str, Any]:
        if depth > 32:
            raise ValueError("PDF stream dictionary exceeds nesting limit")
        if token == b"<<":
            seen = set()
            while (key := self.token()) != b">>":
                if not key.startswith(b"/"):
                    raise ValueError("Expected PDF dictionary key")
                key = _name(key)
                if key in seen and not (depth == 0 and key == b"/Length"):
                    raise ValueError("Unverified duplicate PDF dictionary key")
                seen.add(key)
                kind, value = self.value(self.token(), depth + 1)
                if depth == 0 and key == b"/Length":
                    if kind != "integer" or value < 0:
                        raise ValueError(
                            "Redundant stream lengths must be direct integers"
                        )
                    self.lengths.append(value)
            return "dictionary", None
        if token == b"[":
            while (item := self.token()) != b"]":
                self.value(item, depth + 1)
            return "array", None
        if _INTEGER.fullmatch(token):
            # Detect an indirect reference without consuming the following value.
            position, count = self.position, self.tokens
            next_token = self.token()
            indirect = _INTEGER.fullmatch(next_token) and self.token() == b"R"
            if indirect:
                return "reference", None
            self.position, self.tokens = position, count
            return "integer", int(token)
        if token.startswith(b"/"):
            return "name", _name(token)
        if token in {b"true", b"false", b"null"} or re.fullmatch(
            rb"[+-]?(?:\d+\.\d*|\.\d+)", token
        ):
            return "scalar", None
        raise ValueError("Unsupported PDF dictionary value")


def _verify(data: bytes, pdf: pikepdf.Pdf, xref: dict, warning: str) -> dict:
    match = _WARNING.search(warning)
    if match is None:
        raise ValueError("Native PDF parser reported warnings; repair separately")
    key = int(match[1]), int(match[2])
    entry = xref.get(key)
    if entry is None or entry.type != 1:
        raise ValueError(
            "Redundant PDF length requires an original uncompressed object"
        )
    header = _HEADER.match(data, entry.offset)
    if header is None or (int(header[1]), int(header[2])) != key:
        raise ValueError("PDF xref/object header mismatch")
    skip = _SKIP.match(data, header.end())
    assert skip is not None
    start = skip.end()
    if data[start : start + 2] != b"<<" or start + 2 != int(match[3]):
        raise ValueError("Duplicate length warning is not the root stream dictionary")
    parser = _Dictionary(data, start)
    parser.value(parser.token(), 0)
    lengths = parser.lengths
    if len(lengths) < 2 or len(set(lengths)) != 1:
        raise ValueError("Conflicting or missing redundant stream lengths")
    end = start + parser.position
    skip = _SKIP.match(data, end)
    assert skip is not None
    stream = re.match(rb"stream(?:\r\n|\r|\n)", data[skip.end() : skip.end() + 9])
    if stream is None:
        raise ValueError("Expected original PDF stream boundary")
    stream_start = skip.end() + stream.end()
    stream_end = stream_start + lengths[0]
    obj = pdf.get_object(*key)
    if not isinstance(obj, pikepdf.Stream) or lengths[0] > len(data):
        raise ValueError("Redundant Length does not describe a bounded stream")
    raw = obj.read_raw_bytes()
    if len(raw) != lengths[0] or data[stream_start:stream_end] != raw:
        raise ValueError("Declared PDF lengths disagree with original raw stream bytes")
    if not re.match(rb"(?:\r\n|\r|\n)?endstream\b", data[stream_end : stream_end + 16]):
        raise ValueError("Declared PDF length misses original endstream boundary")
    return {
        "object": list(key),
        "dictionary_span": [start, end],
        "dictionary_sha256": hashlib.sha256(data[start:end]).hexdigest(),
        "length": lengths[0],
        "declarations": len(lengths),
    }


def verified_parser_checks(
    data: bytes, pdf: pikepdf.Pdf, warnings: list[str]
) -> list[dict[str, Any]]:
    if not warnings:
        return []
    xref = pdf.get_xref_table()
    proofs = [_verify(data, pdf, xref, warning) for warning in warnings]
    by_object = {tuple(p["object"]): p for p in proofs}
    if len(proofs) != sum(p["declarations"] - 1 for p in by_object.values()):
        raise ValueError("Unaccounted duplicate PDF length diagnostics")
    if pdf.get_warnings():
        raise ValueError("Additional PDF warnings require separate repair")
    unique = sorted(by_object.values(), key=lambda p: p["object"])
    return [
        {
            "policy": "identical_direct_stream_length_v1",
            "verified_stream_count": len(unique),
            "declaration_count": sum(p["declarations"] for p in unique),
            "proof_sha256": hashlib.sha256(canonical(unique)).hexdigest(),
            "source_bytes_preserved": True,
            "scope": "Equal direct lengths and original raw stream boundaries; no general PDF repair or semantic verdict",
        }
    ]
