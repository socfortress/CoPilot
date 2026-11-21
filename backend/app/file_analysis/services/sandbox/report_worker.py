"""Summarise one CAPE JSON report, in a process of its own (#1361).

Run by ``report_process`` as ``python -m app.file_analysis.services.sandbox.report_worker``:
the report arrives on stdin, its ``CapeSummary`` leaves on stdout as JSON, and nothing
else is written to stdout. The parsed report (several times the report's size in memory:
about 440 MB for a 59 MB report) lives and dies with this process, so the backend never
holds it and gets all of that memory back when the process exits.

Exit codes, read by ``report_process``: 0 summarised, ``EXIT_NOT_JSON`` the input is not
JSON, ``EXIT_NOT_A_REPORT`` it is JSON but not an object, ``EXIT_SUMMARY_FAILED`` the
summary raised (its traceback goes to stderr).
"""
from __future__ import annotations

import json
import sys
import traceback

from app.file_analysis.services.sandbox.cape import summarize
from app.file_analysis.services.sandbox.report_process import EXIT_NOT_A_REPORT
from app.file_analysis.services.sandbox.report_process import EXIT_NOT_JSON
from app.file_analysis.services.sandbox.report_process import EXIT_SUMMARY_FAILED


def main() -> int:
    raw = sys.stdin.buffer.read()
    try:
        report = json.loads(raw)
    except ValueError:
        sys.stderr.write("the CAPE report is not valid JSON\n")
        return EXIT_NOT_JSON
    del raw
    if not isinstance(report, dict):
        sys.stderr.write(f"the CAPE report is a JSON {type(report).__name__}, not an object\n")
        return EXIT_NOT_A_REPORT
    try:
        summary = summarize(report).to_dict()
    except Exception:  # noqa: BLE001 — reported to the parent by exit code, with the traceback
        traceback.print_exc()
        return EXIT_SUMMARY_FAILED
    del report
    sys.stdout.write(json.dumps(summary))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
