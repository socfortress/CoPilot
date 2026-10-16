"""E2E for #1261 (WAF Overview times out on a busy WAF) — NOT collected by pytest; run by hand.

The whole request path a browser takes, with nothing mocked but the WAF:

    client → nginx (the frontend image's own site template, nginx 1.30.3 as in its Dockerfile)
           → backend (real WAF routers, real JWT, real MySQL on 13306, served by uvicorn)
           → a fake WAF that answers /logs/stats and /logs/ after a chosen delay

Needs Docker and the disposable MySQL of customer_waf_e2e.py:

    docker run -d --name copilot-e2e-mysql -p 13306:3306 \\
        -e MYSQL_ROOT_PASSWORD=e2eroot -e MYSQL_DATABASE=copilot \\
        -e MYSQL_USER=copilot -e MYSQL_PASSWORD=e2epass mysql:8.0
    cd backend && export PYTHONPATH=$PWD
    .venv/bin/python -c "from app.db.db_setup import apply_migrations; apply_migrations()"
    .venv/bin/python tests/e2e/customer_waf_slow_stats_e2e.py        # about 2.5 minutes

``E2E_NGINX_CONF=<path>`` runs it against another site template, e.g. the one before
#1261 (``git show <rev>:frontend/build/etc/nginx/sites-enabled/default.conf``): nginx then
answers 504 after its default 60s, before the WAF does. The only change made to the
template is the upstream port (``copilot-backend:5000`` → this script's backend on the host).

What it proves that the unit tests can't: a WAF answering /logs/stats in 70s reaches the
browser (the old path failed it at 15s in the backend, and at 60s in nginx); a WAF slower
than STATS_TIMEOUT is a 502 ``timeout`` from the backend, not nginx's 504; every other
read still gives up at 15s; a WAF that is down reads as unreachable in seconds even on
the stats route. Exits non-zero on any failure.

Against the tree before #1261 (backend and nginx), 7 of its 14 checks fail: the busy WAF's
stats is a 502 "did not respond within 15s" with reason ``unreachable`` — the bug as
reported, which the UI explains as "CoPilot can't reach the WAF".
"""
import asyncio
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

import httpx  # noqa: E402
import uvicorn  # noqa: E402
from cryptography.fernet import Fernet  # noqa: E402
from fastapi import APIRouter  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from sqlalchemy import delete  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from starlette.requests import Request  # noqa: E402
from starlette.responses import JSONResponse  # noqa: E402

from app.auth.models.users import Role  # noqa: E402
from app.auth.models.users import User  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.customer_waf.services import crypto  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.db.universal_models import CustomerWafInstance  # noqa: E402

assert "13306" in os.environ["MYSQL_URL"], "refusing to run against anything but the disposable e2e MySQL"

CUSTOMER = "E2E_WAF_SLOW"
ADMIN = "e2e_waf_slow_admin"
TOKEN = "wafst_" + "S" * 43
NGINX_IMAGE = "nginx:1.30.3-alpine"  # frontend/Dockerfile's runtime image
REPO = Path(__file__).resolve().parents[3]
NGINX_CONF = Path(os.environ.get("E2E_NGINX_CONF") or REPO / "frontend/build/etc/nginx/sites-enabled/default.conf")
UNROUTABLE = "192.0.2.1"  # RFC 5737 TEST-NET-1: never routed, so a connection attempt just hangs

STATS = {"total_1h": 4821, "blocked_1h": 312, "detected_1h": 57, "block_rate": 0.0647}

# The contract under test, stated here rather than imported, so the script also runs
# against the tree before #1261 and shows what was broken there.
STATS_TIMEOUT = 120.0  # how long the backend waits for /logs/stats
DEFAULT_TIMEOUT = 15.0  # every other WAF read
CONNECT_TIMEOUT = 15.0  # opening the connection, whatever the call allows for the answer

results = []


def check(name, passed, detail=""):
    results.append((name, passed))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ── the fake WAF: /d/<seconds>/api/v1/… answers the log reads after <seconds> ──


