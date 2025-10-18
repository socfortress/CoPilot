# FROM debian:12

# # Set environment variables
# ENV PYTHONDONTWRITEBYTECODE 1
# ENV PYTHONUNBUFFERED 1
# # Set environment variable to use pure-Python implementation
# ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

# # Update the package lists
# RUN apt-get update

# # Install necessary dependencies
# RUN apt-get install -y \
#     apt-transport-https \
#     ca-certificates \
#     curl \
#     gnupg \
#     lsb-release

# # Add the deadsnakes PPA
# #RUN echo "deb http://ppa.launchpad.net/deadsnakes/ppa/ubuntu focal main" | tee /etc/apt/sources.list.d/focal.list
# #RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys F23C5A6CF475977595C89F51BA6932366A755776

# # Update the package lists
# RUN apt-get update

# # Install Python 3.11, pip and venv
# RUN apt-get install -y python3.11 python3-pip python3.11-venv python3.11-dev

# # Create a Python virtual environment and activate it
# RUN python3.11 -m venv /opt/venv
# ENV PATH="/opt/venv/bin:$PATH"

# # Install setuptools
# RUN /opt/venv/bin/pip install setuptools

# # Install your application's dependencies
# WORKDIR /opt/copilot/backend
# COPY requirements.txt ./
# RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# # Install required browsers for playwright
# RUN playwright install-deps
# RUN playwright install

# # Install wkhtmltopdf
# RUN apt-get install -y wkhtmltopdf

# # Copy your application into the Docker image
# WORKDIR /opt/copilot/backend
# COPY . .
# COPY wait-for-it.sh /usr/wait-for-it.sh
# RUN chmod +x /usr/wait-for-it.sh
# # Create file-store folder
# RUN mkdir file-store

# # Expose ports
# EXPOSE 5000

# ENV SERVER_IP=0.0.0.0

# # Connector Credentials
# # ! SETTING UP YOUR CONNECTORS DEMOs https://www.youtube.com/@taylorwalton_socfortress/videos! #
# ENV WAZUH_INDEXER_URL=https://1.1.1.1:9200
# ENV WAZUH_INDEXER_USERNAME=admin
# ENV WAZUH_INDEXER_PASSWORD=admin

# ENV WAZUH_MANAGER_URL=https://1.1.1.1
# ENV WAZUH_MANAGER_USERNAME=dummy
# ENV WAZUH_MANAGER_PASSWORD=dummy

# ENV GRAYLOG_URL=http://1.1.1.1
# ENV GRAYLOG_USERNAME=dummy
# ENV GRAYLOG_PASSWORD=dummy

# ENV SHUFFLE_URL=https://1.1.1.1
# ENV SHUFFLER_API_KEY=dummy

# ENV DFIR_IRIS_URL=https://1.1.1.1
# ENV DFIR_IRIS_API_KEY=dummy

# ENV VELOCIRAPTOR_URL=https://1.1.1.1
# ENV VELOCIRAPTOR_API_KEY_PATH=dummy

# ENV SUBLIME_URL=http://1.1.1.1
# ENV SUBLIME_API_KEY=dummy

# ENV INFLUXDB_URL=http://1.1.1.1
# ENV INFLUXDB_API_KEY=dummy
# ENV INFLUXDB_ORG_AND_BUCKET=dummy,dummy

# ENV ASKSOCFORTRESS_URL=https://knowledge.socfortress.co
# ENV ASKSOCFORTRESS_API_KEY=dummy

# ENV SOCFORTRESSTHREATINTEL_URL=https://intel.socfortress.co/search
# ENV SOCFORTRESSTHREATINTEL_API_KEY=dummy

# ENV CORTEX_URL=http://1.1.1.1
# ENV CORTEX_API_KEY=dummy

# ENV GRAFANA_URL=http://1.1.1.1
# ENV GRAFANA_USERNAME=dummy
# ENV GRAFANA_PASSWORD=dummy

# ENV WAZUH_WORKER_PROVISIONING_URL=http://1.1.1.1

# ENV EVENT_SHIPPER_URL=graylog_host
# ENV GELF_INPUT_PORT=gelf_port

# ENV ALERT_CREATION_PROVISIONING_URL=http://1.1.1.1

# ARG COPILOT_API_KEY
# ENV COPILOT_API_KEY=$COPILOT_API_KEY

# # Run your application
# # CMD ["sh", "-c", "ls -la && /opt/venv/bin/python copilot.py"]
# # Use wait-for-it.sh to wait for the MySQL service to be ready before starting your application
# CMD ["/usr/wait-for-it.sh", "copilot-mysql:3306", "--", "/opt/venv/bin/python", "copilot.py"]

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
