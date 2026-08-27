"""Pure-static deobfuscation tests. No external tools, no network."""
from __future__ import annotations

from analyzers.script import analyze
from analyzers.script import deobfuscate
from contract import FLAG_DEOBFUSCATION_INCOMPLETE
from contract import FLAG_ENCODED_POWERSHELL
from contract import InspectorResult


def test_enc_layer_is_unwound(layered_powershell):
    layers, saw_encoded, incomplete = deobfuscate(layered_powershell)
    assert saw_encoded is True
    assert layers, "expected at least one decoded layer"
    assert "evil.example.com" in layers[-1]
    # The decoded body still contains a live IEX/DownloadString -> incomplete.
    assert incomplete is True


def test_concat_is_flattened(concat_powershell):
    layers, _, _ = deobfuscate(concat_powershell)
    assert layers
    assert "evil.example.com" in layers[-1]


def test_no_obfuscation_yields_no_layers():
    layers, saw_encoded, incomplete = deobfuscate("Write-Host 'hello world'")
    assert layers == []
    assert saw_encoded is False
    assert incomplete is False


def test_analyze_sets_flags_and_iocs(tmp_sample, layered_powershell):
    path = tmp_sample("a.ps1", layered_powershell)
    result = InspectorResult(sha256="x", filename="a.ps1", customer_code="HTL01")
    analyze(path, result)
    assert result.filetype == "script"
    assert FLAG_ENCODED_POWERSHELL in result.flags
    assert FLAG_DEOBFUSCATION_INCOMPLETE in result.flags
    assert "evil.example.com" in result.iocs["domains"]
    assert "deobfuscated" in result.content


def test_bounded_rounds_terminate():
    # Deeply nested concatenation must not loop forever.
    payload = "+".join(["'a'"] * 200)
    layers, _, _ = deobfuscate(payload)
    assert isinstance(layers, list)  # returned, did not hang