def build_fake_waf() -> FastAPI:
    waf = FastAPI()

    @waf.get("/d/{delay}/api/v1/{rest:path}")
    async def answer(delay: float, rest: str, request: Request):
        if rest == "users/me":
            return {"email": "copilot@e2e", "roles": [{"id": "r", "name": "viewer"}]}
        if rest in ("logs/stats", "logs/"):
            deadline = time.monotonic() + delay
            while time.monotonic() < deadline:
                if await request.is_disconnected():  # CoPilot gave up: stop, as a real server would
                    return JSONResponse({"detail": "client went away"}, status_code=499)
                await asyncio.sleep(0.25)
            return STATS if rest == "logs/stats" else []
        return JSONResponse({"detail": "Not Found"}, status_code=404)

    return waf


def build_backend() -> FastAPI:
    from app.customer_waf.routes.customer_waf import customer_waf_router

    api = APIRouter(prefix="/api")
    api.include_router(customer_waf_router, prefix="/customer_waf")
    app = FastAPI()
    app.include_router(api)
    return app


async def serve(app: FastAPI, port: int):
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", lifespan="off", timeout_graceful_shutdown=5),
    )
    task = asyncio.create_task(server.serve())
    for _ in range(100):
        if server.started:
            return server, task
        await asyncio.sleep(0.05)
    raise RuntimeError(f"server on {port} did not start")


# ── nginx, as the frontend image runs it ──


def host_gateway_ipv4() -> str:
    """The host's IPv4 address as containers see it.

    ``--add-host x:host-gateway`` gives Docker Desktop's IPv6 gateway as well; nginx then
    tries both, and a timeout on the IPv4 one reads 502 ("no live upstreams") instead of
    the 504 a compose network, where the backend has one address, gives.
    """
    out = subprocess.run(
        ["docker", "run", "--rm", "--add-host", "gw:host-gateway", "--entrypoint", "getent", NGINX_IMAGE, "ahostsv4", "gw"],
        check=True,
        capture_output=True,
        text=True,
    )
    return out.stdout.split()[0]


def start_nginx(workdir: Path, backend_port: int, https_port: int) -> str:
    template = NGINX_CONF.read_text()
    assert "copilot-backend:5000" in template, f"{NGINX_CONF} does not proxy to copilot-backend:5000"
    (workdir / "default.conf.template").write_text(template.replace("copilot-backend:5000", f"copilot-backend:{backend_port}"))
    certs, dh = workdir / "certs.d", workdir / "certs"
    certs.mkdir()
    dh.mkdir()
    subprocess.run(
        ["openssl", "req", "-x509", "-subj", "/CN=localhost", "-nodes", "-newkey", "rsa:2048", "-days", "1"]
        + ["-keyout", str(certs / "server.key"), "-out", str(certs / "server.crt")],
        check=True,
        capture_output=True,
    )
    subprocess.run(["openssl", "dhparam", "-dsaparam", "-out", str(dh / "dhparams.pem"), "2048"], check=True, capture_output=True)
    run = subprocess.run(
        # copilot-backend → the host running this script: one address, as on the compose network.
        ["docker", "run", "-d", "--rm", "--add-host", f"copilot-backend:{host_gateway_ipv4()}", "-p", f"127.0.0.1:{https_port}:443"]
        + ["-e", "TLS_CERT_PATH=/etc/nginx/certs.d/server.crt", "-e", "TLS_KEY_PATH=/etc/nginx/certs.d/server.key"]
        + ["-v", f"{workdir / 'default.conf.template'}:/etc/nginx/templates/default.conf.template:ro"]
        + ["-v", f"{certs}:/etc/nginx/certs.d:ro", "-v", f"{dh}:/etc/nginx/certs:ro", NGINX_IMAGE],
        check=True,
        capture_output=True,
        text=True,
    )
    return run.stdout.strip()


