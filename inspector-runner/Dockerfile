# inspector-runner sidecar.
#
# Small HTTP service that spawns hardened inspector containers via an allowlisting
# Docker socket proxy. Holds NO CoPilot secrets. Never mounts the raw Docker socket
# (it talks to DOCKER_HOST=tcp://docker-socket-proxy:2375).
#
# BUILD FROM THE REPO ROOT (it needs both inspector-runner/ and inspector/):
#   docker build -f inspector-runner/Dockerfile -t ...copilot-inspector-runner .
FROM python:3.11-slim-bookworm

WORKDIR /app
COPY inspector-runner/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY inspector-runner/main.py .

# The inspector source is copied in so INSPECTOR_MODE=service (dev) can import it.
# In production (INSPECTOR_MODE=container) this is unused — the runner spawns the
# separately-built inspector image instead.
COPY inspector /opt/inspector
ENV INSPECTOR_SRC=/opt/inspector

RUN useradd --create-home --uid 10002 runner && chown -R runner:runner /app
USER runner

EXPOSE 9000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
