"""Archive inspector: ZIP and the TAR family, recursively.

The three limits that matter live here (#974 §E), and they are enforced against
the *declared* member size before anything is decompressed. Checking after the
fact is what makes a decompression bomb work: a 42 KB archive expanding to
petabytes has already exhausted the host by the time you measure the result.

The budget is shared across the whole recursion rather than reset per level --
otherwise depth 3 could expand three times the ceiling.

7z and RAR are identified but not expanded. Both would need a new dependency
(and RAR an external binary) to walk, and neither is common enough in delivery
to justify that in Tier 1. The job records why the view is partial rather than
pretending the archive was empty.
"""

from __future__ import annotations

import io
import re
import tarfile
import zipfile
from typing import List
from typing import Optional
from typing import Set

from loguru import logger

from app.file_analysis.services.inspectors import register
from app.file_analysis.services.inspectors.base import Inspector
from app.file_analysis.services.inspectors.base import InspectorContext
from app.file_analysis.services.inspectors.base import InspectorResult
from app.file_analysis.services.inspectors.base import truncate_evidence
from app.file_analysis.services.limits import AnalysisLimits

SEVEN_ZIP_MAGIC = b"7z\xbc\xaf\x27\x1c"
RAR_MAGIC = b"Rar!\x1a\x07"

EXECUTABLE_EXTENSIONS = (
    ".exe",
    ".dll",
    ".scr",
    ".com",
    ".pif",
    ".bat",
    ".cmd",
    ".vbs",
    ".vbe",
    ".js",
    ".jse",
    ".wsf",
    ".wsh",
    ".hta",
    ".lnk",
    ".msi",
    ".ps1",
    ".jar",
)

# A benign-looking name followed by an executable one. The classic delivery
# trick, and unambiguous enough to carry real weight.
_DOUBLE_EXTENSION = re.compile(
    r"\.(?:pdf|docx?|xlsx?|pptx?|jpe?g|png|gif|txt|csv|rtf|zip)\s*" r"\.(?:exe|scr|com|pif|bat|cmd|vbs|vbe|js|jse|wsf|hta|lnk|msi|ps1)$",
    re.IGNORECASE,
)

ARCHIVE_EXTENSIONS = ("zip", "tar", "gz", "tgz", "bz2", "xz", "7z", "rar", "jar")

PE_MAGIC = b"MZ"
ELF_MAGIC = b"\x7fELF"


class _Budget:
    """Expansion allowance shared by every level of one archive tree.

    Every field is set in ``__init__``. A class-level ``set()`` here would be a
    single object shared by every archive ever inspected in the process, so one
    sample hitting a limit would mark every later one as truncated.
    """

    def __init__(self, limits: AnalysisLimits) -> None:
        self.remaining_bytes = limits.max_expanded_size
        self.remaining_objects = limits.max_extracted_objects
        self.max_depth = limits.max_archive_depth
        self.reasons: List[str] = []
        self.flags: Set[str] = set()

    def note(self, reason: str, flag: str) -> None:
        if reason not in self.reasons:
            self.reasons.append(reason)
        self.flags.add(flag)

    def allow(self, declared_size: int) -> bool:
        """Reserve budget for a member, or refuse it.

        Checked against the *declared* size, before decompressing. Measuring
        afterwards is what lets a decompression bomb through -- the host is
        already gone by the time the result can be weighed.
        """
        if self.remaining_objects <= 0:
            return False
        if declared_size > self.remaining_bytes:
            return False
        self.remaining_objects -= 1
        self.remaining_bytes -= max(declared_size, 0)
        return True


