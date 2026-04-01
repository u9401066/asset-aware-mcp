"""
Infrastructure Layer - Encoding Guard

Early-stage encoding validation and normalisation utilities for the
ingestion / export pipeline.

Design goal: **fail-closed**.  Suspicious or undecodable input is
rejected with a clear error rather than being silently mangled.

Covered cases
-------------
- Wrong file content (non-ZIP) supplied with a .docx extension
- UTF-8 BOM (EF BB BF) in text content or user-provided strings
- UTF-16 LE/BE BOMs (FF FE / FE FF) in text content
- Non-ASCII characters in document-ID stems (filesystem safety)
- Undecodable byte sequences (latin-1 / Big5 / GBK bytes in a
  nominally UTF-8 context)

Not in scope
------------
- Full charset detection (chardet/charset-normalizer dependency).
  We intentionally keep this dependency-free and rely on Python's
  built-in codecs with a defined fallback ladder:
      UTF-8-BOM → UTF-8 → UTF-16 → fail
"""

from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# ============================================================================
# Constants
# ============================================================================

# ZIP local-file-header magic (PK\x03\x04)
_ZIP_MAGIC = b"PK\x03\x04"

# BOM byte sequences, longest first so we strip the right one.
_BOMS: list[tuple[bytes, str]] = [
    (b"\xff\xfe\x00\x00", "UTF-32 LE"),   # must precede UTF-16 LE
    (b"\x00\x00\xfe\xff", "UTF-32 BE"),
    (b"\xff\xfe", "UTF-16 LE"),
    (b"\xfe\xff", "UTF-16 BE"),
    (b"\xef\xbb\xbf", "UTF-8 BOM"),
]


# ============================================================================
# Custom exception
# ============================================================================

class EncodingError(ValueError):
    """Raised when input violates encoding expectations."""


# ============================================================================
# Public API
# ============================================================================

def validate_zip_magic(path: Path) -> None:
    """Verify that *path* starts with the ZIP magic bytes.

    .docx files are ZIP archives.  If the file fails this check it is
    corrupt, misnamed, or malicious.

    Raises:
        EncodingError: if the file does not start with PK\\x03\\x04.
        FileNotFoundError: if the file does not exist.
    """
    with path.open("rb") as fh:
        header = fh.read(4)
    if header[:4] != _ZIP_MAGIC:
        raise EncodingError(
            f"File does not appear to be a valid ZIP/DOCX archive "
            f"(bad magic bytes: {header!r}): {path}"
        )


def strip_bom(text: str) -> str:
    """Remove a leading Unicode BOM (U+FEFF) from *text* if present.

    Handles strings that were decoded from UTF-8-BOM, UTF-16-LE/BE, or
    where a BOM was inserted by an editor.

    Returns the cleaned string (unchanged if no BOM present).
    """
    if text.startswith("\ufeff"):
        return text[1:]
    return text


def strip_bom_bytes(data: bytes) -> tuple[bytes, str | None]:
    """Strip a BOM from raw bytes.

    Returns:
        (stripped_bytes, bom_name | None)

    The *bom_name* describes which BOM was found, or None if none.
    """
    for bom_bytes, bom_name in _BOMS:
        if data.startswith(bom_bytes):
            return data[len(bom_bytes):], bom_name
    return data, None


def safe_decode(data: bytes, hint: str = "<unknown>") -> str:
    """Decode *data* to ``str``, trying a safe encoding ladder.

    Ladder (fail-closed):
    1. UTF-8 (strict) — after stripping any UTF-8 BOM
    2. UTF-16 — if a UTF-16 BOM is present
    3. Raise ``EncodingError`` for anything else

    Args:
        data: Raw bytes to decode.
        hint: Human-readable label (file path / field name) for error
              messages.

    Returns:
        Decoded string with no leading BOM character.

    Raises:
        EncodingError: if the bytes cannot be decoded as UTF-8 or UTF-16.
    """
    stripped, bom_name = strip_bom_bytes(data)

    # UTF-16 with explicit BOM — delegate to Python's UTF-16 codec
    if bom_name in ("UTF-16 LE", "UTF-16 BE"):
        try:
            return stripped.decode("utf-16-le" if bom_name == "UTF-16 LE" else "utf-16-be")
        except UnicodeDecodeError as exc:
            raise EncodingError(
                f"Failed to decode {hint!r} as {bom_name}: {exc}"
            ) from exc

    # UTF-32 — uncommon, surface a clear error rather than mangling
    if bom_name in ("UTF-32 LE", "UTF-32 BE"):
        raise EncodingError(
            f"{hint!r} appears to be {bom_name}-encoded text, which is not "
            "supported by this pipeline.  Please re-save the file as UTF-8."
        )

    # UTF-8 (with or without BOM)
    try:
        text = stripped.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise EncodingError(
            f"File {hint!r} contains bytes that are not valid UTF-8 "
            f"(offset {exc.start}–{exc.end}).  "
            "If the file uses a legacy encoding (Big5, GBK, Latin-1, etc.) "
            "please convert it to UTF-8 first."
        ) from exc

    # Strip any residual BOM character (U+FEFF) from UTF-8-BOM decode
    return strip_bom(text)


def sanitize_id_stem(raw: str, *, maxlen: int = 30) -> str:
    """Convert an arbitrary filename stem to a safe ASCII identifier.

    Steps:
    1. NFKD-normalise to decompose composed characters.
    2. Drop non-ASCII codepoints (accents, CJK, etc.).
    3. Lowercase the result.
    4. Replace any character outside ``[a-z0-9]`` with ``_``.
    5. Collapse consecutive underscores and strip leading/trailing ones.
    6. Truncate to *maxlen* characters.
    7. Fall back to ``"doc"`` if the result is empty.

    This matches the sanitisation already applied by ``DocxAdapter``
    so that ``DocxService`` can generate a consistent doc_id.

    Examples::

        sanitize_id_stem("Hello World!")   -> "hello_world"
        sanitize_id_stem("病歷報告_2024")   -> "2024"
        sanitize_id_stem("résumé.docx")    -> "resume_docx"
        sanitize_id_stem("")               -> "doc"
    """
    # Decompose unicode
    normalized = unicodedata.normalize("NFKD", raw)
    # Keep only ASCII characters
    ascii_only = normalized.encode("ascii", errors="ignore").decode("ascii")
    # Lowercase + replace non-alphanumeric with underscore
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_only.lower())
    # Strip edges and collapse
    slug = slug.strip("_")
    # Truncate
    slug = slug[:maxlen]
    return slug or "doc"


def normalize_text_input(text: str, hint: str = "<input>") -> str:
    """Normalise a user-supplied text string for ingestion.

    - Strips leading BOM (U+FEFF).
    - Normalises line endings to LF.
    - Rejects strings containing the NULL byte (likely binary data).

    Args:
        text: The raw input string.
        hint: Label used in error messages.

    Returns:
        Cleaned string.

    Raises:
        EncodingError: if the string contains NUL bytes.
    """
    text = strip_bom(text)
    if "\x00" in text:
        raise EncodingError(
            f"{hint!r} contains NUL bytes, which suggests it is binary data "
            "rather than text.  Ingestion aborted."
        )
    # Normalise CRLF → LF
    return text.replace("\r\n", "\n").replace("\r", "\n")
