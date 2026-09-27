# ─────────────────────────────────────────────
# SOCFortress CoPilot Backend – Single-Stage Build
# Optimized with uv (Rust-based pip)
# Compatible with Debian 12 / ARM64 / x86_64
# ─────────────────────────────────────────────

FROM debian:12

# ───────────────
# Core Environment
# ───────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python \
    UV_CACHE_DIR=/root/.cache/uv \
    PATH="/opt/venv/bin:$PATH"

# ───────────────
# System Dependencies
# ───────────────
RUN apt-get update && apt-get install -y \
    curl ca-certificates build-essential \
    python3.11 python3.11-venv python3.11-dev \
    libnss3 libatk-bridge2.0-0 libxkbcommon0 libgtk-3-0 libasound2 libx11-xcb1 \
    wkhtmltopdf libmagic1 file && \
    rm -rf /var/lib/apt/lists/*

# ───────────────
# Virtual Environment + uv
# ───────────────
RUN python3.11 -m venv /opt/venv && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    ln -s /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /opt/copilot/backend

# ───────────────
# Install Dependencies
# ───────────────
COPY requirements.txt ./
RUN uv pip install -r requirements.txt --no-cache

# urllib3-future (via grafana-client → niquests) ships its own `urllib3/`
# package into the same directory as the pinned urllib3 1.26 (elasticsearch7
# needs <2). uv unpacks wheels in parallel, so the two can interleave into a
# broken hybrid (ImportError: create_proxy_ssl_context). Reinstall 1.26 so it
# owns `urllib3/` outright — niquests then uses `urllib3_future` on its own —
# and fail the build if the result is still mixed.
RUN uv pip install --no-cache --reinstall-package urllib3 "urllib3==1.26.20" && \
    python -c "import urllib3, requests, niquests; assert urllib3.__version__ == '1.26.20', urllib3.__version__"

# ───────────────
# Install Playwright Chromium
# ───────────────
RUN /opt/venv/bin/python -m playwright install-deps && \
    /opt/venv/bin/python -m playwright install chromium

# ───────────────
# Copy Application
# ───────────────
COPY . .
COPY wait-for-it.sh /usr/local/bin/wait-for-it.sh
RUN chmod +x /usr/local/bin/wait-for-it.sh && mkdir -p file-store

# ───────────────
# Compile to bytecode (tamper resistance)
# Strips readable .py from app/ so the licensing / customer-onboarding logic
# can't be trivially edited in a running container, then pins the compiled
# enforcement modules in an integrity manifest. copilot.py (entrypoint) and
# alembic/ (migration discovery scans for .py) stay as source. Build with
# --build-arg COMPILE_BYTECODE=false for a debuggable source image.
# ───────────────
ARG COMPILE_BYTECODE=true
RUN if [ "$COMPILE_BYTECODE" = "true" ]; then \
        python -m compileall -b -q app && \
        find app -name '*.py' -type f -delete && \
        find app -type d -name '__pycache__' -exec rm -rf {} + && \
        python -c "from app.middleware.integrity import write_manifest; write_manifest()" && \
        echo "Bytecode compilation complete; .py stripped from app/"; \
    fi

# ───────────────
# Expose API Port
# ───────────────
EXPOSE 5000

# ───────────────
# Runtime Environment
# ───────────────
# Performance session logs (#1072) land in /opt/logs, which docker-compose already
# bind-mounts to ./data/copilot-backend-data/logs on the host — without this they
# would be written inside the container and lost on every recreate. Outside Docker
# the default is backend/logs/performance instead.
ENV PERF_LOG_DIR=/opt/logs/performance \
    SERVER_IP=0.0.0.0 \
    WAZUH_INDEXER_URL=https://1.1.1.1:9200 \
    WAZUH_INDEXER_USERNAME=admin \
    WAZUH_INDEXER_PASSWORD=admin \
    WAZUH_MANAGER_URL=https://1.1.1.1 \
    WAZUH_MANAGER_USERNAME=dummy \
    WAZUH_MANAGER_PASSWORD=dummy \
    GRAYLOG_URL=http://1.1.1.1 \
    GRAYLOG_USERNAME=dummy \
    GRAYLOG_PASSWORD=dummy \
    SHUFFLE_URL=https://1.1.1.1 \
    SHUFFLER_API_KEY=dummy \
    VELOCIRAPTOR_URL=https://1.1.1.1 \
    VELOCIRAPTOR_API_KEY_PATH=dummy \
    SUBLIME_URL=http://1.1.1.1 \
    SUBLIME_API_KEY=dummy \
    INFLUXDB_URL=http://1.1.1.1 \
    INFLUXDB_API_KEY=dummy \
    INFLUXDB_ORG_AND_BUCKET=dummy,dummy \
    ASKSOCFORTRESS_URL=https://knowledge.socfortress.co \
    ASKSOCFORTRESS_API_KEY=dummy \
    SOCFORTRESSTHREATINTEL_URL=https://intel.socfortress.co/search \
    SOCFORTRESSTHREATINTEL_API_KEY=dummy \
    CORTEX_URL=http://1.1.1.1 \
    CORTEX_API_KEY=dummy \
    GRAFANA_URL=http://1.1.1.1 \
    GRAFANA_USERNAME=dummy \
    GRAFANA_PASSWORD=dummy \
    WAZUH_WORKER_PROVISIONING_URL=http://1.1.1.1 \
    EVENT_SHIPPER_URL=graylog_host \
    GELF_INPUT_PORT=gelf_port \
    ALERT_CREATION_PROVISIONING_URL=http://1.1.1.1

# ───────────────
# Optional Build ARG
# ───────────────
ARG COPILOT_API_KEY
ENV COPILOT_API_KEY=$COPILOT_API_KEY

# ───────────────
# Start Application
# ───────────────
CMD ["wait-for-it.sh", "copilot-mysql:3306", "--", "python", "copilot.py"]
