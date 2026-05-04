from __future__ import annotations

from src.infrastructure.ocr_processor import OCRProcessor


def test_normalize_language_strips_and_aliases() -> None:
    processor = OCRProcessor()

    assert processor.normalize_language(" zh-TW ") == "chi_tra"
    assert processor.normalize_language(" ENG ") == "eng"
