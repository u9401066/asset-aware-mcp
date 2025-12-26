"""
Domain Layer - Value Objects

Immutable objects that describe characteristics of entities.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any


class AssetType(str, Enum):
    """Asset types in a document."""

    TABLE = "table"
    FIGURE = "figure"
    SECTION = "section"
    FULL_TEXT = "full_text"


class DocId:
    """
    Value Object for Document Identifier.

    Validated and immutable document ID.
    Format: doc_{name}_{hash}
    """

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        if not self._is_valid(value):
            raise ValueError(f"Invalid doc_id format: {value}")
        self._value = value

    @staticmethod
    def _is_valid(value: str) -> bool:
        """Validate doc_id format."""
        if not value:
            return False
        # Must start with 'doc_' and contain only alphanumeric + underscore
        return bool(re.match(r"^doc_[a-z0-9_]+$", value))

    @classmethod
    def generate(cls, filename: str, unique_suffix: str) -> DocId:
        """Generate a new DocId from filename."""
        import hashlib

        # Clean filename
        name = re.sub(r"[^a-z0-9]", "_", filename.lower())[:30]
        # Add hash for uniqueness
        hash_suffix = hashlib.md5(unique_suffix.encode()).hexdigest()[:6]
        return cls(f"doc_{name}_{hash_suffix}")

    @property
    def value(self) -> str:
        return self._value

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"DocId({self._value!r})"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, DocId):
            return self._value == other._value
        if isinstance(other, str):
            return self._value == other
        return False

    def __hash__(self) -> int:
        return hash(self._value)


class ImageMediaType(str, Enum):
    """Supported image MIME types."""

    PNG = "image/png"
    JPEG = "image/jpeg"
    GIF = "image/gif"
    WEBP = "image/webp"
    BMP = "image/bmp"

    @classmethod
    def from_extension(cls, ext: str) -> ImageMediaType:
        """Get media type from file extension."""
        ext_map = {
            "png": cls.PNG,
            "jpg": cls.JPEG,
            "jpeg": cls.JPEG,
            "gif": cls.GIF,
            "webp": cls.WEBP,
            "bmp": cls.BMP,
        }
        return ext_map.get(ext.lower(), cls.PNG)
