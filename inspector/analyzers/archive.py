"""Archive / ISO / IMG analyzer — list members and recurse each one.

This is where the real payload usually hides (ISO/LNK smuggling, zip-of-zips).
Recursion is bounded by depth and a total-member cap (zip-bomb / billion-laughs
defense). Encrypted archives get the conventional phishing passwords tried
(``infected`` / ``malware`` / ``password``) before giving up.
"""
from __future__ import annotations

import os
import tempfile
from typing import List

from contract import FLAG_ENCRYPTED_ARCHIVE
from contract import FLAG_ENCRYPTED_ARCHIVE_OPENED
from contract import FLAG_SUSPICIOUS_ATTACHMENT
from contract import InspectorResult

_MAX_DEPTH = 3
_MAX_MEMBERS = 500
_COMMON_PASSWORDS = ("infected", "malware", "password", "123456")


def analyze(sample_path: str, result: InspectorResult, results_dir: str = "", depth: int = 0) -> None:
    result.filetype = "archive"
    try:
        import py7zr  # noqa: F401  (probe only)
    except ImportError:
        py7zr = None  # type: ignore
    members = _list_and_extract(sample_path, result, depth)
    result.content["members"] = members


def _list_and_extract(sample_path: str, result: InspectorResult, depth: int) -> List[dict]:
    import zipfile

    members: List[dict] = []
    if not zipfile.is_zipfile(sample_path):
        # Non-zip container (rar/7z/iso) — best-effort listing only in pure dev;
        # full support lands with the image's 7z binary.
        result.content["note"] = "non-zip container; member extraction requires 7z in the image"
        return members

    try:
        zf = zipfile.ZipFile(sample_path)
    except zipfile.BadZipFile:
        result.mark_incomplete()
        return members

    encrypted = any(info.flag_bits & 0x1 for info in zf.infolist())
    password = None
    if encrypted:
        result.add_flag(FLAG_ENCRYPTED_ARCHIVE)
        password = _guess_password(zf)
        if password is not None:
            result.add_flag(FLAG_ENCRYPTED_ARCHIVE_OPENED)

    count = 0
    for info in zf.infolist():
        if count >= _MAX_MEMBERS:
            result.content["truncated"] = True
            break
        if info.is_dir():
            continue
        count += 1
        entry = {"name": info.filename, "size": info.file_size, "compressed": info.compress_size}
        if depth < _MAX_DEPTH and info.file_size and info.file_size < 50 * 1024 * 1024:
            child = _recurse_member(zf, info, result, depth, password)
            if child:
                entry["analysis"] = child
                if child.get("verdict_hint") in ("suspicious", "malicious"):
                    result.add_flag(FLAG_SUSPICIOUS_ATTACHMENT)
        members.append(entry)
    zf.close()
    return members


def _guess_password(zf) -> "bytes | None":
    import zipfile

    first = next((i for i in zf.infolist() if not i.is_dir()), None)
    if first is None:
        return None
    for candidate in _COMMON_PASSWORDS:
        try:
            with zf.open(first, pwd=candidate.encode()) as fh:
                fh.read(16)
            return candidate.encode()
        except (RuntimeError, zipfile.BadZipFile, Exception):
            continue
    return None


def _recurse_member(zf, info, result: InspectorResult, depth: int, password) -> dict:
    import router  # lazy import to avoid a cycle

    tmp = None
    try:
        with zf.open(info, pwd=password) as src:
            data = src.read(50 * 1024 * 1024)
        fd, tmp = tempfile.mkstemp(prefix="member_")
        with os.fdopen(fd, "wb") as dst:
            dst.write(data)
        child = router.inspect_path(
            tmp,
            filename=os.path.basename(info.filename),
            customer_code=result.customer_code,
            results_dir="",
            depth=depth + 1,
        )
        return {
            "filetype": child.filetype,
            "flags": child.flags,
            "verdict_hint": child.verdict_hint,
            "iocs": child.iocs,
        }
    except Exception:
        return {}
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
