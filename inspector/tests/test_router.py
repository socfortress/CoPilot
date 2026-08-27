"""Router tests: type detection, extension mismatch, recursion, graceful degrade.

These exercise only the offline path (magic bytes + pure-python analyzers); the
tool-backed analyzers (pdfid/libreoffice/oletools) are covered in the image test
job (WI-1) where those binaries exist.
"""
from __future__ import annotations

import router
from contract import FLAG_HTML_SMUGGLING


def test_pdf_detected_by_magic_bytes_despite_docx_name(pdf_renamed_docx):
    result = router.inspect_path(pdf_renamed_docx, filename="report.docx", customer_code="HTL01")
    assert result.filetype == "pdf"
    assert result.extension_mismatch is True


def test_corrupt_ole_degrades_without_crashing(corrupt_ole):
    result = router.inspect_path(corrupt_ole, filename="broken.doc", customer_code="HTL01")
    # office analyzer without oletools installed -> incomplete, never an exception.
    assert result.filetype in ("office", "unknown")
    assert result.analysis_incomplete is True


def test_zip_recursion_is_bounded(zip_of_zips):
    result = router.inspect_path(zip_of_zips, filename="outer.zip", customer_code="HTL01")
    assert result.filetype == "archive"
    members = result.content.get("members", [])
    assert any(m["name"] == "inner.zip" for m in members)


def test_html_smuggling_flagged(html_smuggling):
    result = router.inspect_path(html_smuggling, filename="invoice.html", customer_code="HTL01")
    assert result.filetype == "html"
    assert FLAG_HTML_SMUGGLING in result.flags


def test_result_always_has_sha256_and_customer(pdf_renamed_docx):
    result = router.inspect_path(pdf_renamed_docx, filename="report.docx", customer_code="HTL01")
    assert result.sha256 and len(result.sha256) == 64
    assert result.customer_code == "HTL01"
    assert result.verdict_hint in ("clean", "suspicious", "malicious")
