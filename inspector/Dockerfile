# Tier 1 inspector image — the HARDENED, production per-job container.
#
# Spawned ONE-PER-JOB by inspector-runner with:
#   --network none --read-only --cap-drop ALL --security-opt no-new-privileges
#   --pids-limit N --memory M --cpus C --tmpfs /tmp
# and force-removed after every job. Its safety rests on that isolation, not on
# parser correctness (see CLAUDE.md -> File Analysis). The
# sample arrives base64 on stdin; the result (incl. base64 previews) leaves on
# stdout — no network, no shared volume, nothing executes the sample.
FROM python:3.11-slim-bookworm

# Parser tooling with NO external-binary dependency for the common path:
#   libmagic1  — true-type detection
#   poppler-utils, p7zip-full — pdftoppm fallback + archive extraction
# PDF rendering + structure is PyMuPDF (pip, in requirements.txt) — no poppler
# needed for it. LibreOffice (Office page previews) is intentionally omitted to
# keep the image lean; olevba still extracts macro source without it.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libmagic1 \
        poppler-utils \
        p7zip-full \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY contract.py common.py router.py entrypoint.py ./
COPY analyzers ./analyzers

# Non-root; scratch is the container's own tmpfs at run time (/tmp).
RUN useradd --create-home --uid 10001 inspector && chown -R inspector:inspector /app
USER inspector

# Reads a job on stdin, writes result JSON on stdout.
ENTRYPOINT ["python", "/app/entrypoint.py"]
