"""Strict decoding with original-byte boundaries, including legacy code-page aliases."""

from __future__ import annotations

import codecs
from array import array
from dataclasses import dataclass

from src.domain.native_delimited import MAX_DELIMITED_BYTES

BOMS = {
    "utf-8": codecs.BOM_UTF8,
    "utf-16-le": codecs.BOM_UTF16_LE,
    "utf-16-be": codecs.BOM_UTF16_BE,
}


@dataclass
class TextSource:
    data: bytes
    text: str
    encoding: str
    bom: bytes
    offsets: array

    def byte_span(self, start: int, end: int) -> tuple[int, int]:
        return self.offsets[start], self.offsets[end]


def decode_source(data: bytes, requested: str | None) -> TextSource:
    if len(data) > MAX_DELIMITED_BYTES:
        raise ValueError("Delimited file exceeds the byte budget")
    if data.startswith((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)):
        raise ValueError("UTF-32 needs a dedicated text adapter")
    found = next((name for name, bom in BOMS.items() if data.startswith(bom)), None)
    if found and requested and found != requested:
        raise ValueError("Explicit encoding conflicts with source BOM")
    encoding = requested or found or "utf-8"
    bom = BOMS[found] if found else b""
    body = data[len(bom) :]
    text = body.decode(encoding, errors="strict")
    offsets = array("I", [len(bom)])
    if encoding == "cp950":
        # Some legacy byte sequences decode to an alias that re-encodes differently.
        # Track actual consumed bytes instead of estimating via re-encoding text.
        decoder = codecs.getincrementaldecoder(encoding)(errors="strict")
        for index, byte in enumerate(body, start=len(bom) + 1):
            value = decoder.decode(bytes((byte,)))
            if value:
                if len(value) != 1:
                    raise ValueError("Ambiguous legacy character boundary")
                offsets.append(index)
        if decoder.decode(b"", final=True):
            raise ValueError("Incomplete legacy character boundary")
    else:
        position = len(bom)
        for char in text:
            point = ord(char)
            if encoding == "utf-8":
                size = (
                    1
                    if point < 0x80
                    else 2
                    if point < 0x800
                    else 3
                    if point < 0x10000
                    else 4
                )
            elif encoding.startswith("utf-16-"):
                size = 2 if point <= 0xFFFF else 4
            else:
                size = 1
            position += size
            offsets.append(position)
    if len(offsets) != len(text) + 1 or offsets[-1] != len(data):
        raise ValueError("Decoded characters do not map to exact source bytes")
    return TextSource(data, text, encoding, bom, offsets)
