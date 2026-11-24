# CoPilot's Prowler runner (#1328): Prowler's official CLI image plus a small job API.
#
# Build from this directory:
#   docker build -t ghcr.io/socfortress/copilot-prowler:latest prowler-runner
#
# The base image already carries Prowler, PowerShell 7 with the Microsoft 365 modules,
# and Trivy, and runs as the non-root user 1000. Upgrading Prowler means changing
# PROWLER_IMAGE (tag and digest), then the checks in README.md ("Upgrading Prowler").
ARG PROWLER_IMAGE=toniblyx/prowler:5.52.0@sha256:1d3e989a48ef5d7b41def7c17a1828dc4d9d7b6302e479ce854e473fc0ed8d7f
FROM ${PROWLER_IMAGE}

USER 0

# The API gets a virtualenv of its own, built with the image's Python. Prowler's
# (/home/prowler/.venv) stays exactly as the base image ships it.
COPY requirements.txt /opt/prowler-runner/requirements.txt
RUN python3 -m venv /opt/prowler-runner/venv \
    && /opt/prowler-runner/venv/bin/pip install --no-cache-dir -r /opt/prowler-runner/requirements.txt \
    && /opt/prowler-runner/venv/bin/pip uninstall -y pip \
    && mkdir -p /work \
    && chown 1000:1000 /work \
    && chmod 0700 /work

COPY runner /opt/prowler-runner/runner

# Fail the build, not the first scan, if either interpreter or Prowler is missing.
RUN cd /opt/prowler-runner && /opt/prowler-runner/venv/bin/python -c "import fastapi, uvicorn, runner.main" \
    && /home/prowler/.venv/bin/python -c "import prowler, importlib.metadata as m; print('Prowler', m.version('prowler'))" \
    && test -x /home/prowler/.venv/bin/prowler \
    && test -d /home/prowler/prowler/compliance/aws

USER 1000
WORKDIR /opt/prowler-runner
ENV PROWLER_COMPLIANCE_DIR=/home/prowler/prowler/compliance \
    PROWLER_WORK_DIR=/work \
    PROWLER_SCAN_HOME=/home/prowler \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["/opt/prowler-runner/venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=3)"]

# One worker on purpose: scans are tracked in this process's memory.
ENTRYPOINT []
CMD ["/opt/prowler-runner/venv/bin/uvicorn", "--factory", "runner.main:create_app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--no-server-header"]