@register
class ArchiveInspector(Inspector):
    name = "archive"
    mime_types = (
        "application/zip",
        "application/x-zip-compressed",
        "application/java-archive",
        "application/gzip",
        "application/x-gzip",
        "application/x-tar",
        "application/x-bzip2",
        "application/x-xz",
        "application/x-7z-compressed",
        "application/x-rar",
        "application/vnd.rar",
    )
    extensions = ARCHIVE_EXTENSIONS
    magic_prefixes = (SEVEN_ZIP_MAGIC, RAR_MAGIC)

    def inspect(self, ctx: InspectorContext) -> InspectorResult:
        budget = _Budget(ctx.limits)
        result = self._expand(ctx.data, ctx, budget, depth=ctx.depth)

        for flag in sorted(budget.flags):
            result.add(flag, "; ".join(budget.reasons))
        if budget.reasons:
            result.truncated_reason = "; ".join(budget.reasons)[:255]
        return result

    # ------------------------------------------------------------------
    def _expand(self, data: bytes, ctx: InspectorContext, budget: _Budget, depth: int) -> InspectorResult:
        result = InspectorResult()

        if data.startswith(SEVEN_ZIP_MAGIC) or data.startswith(RAR_MAGIC):
            fmt = "7z" if data.startswith(SEVEN_ZIP_MAGIC) else "RAR"
            budget.reasons.append(f"{fmt} archives are identified but not expanded in Tier 1")
            return result

        if depth > budget.max_depth:
            budget.note(f"archive recursion stopped at depth {budget.max_depth}", "limit.depth_reached")
            return result

        if zipfile.is_zipfile(io.BytesIO(data)):
            return self._expand_zip(data, ctx, budget, depth)

        try:
            if tarfile.is_tarfile(io.BytesIO(data)):
                return self._expand_tar(data, ctx, budget, depth)
        except (tarfile.TarError, OSError) as exc:
            logger.debug(f"file_analysis: tar probe failed: {exc}")

        return result

    # ------------------------------------------------------------------
    def _expand_zip(self, data: bytes, ctx: InspectorContext, budget: _Budget, depth: int) -> InspectorResult:
        result = InspectorResult()

        try:
            archive = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile as exc:
            logger.warning(f"file_analysis: zip container unreadable: {exc}")
            return result

        for info in archive.infolist():
            if info.is_dir():
                continue

            # Bit 0 of the general purpose flag marks an encrypted entry. The
            # names are still readable, which is why this is a finding and not
            # a dead end.
            if info.flag_bits & 0x1:
                result.add("archive.encrypted", truncate_evidence(info.filename, ctx.limits))

            result.merge(self._inspect_member_name(info.filename, ctx))

            if not budget.allow(info.file_size):
                budget.note(
                    f"stopped expanding at {info.filename}",
                    "limit.size_reached" if budget.remaining_objects > 0 else "limit.object_cap_reached",
                )
                break

            if info.flag_bits & 0x1:
                continue

            try:
                member = archive.read(info)
            except (RuntimeError, zipfile.BadZipFile, OSError) as exc:
                logger.debug(f"file_analysis: zip member {info.filename} unreadable: {exc}")
                continue

            result.merge(self._inspect_member(member, info.filename, ctx, budget, depth))

        return result

    # ------------------------------------------------------------------
    def _expand_tar(self, data: bytes, ctx: InspectorContext, budget: _Budget, depth: int) -> InspectorResult:
        result = InspectorResult()

        try:
            archive = tarfile.open(fileobj=io.BytesIO(data), mode="r:*")
        except tarfile.TarError as exc:
            logger.warning(f"file_analysis: tar container unreadable: {exc}")
            return result

        with archive:
            for info in archive.getmembers():
                if not info.isfile():
                    continue

                result.merge(self._inspect_member_name(info.name, ctx))

                if not budget.allow(info.size):
                    budget.note(
                        f"stopped expanding at {info.name}",
                        "limit.size_reached" if budget.remaining_objects > 0 else "limit.object_cap_reached",
                    )
                    break

                handle = archive.extractfile(info)
                if handle is None:
                    continue
                try:
                    member = handle.read()
                except OSError as exc:
                    logger.debug(f"file_analysis: tar member {info.name} unreadable: {exc}")
                    continue

                result.merge(self._inspect_member(member, info.name, ctx, budget, depth))

        return result

    # ------------------------------------------------------------------
    @staticmethod
    def _inspect_member_name(name: str, ctx: InspectorContext) -> InspectorResult:
        result = InspectorResult()
        lowered = name.lower()

        if _DOUBLE_EXTENSION.search(lowered):
            result.add("archive.double_extension", truncate_evidence(name, ctx.limits))
        if lowered.endswith(EXECUTABLE_EXTENSIONS):
            result.add("archive.executable_content", truncate_evidence(name, ctx.limits))

        return result

    def _inspect_member(
        self,
        member: bytes,
        name: str,
        ctx: InspectorContext,
        budget: _Budget,
        depth: int,
    ) -> InspectorResult:
        result = InspectorResult()

        if member.startswith(PE_MAGIC) or member.startswith(ELF_MAGIC):
            result.add("archive.executable_content", truncate_evidence(f"{name} (by content)", ctx.limits))

        nested = self._nested_inspector(member, name)
        if nested is None:
            return result

        if nested.name == self.name:
            result.add("archive.nested_archive", truncate_evidence(name, ctx.limits))
            result.merge(self._expand(member, ctx, budget, depth + 1))
            return result

        member_ctx = InspectorContext(
            data=member,
            file_name=name,
            # Members are routed by their own content, so the parent's MIME
            # must not leak down and mislabel them.
            mime_type="",
            magic_type="",
            limits=ctx.limits,
            depth=depth + 1,
        )
        try:
            result.merge(nested.inspect(member_ctx))
        except RuntimeError:
            raise
        except Exception as exc:
            logger.warning(f"file_analysis: nested inspection of {name} failed: {exc}")

        return result

    @staticmethod
    def _nested_inspector(member: bytes, name: str) -> Optional[Inspector]:
        # Imported here rather than at module scope: the registry imports this
        # module, so a top-level import would be circular.
        from app.file_analysis.services.inspectors import select_inspector

        return select_inspector(member, "", name)
