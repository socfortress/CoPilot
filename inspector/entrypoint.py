"""Inspector container entrypoint.

Reads a job as JSON on stdin (or a path as argv[1]), runs the type router on the
sample, and writes the result JSON to stdout. This process is the ONLY thing that
runs inside the hardened container; it never executes the sample.

The sample arrives base64-encoded inside the job (``sample_b64``) rather than via
a mounted file, so the container needs NO shared volume — everything comes in on
stdin and leaves on stdout (previews base64-encoded in ``previews_b64``). Scratch
is the container's own tmpfs (``/tmp``); with a read-only root FS that is the only
writable place, and it vanishes when the container is destroyed.

Job shape (see CLAUDE.md -> File Analysis):
    { "sha256": "...", "filename": "invoice.pdf", "customer_code": "HTL01",
      "sample_b64": "<base64 of the file bytes>",
      "context": { "motw": "...", "parent_process": "...", ... } }
"""
from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
from typing import Any
from typing import Dict

import router
from contract import VERDICT_SUSPICIOUS


def _read_job() -> Dict[str, Any]:
    if len(sys.argv) > 1 and sys.argv[1] not in ("-", ""):
        with open(sys.argv[1], "r", encoding="utf-8") as fh:
            return json.load(fh)

    # stdin protocol. Two accepted framings:
    #   1. Length-prefixed: first line is a decimal byte count, then exactly that
    #      many bytes of JSON. Used by inspector-runner because stdin-EOF does NOT
    #      propagate reliably through the Docker socket proxy's tunneled attach.
    #   2. Raw JSON terminated by EOF. Used by native `docker run -i` (verify_isolation)
    #      where closing stdin cleanly signals EOF.
    stdin = sys.stdin.buffer
    first = stdin.readline()
    if not first:
        raise ValueError("empty stdin")
    header = first.strip()
    if header.isdigit():
        want = int(header)
        buf = bytearray()
        while len(buf) < want:
            chunk = stdin.read(want - len(buf))
            if not chunk:
                break
            buf.extend(chunk)
        return json.loads(buf.decode("utf-8"))
    return json.loads(first + stdin.read())


def _collect_previews(results_dir: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not results_dir or not os.path.isdir(results_dir):
        return out
    for name in sorted(os.listdir(results_dir)):
        if name.endswith(".png"):
            with open(os.path.join(results_dir, name), "rb") as fh:
                out[name] = base64.b64encode(fh.read()).decode()
    return out


def main() -> int:
    try:
        job = _read_job()
    except (json.JSONDecodeError, OSError) as exc:
        json.dump({"error": f"invalid job: {exc}", "verdict_hint": VERDICT_SUSPICIOUS, "analysis_incomplete": True}, sys.stdout)
        return 2

    filename = job.get("filename", "sample")
    customer_code = job.get("customer_code", "")
    context = job.get("context") or {}

    # Materialize the sample into the container's tmpfs scratch.
    workdir = tempfile.mkdtemp(prefix="job_", dir="/tmp")
    scratch = os.path.join(workdir, "scratch")
    results = os.path.join(workdir, "results")
    os.makedirs(scratch, exist_ok=True)
    os.makedirs(results, exist_ok=True)
    sample_path = os.path.join(scratch, "sample")

    sample_b64 = job.get("sample_b64")
    if sample_b64:
        with open(sample_path, "wb") as fh:
            fh.write(base64.b64decode(sample_b64))
    elif job.get("sample_path") and os.path.exists(job["sample_path"]):
        sample_path = job["sample_path"]  # fallback: mounted file (dev)
    else:
        json.dump({"error": "no sample provided", "verdict_hint": VERDICT_SUSPICIOUS, "analysis_incomplete": True}, sys.stdout)
        return 2

    try:
        result = router.inspect_path(
            sample_path,
            filename=filename,
            customer_code=customer_code,
            results_dir=results,
            depth=0,
            context=context,
        )
        payload = result.to_dict()
        payload["previews_b64"] = _collect_previews(results)
    except Exception as exc:  # never let the container die without a structured answer
        payload = {
            "sha256": job.get("sha256", ""),
            "filename": filename,
            "customer_code": customer_code,
            "filetype": "unknown",
            "analysis_incomplete": True,
            "flags": ["analysis_incomplete"],
            "verdict_hint": VERDICT_SUSPICIOUS,
            "error": f"inspector exception: {exc}",
            "previews_b64": {},
        }

    json.dump(payload, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
