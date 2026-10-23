"""CoPilot for the browser e2e of #1291 (frontend/e2e/healthcheck-delete.spec.ts) — never deployed.

The real app (``copilot:app``: every router, real JWTs, real MySQL, the real audit writer), with two
things changed in this process only:

- **No connection leaves 127.0.0.1.** The disposable database's connectors name real-looking hosts
  that may resolve on a developer's network; deleting agents would otherwise reach them. Name
  resolution and every socket connect to anything but loopback fail at once.
- **Wazuh and Velociraptor deletions are recorded, not sent**, and ``GET /e2e/upstream-calls`` reads
  the record back for the browser test; ``POST /e2e/reset`` seeds again and empties it, so every run
  of the spec starts from the same state.

From backend/ (the spec seeds through ``POST /e2e/reset``; healthcheck_delete_seed.py does the same by hand):

    MYSQL_URL=127.0.0.1:13306 MYSQL_USER=copilot MYSQL_PASSWORD=e2epass MYSQL_ROOT_PASSWORD=e2eroot \\
    JWT_SECRET=e2e-test-secret-not-the-default MINIO_URL=127.0.0.1:19000 PYTHONPATH=$PWD \\
    .venv/bin/uvicorn tests.e2e.healthcheck_delete_server:app --lifespan off --port 5102

``--lifespan off``: no scheduler, no connector sync, no MinIO bootstrap.
"""

import ipaddress
import os
import socket

for key, value in {
    "MYSQL_URL": "127.0.0.1:13306",
    "MYSQL_USER": "copilot",
    "MYSQL_PASSWORD": "e2epass",
    "MYSQL_ROOT_PASSWORD": "e2eroot",
    "JWT_SECRET": "e2e-test-secret-not-the-default",
    "MINIO_URL": "127.0.0.1:19000",
}.items():
    os.environ.setdefault(key, value)

LOOPBACK_NAMES = {"localhost", "127.0.0.1", "::1"}
_getaddrinfo = socket.getaddrinfo
_connect = socket.socket.connect
_connect_ex = socket.socket.connect_ex


def _is_loopback(host) -> bool:
    if isinstance(host, bytes):
        host = host.decode()
    if host in LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _guarded_getaddrinfo(host, *args, **kwargs):
    if host is not None and not _is_loopback(host):
        raise socket.gaierror(socket.EAI_NONAME, f"e2e: no network beyond 127.0.0.1 ({host})")
    return _getaddrinfo(host, *args, **kwargs)


def _check_address(sock, address):
    if sock.family in (socket.AF_INET, socket.AF_INET6) and not _is_loopback(address[0]):
        raise ConnectionRefusedError(f"e2e: no network beyond 127.0.0.1 ({address[0]})")


def _guarded_connect(self, address):
    _check_address(self, address)
    return _connect(self, address)


def _guarded_connect_ex(self, address):
    _check_address(self, address)
    return _connect_ex(self, address)


socket.getaddrinfo = _guarded_getaddrinfo
socket.socket.connect = _guarded_connect
socket.socket.connect_ex = _guarded_connect_ex

from app.agents.services import deletion  # noqa: E402
from copilot import app  # noqa: E402
from tests.e2e.healthcheck_delete_seed import seed  # noqa: E402

CALLS = {"wazuh": [], "velociraptor": []}


async def _record_wazuh(agent_id):
    CALLS["wazuh"].append(agent_id)


async def _record_velociraptor(client_id):
    CALLS["velociraptor"].append(client_id)


deletion.delete_agent_wazuh = _record_wazuh
deletion.delete_agent_velociraptor = _record_velociraptor


@app.get("/e2e/upstream-calls", include_in_schema=False)
async def upstream_calls():
    """What Wazuh and Velociraptor were asked to delete since the last reset."""
    return CALLS


@app.post("/e2e/reset", include_in_schema=False)
async def reset():
    """The seed's rows again, and an empty record."""
    await seed(dispose=False)
    CALLS["wazuh"].clear()
    CALLS["velociraptor"].clear()
    return {"success": True}
