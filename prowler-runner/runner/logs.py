"""Reads Prowler's log lines.

With ``--only-logs`` Prowler prints each record with the format
``{"timestamp": "...", "filename": "...", "level": "...", "module": "...", "message": "..."}``.
It looks like JSON but isn't: the message goes in unescaped, so one with a quote or a
newline (Azure's sign-in errors have both) breaks the line apart. Records are therefore
recognised by their prefix, and only the start of each message is read.

Only counts and exception class names are kept. The messages name accounts, roles
and resources, so they are dropped as soon as they are read.
"""

from __future__ import annotations

import re
from collections import Counter

_RECORD = re.compile(
    r'^\{"timestamp": "[^"]*", "filename": "[^"]*", "level": "(?P<level>[A-Z]+)", "module": "[^"]*", "message": "(?P<message>.*)$',
)
# "AWSAssumeRoleError[1012]: AWS assume role ..." or "ClientAuthenticationError[933] -- ..." -> the class name
_EXCEPTION = re.compile(r"^([A-Za-z_][A-Za-z0-9_]{0,99})\[\d+\]")
MAX_DISTINCT = 50
MAX_REPORTED = 10


class LogCollector:
    def __init__(self) -> None:
        self.error_lines = 0
        self.critical_lines = 0
        self._critical: list[str] = []
        self._errors: Counter[str] = Counter()

    def feed(self, line: str) -> None:
        record = _RECORD.match(line)
        if record is None:
            return  # not a record's first line: a continuation of a message, or other output
        level = record.group("level")
        if level not in ("ERROR", "CRITICAL"):
            return
        match = _EXCEPTION.match(record.group("message"))
        name = match.group(1) if match else None
        if level == "CRITICAL":
            self.critical_lines += 1
            if name and name not in self._critical and len(self._critical) < MAX_DISTINCT:
                self._critical.append(name)
        else:
            self.error_lines += 1
            if name and (name in self._errors or len(self._errors) < MAX_DISTINCT):
                self._errors[name] += 1

    @property
    def critical_names(self) -> list[str]:
        return list(self._critical)

    @property
    def error_names(self) -> list[str]:
        return [name for name, _count in self._errors.most_common()]

    def failure_names(self) -> list[str]:
        """What a failed scan reported: the CRITICAL exceptions first, then the commonest ERROR ones."""
        names = list(self._critical)
        for name in self.error_names:
            if name not in names:
                names.append(name)
        return names[:MAX_REPORTED]

    def summary(self) -> dict:
        """What a scan reported along the way: how many checks logged an error, and as what."""
        return {
            "error_lines": self.error_lines,
            "critical_lines": self.critical_lines,
            "error_classes": [{"name": name, "count": count} for name, count in self._errors.most_common(MAX_REPORTED)],
        }
