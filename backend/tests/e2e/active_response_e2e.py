"""E2E per #960 — NON raccolto da pytest (serve un MySQL vivo); si lancia a mano.

    docker run -d --name copilot-e2e-mysql -p 13306:3306 \
        -e MYSQL_ROOT_PASSWORD=e2eroot -e MYSQL_DATABASE=copilot \
        -e MYSQL_USER=copilot -e MYSQL_PASSWORD=e2epass mysql:8.0

    cd backend && export MYSQL_URL=127.0.0.1:13306 MYSQL_USER=copilot \
        MYSQL_PASSWORD=e2epass MYSQL_ROOT_PASSWORD=e2eroot \
        JWT_SECRET=e2e-test-secret-not-the-default PYTHONPATH=$PWD
    .venv/bin/python -c "from app.db.db_setup import apply_migrations; apply_migrations()"
    .venv/bin/python tests/e2e/active_response_e2e.py

Oppure dentro l'immagine di produzione, che verifica in più che il codice
importi e giri nell'artefatto realmente deployato:

    docker run --rm --add-host=host.docker.internal:host-gateway \
        -e MYSQL_URL=host.docker.internal:13306 -e MYSQL_USER=copilot \
        -e MYSQL_PASSWORD=e2epass -e MYSQL_ROOT_PASSWORD=e2eroot \
        -e JWT_SECRET=e2e-test-secret-not-the-default \
        -e PYTHONPATH=/opt/copilot/backend \
        ghcr.io/socfortress/copilot-backend:latest python tests/e2e/active_response_e2e.py

Punta a un'istanza usa-e-getta sulla porta 13306: mai al MySQL della .env.

Perché serve un e2e e non bastano gli unit test di #960: il bug arrivava
all'analista *attraverso* `validation_exception_handler`, che non è codice
puro — apre una `AsyncSession`, risolve l'utente dal token e scrive una riga
in `log_entries` prima di rispondere. Gli unit test coprono lo schema e la
composizione del messaggio; solo qui si vede che la 422 esce davvero con quel
testo, e che la sua scrittura a DB non esplode.

L'unica cosa stubbata è la PUT verso Wazuh: un e2e completo richiederebbe un
Wazuh Manager vivo e un agent Windows registrato. Tutto il resto è reale —
routing, `Security(require_any_scope(...))`, JWT, exception handler, MySQL.

Verifica:
  A) il payload esatto che manda il frontend -> 200 (era 422 "Invalid value.")
  B) un IP non valido -> 422 che nomina il campo e il motivo
  C) un rifiuto di Wazuh -> 502, non un finto successo
  D) il connettore Wazuh assente -> 503
  E) il comando nel casing della UI (WINDOWS_FIREWALL) -> 200
  F) senza token -> respinto
  G) la 422 di (B) è finita davvero in log_entries
"""
import asyncio
import os
import sys
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

import httpx  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError  # noqa: E402
from sqlalchemy import delete  # noqa: E402
from sqlalchemy import desc
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

import app.active_response.routes.active_response as ar_routes  # noqa: E402
from app.active_response.routes.active_response import (  # noqa: E402
    active_response_router,
)
from app.auth.models.users import Role  # noqa: E402
from app.auth.models.users import User
from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import LogEntry  # noqa: E402
from app.middleware.exception_handlers import (  # noqa: E402
    custom_http_exception_handler,
)
from app.middleware.exception_handlers import validation_exception_handler

PASSWORD = "E2ePassw0rd!x"
ANALYST = "e2e_ar_analyst"

FAILURES = []


def check(name, condition, detail=""):
    mark = "PASS" if condition else "FAIL"
    print(f"  [{mark}] {name}{('  -> ' + detail) if detail and not condition else ''}")
    if not condition:
        FAILURES.append(name)


def build_payload(**overrides):
    """Il corpo esatto che costruisce frontend/src/api/endpoints/active-response.ts."""
    payload = {
        "endpoint": "/active-response",
        "arguments": [],
        "command": "windows_firewall",
        "custom": True,
        "alert": {"action": "block", "ip": "1.1.1.1"},
        "params": {"wait_for_complete": True, "agents_list": ["032"]},
    }
    payload.update(overrides)
    return payload


