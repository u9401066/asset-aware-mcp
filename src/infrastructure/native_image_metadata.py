"""Bounded typed metadata; binary/rational fields never become guessed strings."""

from __future__ import annotations

import base64
import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any

from PIL import ExifTags
from PIL.PngImagePlugin import iTXt
from PIL.TiffImagePlugin import IFDRational

from src.domain.native_image import MAX_IMAGE_METADATA_BYTES


def canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


class MetadataEncoder:
    def __init__(self) -> None:
        self.remaining = MAX_IMAGE_METADATA_BYTES
        self.nodes = 0

    def encode(self, value: Any, depth: int = 0) -> Any:
        result: Any
        self.nodes += 1
        if depth > 12 or self.nodes > 20_000:
            raise ValueError("Image metadata exceeds its nesting/node limit")
        if value is None or type(value) is bool:
            result = value
        elif isinstance(value, IFDRational):
            result = {
                "type": "rational",
                "numerator": str(value.numerator),
                "denominator": str(value.denominator),
            }
        elif type(value) is int:
            result = {"type": "integer", "decimal": str(value)}
        elif type(value) is float:
            result = {
                "type": "float",
                "hex": value.hex(),
                "finite": math.isfinite(value),
            }
        elif isinstance(value, iTXt):
            return {
                "type": "international_text",
                "text": self.encode(str(value), depth + 1),
                "language": self.encode(value.lang, depth + 1),
                "translated_keyword": self.encode(value.tkey, depth + 1),
            }
        elif isinstance(value, str):
            try:
                value.encode("utf-8")
                result = {"type": "text", "value": str(value)}
            except UnicodeEncodeError:
                result = {
                    "type": "text_with_surrogates",
                    "encoding": "utf-8/surrogatepass",
                    "base64": base64.b64encode(
                        value.encode("utf-8", "surrogatepass")
                    ).decode("ascii"),
                }
        elif isinstance(value, (bytes, bytearray)):
            if len(value) > self.remaining:
                raise ValueError("Image metadata exceeds its byte limit")
            result = {
                "type": "bytes",
                "size": len(value),
                "sha256": hashlib.sha256(value).hexdigest(),
                "base64": base64.b64encode(value).decode("ascii"),
            }
        elif isinstance(value, Mapping):
            return {
                "type": "mapping",
                "entries": [
                    {
                        "key": self.encode(key, depth + 1),
                        "value": self.encode(item, depth + 1),
                    }
                    for key, item in sorted(
                        value.items(),
                        key=lambda pair: (type(pair[0]).__name__, str(pair[0])),
                    )
                ],
            }
        elif isinstance(value, (tuple, list)):
            return {
                "type": "tuple" if isinstance(value, tuple) else "list",
                "items": [self.encode(item, depth + 1) for item in value],
            }
        else:
            raise ValueError(
                f"Image metadata exposes an unsupported value type: {type(value).__name__}"
            )
        self.remaining -= len(json.dumps(result, ensure_ascii=True).encode())
        if self.remaining < 0:
            raise ValueError("Image metadata exceeds its byte limit")
        return result


def metadata_record(image: Any) -> dict[str, Any]:
    encoder = MetadataEncoder()
    exif = image.getexif()
    root = dict(exif)
    nested = {}
    for tag in (ExifTags.IFD.Exif, ExifTags.IFD.GPSInfo):
        if tag in exif:
            nested[str(int(tag))] = dict(exif.get_ifd(tag))
    if int(ExifTags.IFD.Interop) in nested.get(str(int(ExifTags.IFD.Exif)), {}):
        nested[str(int(ExifTags.IFD.Interop))] = dict(
            exif.get_ifd(ExifTags.IFD.Interop)
        )
    result = {
        "info": encoder.encode(image.info),
        "exif_ifd0": encoder.encode(root),
        "exif_sub_ifds": encoder.encode(nested),
        "tiff_ifd": encoder.encode(dict(image.tag_v2))
        if hasattr(image, "tag_v2")
        else None,
        "palette": encoder.encode(image.palette.tobytes()) if image.palette else None,
        "palette_mode": image.palette.mode if image.palette else None,
        "coverage": "All metadata values exposed by this decoder, not a claim that every private container field is understood. Exact original bytes remain the authority.",
    }
    encoded = canonical(result)
    if len(encoded) > MAX_IMAGE_METADATA_BYTES:
        raise ValueError("Image metadata representation exceeds its byte limit")
    result["metadata_sha256"] = hashlib.sha256(encoded).hexdigest()
    return result
