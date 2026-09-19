"""Private LibreOffice profiles and bounded, shell-free conversion processes."""

from __future__ import annotations

import math
import os
import shutil
import signal
import subprocess
import time
from contextlib import suppress
from pathlib import Path

from src.domain.native_assets import MAX_NATIVE_BYTES

PROFILE = """<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry">
<item oor:path="/org.openoffice.Office.Common/Security/Scripting">
<prop oor:name="DisableMacrosExecution" oor:op="fuse"><value>true</value></prop>
<prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop>
</item>
<item oor:path="/org.openoffice.Office.Common/Filter/PDF/Export">
<prop oor:name="ExportHiddenSlides" oor:op="fuse"><value>true</value></prop>
<prop oor:name="ExportNotesPages" oor:op="fuse"><value>false</value></prop>
<prop oor:name="ExportOnlyNotesPages" oor:op="fuse"><value>false</value></prop>
<prop oor:name="ExportNotes" oor:op="fuse"><value>false</value></prop>
<prop oor:name="UseLosslessCompression" oor:op="fuse"><value>true</value></prop>
</item>
</oor:items>
"""


def office_binary() -> str:
    configured = os.environ.get("LIBREOFFICE_BIN")
    if configured:
        binary = shutil.which(configured)
        if not binary:
            raise ValueError("LIBREOFFICE_BIN is not an executable LibreOffice path")
        return binary
    for name in ("libreoffice", "soffice.com", "soffice"):
        if binary := shutil.which(name):
            return binary
    candidates = ["/Applications/LibreOffice.app/Contents/MacOS/soffice"]
    for key in ("ProgramFiles", "ProgramFiles(x86)"):
        if base := os.environ.get(key):
            candidates.append(str(Path(base) / "LibreOffice/program/soffice.com"))
    for candidate in candidates:
        if binary := shutil.which(candidate):
            return binary
    raise ValueError(
        "Slide previews require LibreOffice with Impress; install it and optionally set LIBREOFFICE_BIN"
    )


def prepare_profile(directory: Path) -> str:
    profile = directory / "profile"
    (profile / "user").mkdir(parents=True)
    (profile / "user/registrymodifications.xcu").write_text(PROFILE, encoding="utf-8")
    return f"-env:UserInstallation={profile.as_uri()}"


def _stop(process: subprocess.Popen) -> None:
    if os.name == "posix":
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
    elif process.poll() is None:
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
        if process.poll() is None:
            process.kill()
    process.wait(timeout=5)


def run_office(command: list[str], directory: Path, timeout: float) -> str:
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Presentation rendering exceeded its time limit")
    # Output goes to a private file, never a PIPE that could deadlock or grow RAM.
    # This process boundary is not an OS filesystem/network sandbox.
    with (directory / "office.log").open("w+b") as log:
        environment = {**os.environ, "SAL_USE_VCLPLUGIN": "svp"}
        process = subprocess.Popen(
            command,
            cwd=directory,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            start_new_session=os.name == "posix",
        )
        try:
            deadline = time.monotonic() + timeout
            while True:
                if log.tell() > 64 * 1024:
                    raise ValueError(
                        "LibreOffice diagnostics exceeded the output limit"
                    )
                pdf = directory / "source.pdf"
                if pdf.is_file() and pdf.stat().st_size > MAX_NATIVE_BYTES:
                    raise ValueError("Rendered presentation PDF exceeds the byte limit")
                if process.poll() is not None:
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(command, timeout)
                with suppress(subprocess.TimeoutExpired):
                    process.wait(timeout=min(remaining, 0.1))
            if process.returncode:
                raise ValueError(
                    "LibreOffice exited unsuccessfully during slide rendering"
                )
            log.seek(0)
            return log.read(512).decode("utf-8", errors="replace").strip()
        except subprocess.TimeoutExpired as exc:
            raise ValueError("Presentation rendering exceeded its time limit") from exc
        finally:
            _stop(process)
