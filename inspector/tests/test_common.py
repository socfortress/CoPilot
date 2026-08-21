"""Common-layer tests: hashes, entropy, extension mismatch, IOC extraction."""
from __future__ import annotations

import hashlib

from common import compute_hashes
from common import extension_mismatch
from common import extract_iocs
from common import shannon_entropy


def test_hashes_match_hashlib(tmp_sample):
    path = tmp_sample("f.bin", b"hello world")
    hashes = compute_hashes(path)
    assert hashes["sha256"] == hashlib.sha256(b"hello world").hexdigest()
    assert hashes["md5"] == hashlib.md5(b"hello world").hexdigest()


def test_entropy_bounds(tmp_sample):
    zeros = tmp_sample("z.bin", b"\x00" * 4096)
    assert shannon_entropy(zeros) == 0.0
    import os

    rnd = tmp_sample("r.bin", os.urandom(65536))
    assert shannon_entropy(rnd) > 7.5


def test_extension_mismatch_detects_masquerade():
    assert extension_mismatch("report.docx", "pdf") is True
    assert extension_mismatch("report.pdf", "pdf") is False
    assert extension_mismatch("unknown.xyz", "pdf") is False


def test_ioc_extraction_and_refang():
    text = "reach hxxp://evil[.]com/a and 10.0.0.5 plus bad-domain.top"
    iocs = extract_iocs(text)
    assert any("evil.com" in u for u in iocs["urls"])
    assert "10.0.0.5" in iocs["ips"]
    assert "bad-domain.top" in iocs["domains"]


def test_ioc_dedup():
    iocs = extract_iocs("http://a.com/x http://a.com/x")
    assert len(iocs["urls"]) == 1
