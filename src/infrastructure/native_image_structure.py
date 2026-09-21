"""Bounded TIFF main-directory checks before a decoder can hide a broken chain."""

from typing import Literal

from src.domain.native_image import MAX_IMAGE_FRAMES


def gif_frame_count(data: bytes) -> int | None:
    """Distinguish a real GIF trailer from the decoder's truncated-file EOF."""
    if data[:6] not in {b"GIF87a", b"GIF89a"}:
        return None
    if len(data) < 13:
        raise ValueError("GIF logical screen header is truncated")
    position = 13
    if data[10] & 128:
        position += 3 * 2 ** ((data[10] & 7) + 1)

    def advance(count: int) -> None:
        nonlocal position
        position += count
        if position > len(data):
            raise ValueError("GIF frame sequence is truncated")

    def blocks() -> None:
        while True:
            advance(1)
            size = data[position - 1]
            if not size:
                return
            advance(size)

    count = 0
    while True:
        advance(1)
        kind = data[position - 1]
        if kind == 0x3B:
            if not count:
                raise ValueError("GIF contains no image frames")
            return count
        if kind == 0x21:
            advance(1)  # Extension label, followed by length-prefixed data blocks.
            blocks()
        elif kind == 0x2C:
            advance(9)
            flags = data[position - 1]
            if flags & 128:
                advance(3 * 2 ** ((flags & 7) + 1))
            advance(1)  # LZW minimum code size.
            blocks()
            count += 1
            if count > MAX_IMAGE_FRAMES:
                raise ValueError("Raster document exceeds its frame limit")
        else:
            raise ValueError("GIF contains an invalid frame/extension marker")


def tiff_frame_count(data: bytes) -> int | None:
    if data[:4] not in (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+"):
        return None
    order: Literal["little", "big"] = "little" if data[:2] == b"II" else "big"

    def number(start: int, size: int) -> int:
        if start < 0 or start + size > len(data):
            raise ValueError("TIFF main IFD chain is truncated")
        return int.from_bytes(data[start : start + size], order)

    if number(2, 2) == 43:
        if number(4, 2) != 8 or number(6, 2) != 0:
            raise ValueError("Invalid BigTIFF offset header")
        offset, count_size, entry_size, pointer_size, header_size = (
            number(8, 8),
            8,
            20,
            8,
            16,
        )
    else:
        offset, count_size, entry_size, pointer_size, header_size = (
            number(4, 4),
            2,
            12,
            4,
            8,
        )
    seen = set()
    while offset:
        if offset in seen:
            raise ValueError("TIFF main IFD chain contains a cycle")
        if offset < header_size:
            raise ValueError("TIFF main IFD overlaps the file header")
        seen.add(offset)
        if len(seen) > MAX_IMAGE_FRAMES:
            raise ValueError("Raster document exceeds its frame limit")
        count = number(offset, count_size)
        if count > 20_000:
            raise ValueError("TIFF directory exceeds its entry limit")
        offset = number(offset + count_size + count * entry_size, pointer_size)
    if not seen:
        raise ValueError("TIFF contains no main image directories")
    return len(seen)