def build_app():
    """L'app reale in miniatura: stesso router, stessi exception handler di copilot.py."""
    app = FastAPI()
    app.include_router(active_response_router, prefix="/active_response", tags=["active-response"])
    app.add_exception_handler(HTTPException, custom_http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    return app


async def ensure_analyst(session: AsyncSession) -> str:
    """Crea (idempotente) un analyst reale e ne restituisce un JWT reale."""
    auth = AuthHandler()

    role = (await session.execute(select(Role).where(Role.id == 2))).scalars().first()
    if role is None:
        session.add(Role(id=2, name="analyst", description="e2e"))
        await session.commit()

    user = (await session.execute(select(User).where(User.username == ANALYST))).scalars().first()
    if user is None:
        user = User(username=ANALYST, password=auth.get_password_hash(PASSWORD), email=f"{ANALYST}@e2e.local", role_id=2)
        session.add(user)
        await session.commit()

    # encode_token e' async e prende lo username: il ruolo lo risolve da DB.
    return await auth.encode_token(ANALYST)


async def max_log_id(session: AsyncSession) -> int:
    row = (await session.execute(select(LogEntry).order_by(desc(LogEntry.id)).limit(1))).scalars().first()
    return row.id if row else 0


async def main():
    async with AsyncSession(async_engine) as session:
        token = await ensure_analyst(session)

    headers = {"Authorization": f"Bearer {token}"}
    app = build_app()
    transport = httpx.ASGITransport(app=app)
    ok = {"success": True, "data": {"data": {"affected_items": ["032"]}}}

    async with httpx.AsyncClient(transport=transport, base_url="http://e2e") as client:
        print("\nA) il payload esatto del frontend")
        stub = AsyncMock(return_value=ok)
        with patch.object(ar_routes, "send_put_request", new=stub):
            r = await client.post("/active_response/invoke", json=build_payload(), headers=headers)
        check("200, non piu' 422 'Invalid value.'", r.status_code == 200, f"{r.status_code} {r.text}")
        check("risposta success=true", r.json().get("success") is True, r.text)
        # Sul codice pre-fix la richiesta muore in validazione e Wazuh non viene
        # mai chiamato: nessun call_args. Non far esplodere lo script, cosi' un
        # run fallito riporta comunque tutti i controlli.
        sent = stub.call_args.kwargs if stub.call_args else None
        check("la PUT verso Wazuh e' partita", sent is not None, "send_put_request mai chiamata")
        check(
            "il corpo verso Wazuh ha il comando con suffisso 0",
            bool(sent) and '"command": "windows_firewall0"' in sent["data"],
            str(sent),
        )
        check("l'IP arriva intatto", bool(sent) and '"ip": "1.1.1.1"' in sent["data"], str(sent))
        check(
            "wait_for_complete e' un booleano JSON",
            bool(sent) and sent["params"]["wait_for_complete"] == "true",
            str(sent),
        )

        print("\nB) un IP non valido")
        # Ancora il controllo (G) a questo punto: senza, una riga lasciata da un
        # run precedente sullo stesso DB lo farebbe passare a vuoto.
        async with AsyncSession(async_engine) as session:
            log_high_water = await max_log_id(session)
        with patch.object(ar_routes, "send_put_request", new=AsyncMock(return_value=ok)):
            r = await client.post(
                "/active_response/invoke",
                json=build_payload(alert={"action": "block", "ip": "10.0.0"}),
                headers=headers,
            )
        body = r.json()
        check("422", r.status_code == 422, f"{r.status_code} {r.text}")
        check("il messaggio nomina il campo", "ip" in body.get("message", ""), r.text)
        check("il messaggio dice il motivo", "not a valid IP address" in body.get("message", ""), r.text)
        check("non e' piu' il generico 'Invalid value.'", body.get("message") != "Invalid value.", r.text)

        print("\nC) Wazuh rifiuta la richiesta")
        rejected = {"success": False, "message": "HTTP error 400", "error_detail": "Invalid agent ID"}
        with patch.object(ar_routes, "send_put_request", new=AsyncMock(return_value=rejected)):
            r = await client.post("/active_response/invoke", json=build_payload(), headers=headers)
        check("502, non un finto 200", r.status_code == 502, f"{r.status_code} {r.text}")
        check("riporta il motivo di Wazuh", "Invalid agent ID" in r.text, r.text)

        print("\nD) connettore Wazuh assente")
        with patch.object(ar_routes, "send_put_request", new=AsyncMock(return_value=None)):
            r = await client.post("/active_response/invoke", json=build_payload(), headers=headers)
        check("503", r.status_code == 503, f"{r.status_code} {r.text}")

        print("\nE) comando nel casing mostrato dalla UI")
        with patch.object(ar_routes, "send_put_request", new=AsyncMock(return_value=ok)):
            r = await client.post(
                "/active_response/invoke",
                json=build_payload(command="WINDOWS_FIREWALL"),
                headers=headers,
            )
        check("200, non 500 da KeyError", r.status_code == 200, f"{r.status_code} {r.text}")

        print("\nF) senza token")
        r = await client.post("/active_response/invoke", json=build_payload())
        check("respinto", r.status_code in (401, 403), f"{r.status_code} {r.text}")

    print("\nG) la 422 e' stata scritta su log_entries")
    async with AsyncSession(async_engine) as session:
        # Solo le righe scritte dopo (B): validation_exception_handler apre una
        # sessione e logga *prima* di rispondere, quindi se il messaggio nuovo
        # rompesse quella scrittura la 422 non arriverebbe mai all'analista.
        rows = (await session.execute(select(LogEntry).where(LogEntry.id > log_high_water))).scalars().all()
        messages = [row.message or "" for row in rows]
        check(
            "la riga con il messaggio dettagliato esiste",
            any("not a valid IP address" in m for m in messages),
            f"righe dopo id {log_high_water}: {messages}",
        )

    async with AsyncSession(async_engine) as session:
        await session.execute(delete(User).where(User.username == ANALYST))
        await session.commit()

    print()
    if FAILURES:
        print(f"FALLITI: {len(FAILURES)} -> {FAILURES}")
        sys.exit(1)
    print("Tutti i controlli e2e sono passati.")


if __name__ == "__main__":
    asyncio.run(main())
