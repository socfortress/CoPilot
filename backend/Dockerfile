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
# Expose API Port
# ───────────────
EXPOSE 5000

# ───────────────
# Runtime Environment
# ───────────────
ENV SERVER_IP=0.0.0.0 \
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
    DFIR_IRIS_URL=https://1.1.1.1 \
    DFIR_IRIS_API_KEY=dummy \
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