async def wait_for_nginx(base: str, container: str):
    async with httpx.AsyncClient(verify=False, timeout=2) as c:
        for _ in range(60):
            try:
                await c.get(f"{base}/api/customer_waf/none/0/stats")
                return
            except httpx.HTTPError:
                await asyncio.sleep(0.5)
    logs = subprocess.run(["docker", "logs", container], capture_output=True, text=True)
    raise RuntimeError(f"nginx did not come up:\n{logs.stdout}{logs.stderr}")


# ── seed ──


async def cleanup(s: AsyncSession):
    await s.execute(delete(CustomerWafInstance).where(CustomerWafInstance.customer_code == CUSTOMER))
    await s.execute(delete(User).where(User.username == ADMIN))
    await s.commit()
    await s.execute(delete(Customers).where(Customers.customer_code == CUSTOMER))
    await s.commit()


async def seed():
    async with AsyncSession(async_engine) as s:
        if not (await s.execute(select(Role).where(Role.id == 1))).scalars().first():
            s.add(Role(id=1, name="admin", description="admin"))
            await s.commit()
        await cleanup(s)
        s.add(
            Customers(
                customer_code=CUSTOMER,
                customer_name=f"{CUSTOMER} name",
                contact_first_name="E2E",
                contact_last_name="Tester",
                phone="000",
                address_line1="a",
                address_line2="b",
                city="c",
                state="d",
                postal_code="1",
                country="IT",
                customer_type="MSSP",
                logo_file="",
            ),
        )
        s.add(User(username=ADMIN, password=AuthHandler().get_password_hash("E2ePassw0rd!x"), email=f"{ADMIN}@e2e.example", role_id=1))
        await s.commit()


async def timed(coro):
    start = time.monotonic()
    response = await coro
    return response, time.monotonic() - start


def reason_of(r: httpx.Response):
    try:
        return r.json().get("reason")
    except ValueError:
        return None


