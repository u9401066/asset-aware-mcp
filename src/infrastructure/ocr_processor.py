"""Infrastructure adapter for optional OCR preprocessing via ocrmypdf."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

LANGUAGE_ALIASES = {
    "en": "eng",
    "fr": "fra",
    "de": "deu",
    "es": "spa",
    "it": "ita",
    "pt": "por",
    "ru": "rus",
    "ja": "jpn",
    "ko": "kor",
    "ar": "ara",
    "zh-cn": "chi_sim",
    "zh-tw": "chi_tra",
}


@dataclass
class OCRProcessResult:
    output_path: Path
    language: str
    rotate_pages: bool
    deskew: bool
    executable: str


class OCRProcessor:
    """Optional OCR preprocessor using the `ocrmypdf` CLI."""

    def __init__(self, executable: str = "ocrmypdf"):
        self.executable = executable

    def is_available(self) -> bool:
        return shutil.which(self.executable) is not None

    def normalize_language(self, language: str) -> str:
        normalized = language.strip().lower()
        return LANGUAGE_ALIASES.get(normalized, normalized)

    def preprocess_pdf(
        self,
        input_path: Path,
        output_path: Path,
        *,
        language: str = "eng",
        rotate_pages: bool = False,
        deskew: bool = False,
    ) -> OCRProcessResult:
        if not self.is_available():
            raise RuntimeError(
                "OCR preprocessing requires `ocrmypdf` to be installed and available on PATH."
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            output_path.unlink()

        normalized_language = self.normalize_language(language)
        command = [
            self.executable,
            "--skip-text",
            "--jobs",
            "4",
            "-l",
            normalized_language,
        ]
        if rotate_pages:
            command.append("--rotate-pages")
        if deskew:
            command.append("--deskew")
        command.extend([str(input_path), str(output_path)])

        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip() if exc.stderr else str(exc)
            raise RuntimeError(f"OCR preprocessing failed: {stderr}") from exc

        return OCRProcessResult(
            output_path=output_path,
            language=normalized_language,
            rotate_pages=rotate_pages,
            deskew=deskew,
            executable=self.executable,
        )
