"""``python -m runner.normalize_cli JOB_DIR PROVIDER``

Reads the job's OCSF output (``JOB_DIR/out/scan.ocsf.json``) and writes
``summary.json`` and ``findings.ndjson`` into JOB_DIR. It runs as a process of its
own, so a report of hundreds of megabytes is parsed here and never in the API's
event loop. It only ever reads and writes inside a job directory.

Exit codes: 0 written; 3 the output could not be read; 2 wrong arguments.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from runner import PROVIDERS
from runner.layout import FINDINGS_FILE
from runner.layout import JOB_ID
from runner.layout import OCSF_FILE
from runner.layout import OUT_DIR
from runner.layout import SUMMARY_FILE
from runner.ocsf import OcsfError
from runner.ocsf import normalize_stream


def _write_private(path: Path):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    return os.fdopen(descriptor, "w", encoding="utf-8", newline="\n")


class _Empty:
    def read(self, _size: int = -1) -> str:
        return ""


def normalize(job_dir: Path, provider: str) -> dict:
    ocsf_path = job_dir / OUT_DIR / OCSF_FILE
    findings_tmp = job_dir / (FINDINGS_FILE + ".tmp")
    summary_tmp = job_dir / (SUMMARY_FILE + ".tmp")
    with _write_private(findings_tmp) as findings:

        def write_finding(finding: dict) -> None:
            # ASCII only: no raw U+2028/U+2029, which some line splitters treat as newlines.
            findings.write(json.dumps(finding, ensure_ascii=True, separators=(",", ":")))
            findings.write("\n")

        if ocsf_path.exists():
            with open(ocsf_path, encoding="utf-8") as stream:
                summary = normalize_stream(stream, write_finding, provider)
        else:
            # Prowler writes no file for a scan without findings.
            summary = normalize_stream(_Empty(), write_finding, provider)
    with _write_private(summary_tmp) as handle:
        json.dump(summary, handle, ensure_ascii=True, separators=(",", ":"))
    findings_tmp.replace(job_dir / FINDINGS_FILE)
    summary_tmp.replace(job_dir / SUMMARY_FILE)
    return summary


def job_directory(value: str) -> Path | None:
    """`value` if it is an absolute path to an existing job directory, else None."""
    path = Path(os.path.realpath(value))
    if not os.path.isabs(value) or not JOB_ID.match(path.name) or not path.is_dir():
        return None
    return path


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    job_dir = job_directory(args[0]) if len(args) == 2 else None
    if job_dir is None or args[1] not in PROVIDERS:
        sys.stderr.write("usage: python -m runner.normalize_cli JOB_DIR PROVIDER\n")
        return 2
    try:
        normalize(job_dir, args[1])
    except (OcsfError, UnicodeDecodeError):
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