async def main() -> int:
    os.environ[crypto.KEY_ENV_VAR] = Fernet.generate_key().decode()
    await seed()
    fake_port, backend_port, https_port = free_port(), free_port(), free_port()
    workdir = Path(tempfile.mkdtemp(prefix="waf-slow-stats-e2e-"))
    servers, container = [], None
    try:
        servers.append(await serve(build_fake_waf(), fake_port))
        servers.append(await serve(build_backend(), backend_port))
        container = start_nginx(workdir, backend_port, https_port)
        base = f"https://127.0.0.1:{https_port}"
        await wait_for_nginx(base, container)
        print(f"nginx {NGINX_IMAGE} with {NGINX_CONF.relative_to(REPO) if NGINX_CONF.is_relative_to(REPO) else NGINX_CONF}")
        print(f"expecting stats {STATS_TIMEOUT:.0f}s, other reads {DEFAULT_TIMEOUT:.0f}s, connect {CONNECT_TIMEOUT:.0f}s\n")

        headers = {"Authorization": f"Bearer {await AuthHandler().encode_token(ADMIN)}"}
        async with httpx.AsyncClient(base_url=base, verify=False, timeout=300, headers=headers) as c:

            async def add_waf(name: str, api_url: str) -> int:
                body = {"name": name, "api_url": api_url, "service_token": TOKEN, "verify_tls": False}
                r = await c.post(f"/api/customer_waf/{CUSTOMER}", json=body)
                assert r.status_code == 201, f"create {name}: {r.status_code} {r.text}"
                return r.json()["instance"]["id"]

            fake = f"http://127.0.0.1:{fake_port}"
            ids = {
                "fast": await add_waf("fast", f"{fake}/d/0"),
                "busy": await add_waf("busy", f"{fake}/d/70"),
                "stuck": await add_waf("stuck", f"{fake}/d/{STATS_TIMEOUT + 15:.0f}"),
                "slow-events": await add_waf("slow-events", f"{fake}/d/25"),
                "down": await add_waf("down", f"http://127.0.0.1:{free_port()}"),
                "unroutable": await add_waf("unroutable", f"http://{UNROUTABLE}:8443"),
            }

            def get(waf: str, path: str):
                return timed(c.get(f"/api/customer_waf/{CUSTOMER}/{ids[waf]}/{path}"))

            print("=== all cases run concurrently; the slowest takes about two minutes ===")
            (
                (fast, t_fast),
                (busy, t_busy),
                (stuck, t_stuck),
                (events, t_events),
                (down, t_down),
                (unroutable, t_unr),
            ) = await asyncio.gather(
                get("fast", "stats"),
                get("busy", "stats"),
                get("stuck", "stats"),
                get("slow-events", "events"),
                get("down", "stats"),
                get("unroutable", "stats"),
            )

            print("\n=== a WAF that answers ===")
            check(
                "stats at once -> 200 with the WAF's figures",
                fast.status_code == 200 and fast.json()["stats"]["total_1h"] == 4821,
                f"{fast.status_code} in {t_fast:.1f}s",
            )

            print("\n=== a busy WAF: /logs/stats answers in 70s (past nginx's default 60s and the old 15s) ===")
            check("stats -> 200, not a timeout and not nginx's 504", busy.status_code == 200, f"{busy.status_code} in {t_busy:.1f}s")
            check("stats body is the WAF's", busy.status_code == 200 and busy.json()["stats"]["total_1h"] == 4821)
            check("it really took the WAF's 70s", t_busy >= 69, f"{t_busy:.1f}s")

            print(f"\n=== a WAF slower than STATS_TIMEOUT ({STATS_TIMEOUT:.0f}s) ===")
            check("stats -> 502 from the backend, not nginx's 504", stuck.status_code == 502, f"{stuck.status_code} in {t_stuck:.1f}s")
            check("reason is timeout, not unreachable", reason_of(stuck) == "timeout", str(reason_of(stuck)))
            check("detail names the 120s budget", "did not answer within 120s" in stuck.text, stuck.text[:120])
            check("given up after the budget, not before", STATS_TIMEOUT - 1 <= t_stuck < STATS_TIMEOUT + 10, f"{t_stuck:.1f}s")

            print("\n=== every other read keeps the 15s default ===")
            check(
                "events from a WAF taking 25s -> 502 timeout",
                events.status_code == 502 and reason_of(events) == "timeout",
                f"{events.status_code} {reason_of(events)}",
            )
            check("given up at 15s", DEFAULT_TIMEOUT - 1 <= t_events < DEFAULT_TIMEOUT + 5, f"{t_events:.1f}s")

            print("\n=== a WAF that is down reads as unreachable in seconds, even on the stats route ===")
            check(
                "refused connection -> 502 unreachable",
                down.status_code == 502 and reason_of(down) == "unreachable",
                f"{down.status_code} {reason_of(down)}",
            )
            check("refused connection reported at once", t_down < 3, f"{t_down:.1f}s")
            check(
                "unroutable address -> 502 unreachable",
                unroutable.status_code == 502 and reason_of(unroutable) == "unreachable",
                f"{unroutable.status_code} {reason_of(unroutable)}",
            )
            check(
                f"unroutable address given up within the {CONNECT_TIMEOUT:.0f}s connect bound, not the 120s budget",
                t_unr < CONNECT_TIMEOUT + 5,
                f"{t_unr:.1f}s: {unroutable.text[:90]}",
            )
    finally:
        if container:
            subprocess.run(["docker", "stop", "-t", "1", container], capture_output=True)
        for server, _ in servers:
            server.should_exit = True
        # Let in-flight requests (and their DB sessions) finish before the engine goes away.
        await asyncio.wait([task for _, task in servers], timeout=10)
        async with AsyncSession(async_engine) as s:
            await cleanup(s)
        await async_engine.dispose()
        shutil.rmtree(workdir, ignore_errors=True)

    failed = [name for name, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    if not shutil.which("docker") or not shutil.which("openssl"):
        sys.exit("needs docker and openssl on PATH")
    sys.exit(asyncio.run(main()))
