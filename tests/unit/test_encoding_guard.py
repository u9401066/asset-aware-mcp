"""
Unit tests for src/infrastructure/encoding_guard.py

Covers:
- validate_zip_magic: accept real ZIP, reject non-ZIP bytes, missing file
- strip_bom / strip_bom_bytes: all BOM variants
- safe_decode: UTF-8, UTF-8-BOM, UTF-16-LE/BE, UTF-32, invalid bytes
- sanitize_id_stem: ASCII, CJK, accents, special chars, empty input
- normalize_text_input: BOM stripping, CRLF normalisation, NUL rejection
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from src.infrastructure.encoding_guard import (
    EncodingError,
    normalize_text_input,
    read_text_file,
    safe_decode,
    sanitize_id_stem,
    strip_bom,
    strip_bom_bytes,
    validate_docx_structure,
    validate_zip_magic,
    write_utf8_text,
)

# ============================================================================
# Helpers
# ============================================================================


def _write_zip(path: Path, filename: str = "hello.txt", content: bytes = b"hi") -> None:
    """Write a minimal valid ZIP file."""
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(filename, content)


# ============================================================================
# validate_zip_magic
# ============================================================================


class TestValidateZipMagic:
    def test_valid_zip_passes(self, tmp_path: Path) -> None:
        z = tmp_path / "good.docx"
        _write_zip(z)
        validate_zip_magic(z)  # must not raise

    def test_non_zip_rejected(self, tmp_path: Path) -> None:
        bad = tmp_path / "fake.docx"
        bad.write_bytes(b"\x00\x01\x02\x03 not a zip")
        with pytest.raises(EncodingError, match="bad magic bytes"):
            validate_zip_magic(bad)

    def test_pdf_rejected(self, tmp_path: Path) -> None:
        pdf = tmp_path / "report.docx"
        pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
        with pytest.raises(EncodingError):
            validate_zip_magic(pdf)

    def test_empty_file_rejected(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.docx"
        empty.write_bytes(b"")
        with pytest.raises(EncodingError):
            validate_zip_magic(empty)

    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            validate_zip_magic(tmp_path / "no_such_file.docx")


# ============================================================================
# strip_bom
# ============================================================================


class TestStripBom:
    def test_utf8_bom_stripped(self) -> None:
        assert strip_bom("\ufeffhello") == "hello"

    def test_no_bom_unchanged(self) -> None:
        assert strip_bom("hello") == "hello"

    def test_empty_string_unchanged(self) -> None:
        assert strip_bom("") == ""

    def test_only_bom_becomes_empty(self) -> None:
        assert strip_bom("\ufeff") == ""

    def test_bom_in_middle_not_stripped(self) -> None:
        # BOM in the middle should be preserved (not our problem)
        assert strip_bom("hel\ufefflo") == "hel\ufefflo"


# ============================================================================
# strip_bom_bytes
# ============================================================================


class TestStripBomBytes:
    def test_utf8_bom(self) -> None:
        data, name = strip_bom_bytes(b"\xef\xbb\xbfhello")
        assert data == b"hello"
        assert name == "UTF-8 BOM"

    def test_utf16_le_bom(self) -> None:
        data, name = strip_bom_bytes(b"\xff\xfehello")
        assert data == b"hello"
        assert name == "UTF-16 LE"

    def test_utf16_be_bom(self) -> None:
        data, name = strip_bom_bytes(b"\xfe\xffhello")
        assert data == b"hello"
        assert name == "UTF-16 BE"

    def test_utf32_le_bom(self) -> None:
        data, name = strip_bom_bytes(b"\xff\xfe\x00\x00hello")
        assert data == b"hello"
        assert name == "UTF-32 LE"

    def test_utf32_be_bom(self) -> None:
        data, name = strip_bom_bytes(b"\x00\x00\xfe\xffhello")
        assert data == b"hello"
        assert name == "UTF-32 BE"

    def test_no_bom(self) -> None:
        data, name = strip_bom_bytes(b"hello")
        assert data == b"hello"
        assert name is None


# ============================================================================
# safe_decode
# ============================================================================


class TestSafeDecode:
    def test_plain_utf8(self) -> None:
        assert safe_decode(b"hello world") == "hello world"

    def test_utf8_with_bom(self) -> None:
        result = safe_decode(b"\xef\xbb\xbfhello")
        assert result == "hello"
        assert not result.startswith("\ufeff")

    def test_utf8_multibyte(self) -> None:
        text = "你好世界"
        assert safe_decode(text.encode("utf-8")) == text

    def test_utf16_le_decoded(self) -> None:
        text = "hello"
        data = b"\xff\xfe" + text.encode("utf-16-le")
        assert safe_decode(data) == text

    def test_utf16_be_decoded(self) -> None:
        text = "hello"
        data = b"\xfe\xff" + text.encode("utf-16-be")
        assert safe_decode(data) == text

    def test_utf32_raises(self) -> None:
        text = "hello"
        data = b"\xff\xfe\x00\x00" + text.encode("utf-32-le")
        with pytest.raises(EncodingError, match="UTF-32"):
            safe_decode(data)

    def test_latin1_bytes_rejected(self) -> None:
        # Byte 0xE9 is 'é' in Latin-1 but invalid UTF-8 sequence
        with pytest.raises(EncodingError, match="not valid UTF-8"):
            safe_decode(b"caf\xe9")

    def test_gbk_bytes_rejected(self) -> None:
        # GBK-encoded Chinese text — invalid UTF-8
        gbk_bytes = "報告".encode("gbk")
        with pytest.raises(EncodingError, match="not valid UTF-8"):
            safe_decode(gbk_bytes)

    def test_big5_bytes_rejected(self) -> None:
        big5_bytes = "報告".encode("big5")
        with pytest.raises(EncodingError, match="not valid UTF-8"):
            safe_decode(big5_bytes)

    def test_hint_appears_in_error(self) -> None:
        with pytest.raises(EncodingError, match="my_field"):
            safe_decode(b"\xff\xfe data that is not utf16", hint="my_field")

    def test_empty_bytes(self) -> None:
        assert safe_decode(b"") == ""


# ============================================================================
# sanitize_id_stem
# ============================================================================


class TestSanitizeIdStem:
    def test_simple_ascii(self) -> None:
        assert sanitize_id_stem("hello_world") == "hello_world"

    def test_uppercase_lowercased(self) -> None:
        assert sanitize_id_stem("HelloWorld") == "helloworld"

    def test_spaces_become_underscores(self) -> None:
        assert sanitize_id_stem("Hello World") == "hello_world"

    def test_cjk_characters_dropped(self) -> None:
        # CJK has no ASCII representation via NFKD
        result = sanitize_id_stem("病歷報告_2024")
        assert result == "2024"

    def test_accented_chars_simplified(self) -> None:
        # é → e after NFKD decomposition + ASCII encoding
        result = sanitize_id_stem("résumé")
        assert result == "resume"

    def test_specials_become_underscores(self) -> None:
        result = sanitize_id_stem("report (v2).docx")
        assert result == "report_v2_docx"

    def test_truncated_to_maxlen(self) -> None:
        long = "a" * 100
        assert len(sanitize_id_stem(long)) <= 30

    def test_custom_maxlen(self) -> None:
        result = sanitize_id_stem("hello_world", maxlen=5)
        assert len(result) <= 5

    def test_empty_string_fallback(self) -> None:
        assert sanitize_id_stem("") == "doc"

    def test_all_special_chars_fallback(self) -> None:
        # All CJK → empty after ASCII drop → fallback
        assert sanitize_id_stem("病歷報告") == "doc"

    def test_leading_trailing_underscores_stripped(self) -> None:
        result = sanitize_id_stem("_hello_")
        assert not result.startswith("_")
        assert not result.endswith("_")

    def test_consecutive_underscores_collapsed(self) -> None:
        result = sanitize_id_stem("hello   world")
        assert "__" not in result


# ============================================================================
# normalize_text_input
# ============================================================================


class TestNormalizeTextInput:
    def test_bom_stripped(self) -> None:
        result = normalize_text_input("\ufeffhello")
        assert result == "hello"

    def test_crlf_normalized_to_lf(self) -> None:
        result = normalize_text_input("line1\r\nline2\r\nline3")
        assert result == "line1\nline2\nline3"

    def test_cr_only_normalized_to_lf(self) -> None:
        result = normalize_text_input("line1\rline2")
        assert result == "line1\nline2"

    def test_nul_byte_rejected(self) -> None:
        with pytest.raises(EncodingError, match="NUL bytes"):
            normalize_text_input("hello\x00world")

    def test_clean_text_unchanged(self) -> None:
        text = "# Heading\n\nSome paragraph.\n"
        assert normalize_text_input(text) == text

    def test_hint_in_nul_error(self) -> None:
        with pytest.raises(EncodingError, match=r"my_file\.dfm"):
            normalize_text_input("bad\x00data", hint="my_file.dfm")



class TestReadWriteUtf8Text:
    def test_read_text_file_strips_utf8_bom(self, tmp_path: Path) -> None:
        p = tmp_path / "bom.md"
        p.write_bytes(b"\xef\xbb\xbfhello")
        assert read_text_file(p) == "hello"

    def test_write_utf8_text_normalizes_newlines(self, tmp_path: Path) -> None:
        p = tmp_path / "out.md"
        write_utf8_text(p, "a\r\nb\r")
        assert p.read_text(encoding="utf-8") == "a\nb\n"

    def test_write_utf8_text_rejects_nul(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.md"
        with pytest.raises(EncodingError):
            write_utf8_text(p, "abc\x00def")


class TestValidateDocxStructure:
    def test_valid_docx_structure_passes(self, tmp_path: Path) -> None:
        z = tmp_path / "good.docx"
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("[Content_Types].xml", b"ok")
            zf.writestr("_rels/.rels", b"ok")
            zf.writestr("word/document.xml", b"<w:document/>")
        validate_docx_structure(z)

    def test_missing_required_members_rejected(self, tmp_path: Path) -> None:
        z = tmp_path / "bad.docx"
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("[Content_Types].xml", b"ok")
        with pytest.raises(EncodingError, match="missing required DOCX members"):
            validate_docx_structure(z)
