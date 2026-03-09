from pathlib import Path

from src.application.docx_service import DocxService


def test_find_libreoffice_binary_prefers_env_var(monkeypatch):
    monkeypatch.setenv("LIBREOFFICE_BIN", "/custom/LibreOffice")
    monkeypatch.setattr(Path, "exists", lambda self: str(self) == "/custom/LibreOffice")
    monkeypatch.setattr("src.application.docx_service.shutil.which", lambda _name: None)

    assert DocxService._find_libreoffice_binary() == "/custom/LibreOffice"


def test_find_libreoffice_binary_uses_soffice_on_macos(monkeypatch):
    monkeypatch.delenv("LIBREOFFICE_BIN", raising=False)

    def fake_which(name: str):
        if name == "soffice":
            return "/Applications/LibreOffice.app/Contents/MacOS/soffice"
        return None

    monkeypatch.setattr("src.application.docx_service.shutil.which", fake_which)

    assert (
        DocxService._find_libreoffice_binary()
        == "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    )
