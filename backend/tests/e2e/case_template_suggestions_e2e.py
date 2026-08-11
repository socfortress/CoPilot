"""E2E per #935 — NON raccolto da pytest (serve un MySQL vivo); si lancia a mano.

    docker run -d --name copilot-e2e-mysql -p 13306:3306 \
        -e MYSQL_ROOT_PASSWORD=e2eroot -e MYSQL_DATABASE=copilot \
        -e MYSQL_USER=copilot -e MYSQL_PASSWORD=e2epass mysql:8.0

    cd backend && export MYSQL_URL=127.0.0.1:13306 MYSQL_USER=copilot \
        MYSQL_PASSWORD=e2epass MYSQL_ROOT_PASSWORD=e2eroot \
        JWT_SECRET=e2e-test-secret-not-the-default PYTHONPATH=$PWD
    .venv/bin/python -c "from app.db.db_setup import apply_migrations; apply_migrations()"
    .venv/bin/python tests/e2e/case_template_suggestions_e2e.py

Oppure dentro l'immagine di produzione, che verifica in più che il codice
importi e giri nell'artefatto realmente deployato:

    cd backend && docker build -t copilot-backend:e2e-935 .
    docker run --rm --add-host=host.docker.internal:host-gateway \
        -e MYSQL_URL=host.docker.internal:13306 -e MYSQL_USER=copilot \
        -e MYSQL_PASSWORD=e2epass -e MYSQL_ROOT_PASSWORD=e2eroot \
        -e JWT_SECRET=e2e-test-secret-not-the-default \
        -e PYTHONPATH=/opt/copilot/backend \
        copilot-backend:e2e-935 python tests/e2e/case_template_suggestions_e2e.py

Punta a un'istanza usa-e-getta sulla porta 13306: mai al MySQL della .env.

I unit test di ``tests/test_case_template_suggestions.py`` girano su sessioni
mockate, quindi non eseguono una sola riga di SQL. Questo script copre proprio
ciò che quelli non possono:

  1. La query di usage-history — ``COUNT(DISTINCT case_id)`` su un join a tre
     tavole con GROUP BY — gira davvero su MySQL.
  2. Il join AlertContext → Asset che estrae MITRE e rule groups legge righe
     vere, non un dict finto.
  3. La riga ORM ``CaseTemplate`` (con i task caricati via ``selectinload``)
     si serializza davvero in ``CaseTemplateResponse`` annidato — è esattamente
     il punto in cui Pydantic 2 fallisce quando manca ``from_attributes``.
  4. La rotta ``/suggest`` è raggiungibile e non viene inghiottita dal
     wildcard ``/{template_id}`` una volta montata sull'app reale.
  5. Lo scope guard admin/analyst è applicato dal router vero.

Verifica le assunzioni portanti:
  A) ranking end-to-end su un alert vero (tag + MITRE + scope)
  B) isolamento tenant: il template di un altro cliente non compare mai
  C) condizione auto-apply che fallisce -> template escluso
  D) usage-history calcolata da SQL reale e limitata al cliente
  E) percorso manuale (customer_code, nessun alert)
  F) i reason sommano allo score, sui dati veri
"""

import asyncio
import datetime
import os

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

import httpx  # noqa: E402
from fastapi import APIRouter  # noqa: E402
from fastapi import FastAPI
from sqlalchemy import delete  # noqa: E402
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.auth.models.users import Role  # noqa: E402
from app.auth.models.users import User
from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.incidents.models import Alert  # noqa: E402
from app.incidents.models import AlertContext
from app.incidents.models import AlertTag
from app.incidents.models import AlertToTag
from app.incidents.models import Asset
from app.incidents.models import Case
from app.incidents.models import CaseTask
from app.incidents.models import CaseTemplate
from app.incidents.models import CaseTemplateTask

PASSWORD = "E2ePassw0rd!x"
CUST_A, CUST_B = "E2E935_A", "E2E935_B"
ANALYST = "e2e935_analyst"

NOW = datetime.datetime(2026, 1, 1)
results = []

# Marcatore su ogni riga creata qui, così la pulizia non tocca dati veri se
# per errore qualcuno punta lo script a un DB popolato.
TAG_PREFIX = "e2e935_"


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


async def _purge(s):
    """Pulizia da run precedenti, dai figli verso i padri."""
    tmpl_ids = list(
        (await s.execute(select(CaseTemplate.id).where(CaseTemplate.name.like(f"{TAG_PREFIX}%")))).scalars().all(),
    )
    case_ids = list((await s.execute(select(Case.id).where(Case.customer_code.in_([CUST_A, CUST_B])))).scalars().all())
    alert_ids = list((await s.execute(select(Alert.id).where(Alert.customer_code.in_([CUST_A, CUST_B])))).scalars().all())

    if case_ids:
        await s.execute(delete(CaseTask).where(CaseTask.case_id.in_(case_ids)))
    if tmpl_ids:
        await s.execute(delete(CaseTemplateTask).where(CaseTemplateTask.template_id.in_(tmpl_ids)))
        await s.execute(delete(CaseTemplate).where(CaseTemplate.id.in_(tmpl_ids)))
    if case_ids:
        await s.execute(delete(Case).where(Case.id.in_(case_ids)))
    if alert_ids:
        await s.execute(delete(AlertToTag).where(AlertToTag.alert_id.in_(alert_ids)))
        await s.execute(delete(Asset).where(Asset.alert_linked.in_(alert_ids)))
        await s.execute(delete(Alert).where(Alert.id.in_(alert_ids)))
    await s.execute(delete(AlertTag).where(AlertTag.tag.like(f"{TAG_PREFIX}%")))
    await s.commit()


async def seed():
    """Un alert ransomware su CUST_A + cinque template che coprono ogni caso.

    ``expire_on_commit=False``: il seed fa molte commit di fila e poi riusa gli
    id degli oggetti già inseriti (``AlertToTag(alert_id=alert.id, ...)``). Col
    default, ogni commit scade gli attributi e il primo accesso successivo
    tenta un refresh sincrono dentro un contesto async — cioè il
    ``MissingGreenlet`` descritto in CLAUDE.md.
    """
    auth = AuthHandler()
    async with AsyncSession(async_engine, expire_on_commit=False) as s:
        for rid, rname in [(1, "admin"), (2, "analyst"), (3, "scheduler"), (4, "customer_user")]:
            if not (await s.execute(select(Role).where(Role.id == rid))).scalars().first():
                s.add(Role(id=rid, name=rname, description=rname))
        await s.commit()

        await _purge(s)

        u = (await s.execute(select(User).where(User.username == ANALYST))).scalars().first()
        if u:
            await s.delete(u)
            await s.commit()

        for code in (CUST_A, CUST_B):
            c = (await s.execute(select(Customers).where(Customers.customer_code == code))).scalars().first()
            if not c:
                s.add(
                    Customers(
                        customer_code=code,
                        customer_name=f"Customer {code}",
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
        await s.commit()

        s.add(User(username=ANALYST, password=auth.get_password_hash(PASSWORD), email=f"{ANALYST}@e2e.local", role_id=2))
        await s.commit()

        # --- alert con tag + contesto MITRE ------------------------------
        alert = Alert(
            alert_name="Ransomware encryption behaviour on FILESRV01",
            alert_description="Mass file rename detected",
            status="OPEN",
            alert_creation_time=NOW,
            customer_code=CUST_A,
            source="wazuh",
            severity="Critical",
            assigned_to=None,
            escalated=False,
        )
        s.add(alert)
        await s.commit()
        await s.refresh(alert)

        tag = AlertTag(tag=f"{TAG_PREFIX}ransomware")
        s.add(tag)
        await s.commit()
        await s.refresh(tag)
        s.add(AlertToTag(alert_id=alert.id, tag_id=tag.id))

        # Il contesto è ciò che l'ingest scrive davvero: chiavi piatte, valori
        # eterogenei (lista per il MITRE, stringa delimitata per i gruppi).
        ctx = AlertContext(
            source="wazuh",
            context={
                "rule_mitre_id": ["T1486"],
                "rule_mitre_technique": "Data Encrypted for Impact",
                # 'ransomware' deve matchare il testo del template, 'syslog' è
                # nella stoplist dei gruppi generici, 'windows' non compare nel
                # corpus: i tre casi in una riga sola.
                "rule_groups": "windows,ransomware,syslog",
                "data_win_system_eventID": "11",
                "rule_id": "554",
            },
        )
        s.add(ctx)
        await s.commit()
        await s.refresh(ctx)

        s.add(
            Asset(
                alert_linked=alert.id,
                asset_name="FILESRV01",
                alert_context_id=ctx.id,
                agent_id="e2e935-1",
                velociraptor_id="",
                customer_code=CUST_A,
                index_name="wazuh-alerts-4.x-e2e",
                index_id="e2e935doc",
            ),
        )
        await s.commit()

        # --- template ----------------------------------------------------
        def tmpl(name, **kw):
            kw.setdefault("customer_code", None)
            kw.setdefault("source", None)
            kw.setdefault("is_default", False)
            kw.setdefault("match_field", None)
            kw.setdefault("match_value", None)
            return CaseTemplate(name=name, created_by="e2e", created_at=NOW, updated_at=NOW, **kw)

        # 1. il bersaglio: cliente + source giusti, testo che parla di T1486
        target = tmpl(
            f"{TAG_PREFIX}Ransomware containment",
            description="Contain encrypting hosts",
            customer_code=CUST_A,
            source="wazuh",
        )
        # 2. altro tenant, testo identico: non deve MAI comparire
        other_tenant = tmpl(
            f"{TAG_PREFIX}Ransomware containment (other tenant)",
            description="Contain encrypting hosts, T1486",
            customer_code=CUST_B,
            source="wazuh",
        )
        # 3. globale generico, usato spesso in passato -> prova usage-history
        generic = tmpl(f"{TAG_PREFIX}Generic triage", description="Baseline checks")
        # 4. condizionale che NON matcha (eventID 11 != 4688) -> va escluso
        cond_fail = tmpl(
            f"{TAG_PREFIX}Process creation deep dive",
            source="wazuh",
            match_field="data_win_system_eventID",
            match_value="4688",
        )
        # 5. condizionale che matcha -> deve vincere
        cond_ok = tmpl(
            f"{TAG_PREFIX}File create deep dive",
            source="wazuh",
            match_field="data_win_system_eventID",
            match_value="11",
        )
        for t in (target, other_tenant, generic, cond_fail, cond_ok):
            s.add(t)
        await s.commit()
        for t in (target, other_tenant, generic, cond_fail, cond_ok):
            await s.refresh(t)

        s.add(CaseTemplateTask(template_id=target.id, title="Isolate the host", order_index=0, mandatory=True))
        s.add(
            CaseTemplateTask(
                template_id=target.id,
                title="Identify encryption scope",
                description="Ransomware payload analysis",
                guidelines="Maps to T1486 Data Encrypted for Impact",
                order_index=1,
            ),
        )
        # Volutamente fuori ordine: il preview deve riordinarli per order_index.
        s.add(CaseTemplateTask(template_id=generic.id, title="Second step", order_index=1))
        s.add(CaseTemplateTask(template_id=generic.id, title="First step", order_index=0))
        await s.commit()

        # --- usage-history: 3 case su CUST_A usano 'generic' -------------
        gen_task = (await s.execute(select(CaseTemplateTask).where(CaseTemplateTask.template_id == generic.id).limit(1))).scalars().first()
        for i in range(3):
            c = Case(
                case_name=f"{TAG_PREFIX}case {i}",
                case_description="x",
                case_creation_time=NOW,
                case_status="OPEN",
                customer_code=CUST_A,
                escalated=False,
            )
            s.add(c)
            await s.commit()
            await s.refresh(c)
            s.add(
                CaseTask(
                    case_id=c.id,
                    template_task_id=gen_task.id,
                    title="First step",
                    mandatory=False,
                    order_index=0,
                    status="TODO",
                    created_by="e2e",
                    created_at=NOW,
                    updated_at=NOW,
                ),
            )
        await s.commit()

        print(
            f"seed: alert #{alert.id} su {CUST_A} (tag ransomware, T1486), "
            f"5 template, 3 case storici sul template 'generic' (#{generic.id})",
        )
        return {
            "alert_id": alert.id,
            "target": target.id,
            "other_tenant": other_tenant.id,
            "generic": generic.id,
            "cond_fail": cond_fail.id,
            "cond_ok": cond_ok.id,
        }


def build_app():
    """Monta il router reale senza gli hook di startup (MinIO/connettori)."""
    from app.incidents.routes.case_templates import case_templates_router

    api = APIRouter()
    api.include_router(case_templates_router, prefix="/incidents/case_templates", tags=["incidents-case-templates"])
    app = FastAPI()
    app.include_router(api)
    return app


async def main():
    ids = await seed()
    app = build_app()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://e2e", timeout=30) as client:
        token = await AuthHandler().encode_token(ANALYST)
        H = {"Authorization": f"Bearer {token}"}

        print("\n=== A) ranking da un alert vero ===")
        r = await client.get(f"/incidents/case_templates/suggest?alert_id={ids['alert_id']}&limit=10", headers=H)
        ok = r.status_code == 200 and r.json().get("success") is True
        check("GET /suggest -> 200 success", ok, f"{r.status_code} {r.text[:160]}")
        if not ok:
            return summary()

        body = r.json()
        got = [s["template"]["id"] for s in body["suggestions"]]
        by_id = {s["template"]["id"]: s for s in body["suggestions"]}

        check(
            "la rotta /suggest non è inghiottita da /{template_id}",
            "suggestions" in body,
            f"chiavi={sorted(body)}",
        )
        # Il condizionale che matcha deve stare in cima ANCHE se un altro
        # template segna di più: è la partizione che tiene il pannello
        # d'accordo con pick_templates_for_alert.
        check(
            "il condizionale che matcha (eventID=11) è in cima, pur segnando meno",
            got and got[0] == ids["cond_ok"],
            f"ordine={got} score={[(s['template']['id'], s['score']) for s in body['suggestions']]}",
        )
        check(
            "condition_matched esposto solo sul template la cui condizione ha sparato",
            [s["template"]["id"] for s in body["suggestions"] if s["condition_matched"]] == [ids["cond_ok"]],
            str([(s["template"]["id"], s["condition_matched"]) for s in body["suggestions"]]),
        )
        check(
            "il template mirato (cliente+source+T1486) è suggerito",
            ids["target"] in got,
            f"ordine={got}",
        )

        print("\n=== B) isolamento tenant ===")
        check(
            "il template di un ALTRO cliente non compare mai",
            ids["other_tenant"] not in got,
            f"ordine={got}",
        )

        print("\n=== C) condizione auto-apply fallita ===")
        check(
            "il condizionale che NON matcha (eventID=4688) è escluso",
            ids["cond_fail"] not in got,
            f"ordine={got}",
        )

        print("\n=== D) usage-history da SQL reale ===")
        gen = by_id.get(ids["generic"])
        usage_reasons = [x for x in (gen or {}).get("reasons", []) if x["signal"] == "usage"]
        check(
            "COUNT(DISTINCT case_id) conta i 3 case storici",
            bool(usage_reasons) and "3 case(s)" in usage_reasons[0]["detail"],
            f"reasons={[x['detail'] for x in (gen or {}).get('reasons', [])]}",
        )

        print("\n=== E) segnali estratti da righe vere ===")
        tgt = by_id.get(ids["target"], {})
        signals = {x["signal"] for x in tgt.get("reasons", [])}
        check("scope cliente riconosciuto", "customer" in signals, f"segnali={sorted(signals)}")
        check("scope source riconosciuto", "source" in signals, f"segnali={sorted(signals)}")
        check(
            "MITRE T1486 estratto dal contesto e trovato nel testo dei task",
            "mitre" in signals,
            f"segnali={sorted(signals)}",
        )
        check(
            "rule group non generico riconosciuto (syslog scartato)",
            "rule_group" in signals,
            f"segnali={sorted(signals)}",
        )

        print("\n=== F) serializzazione ORM -> Pydantic annidato ===")
        gen_tasks = [t["title"] for t in (gen or {}).get("template", {}).get("tasks", [])]
        check(
            "i task arrivano col preview e ordinati per order_index",
            gen_tasks == ["First step", "Second step"],
            f"tasks={gen_tasks}",
        )
        check(
            "i reason sommano allo score, su dati veri",
            all(sum(x["points"] for x in s["reasons"]) == s["score"] for s in body["suggestions"]),
            str([(s["template"]["id"], s["score"], sum(x["points"] for x in s["reasons"])) for s in body["suggestions"]]),
        )

        print("\n=== G) percorso manuale (nessun alert) ===")
        r2 = await client.get(f"/incidents/case_templates/suggest?customer_code={CUST_A}&limit=10", headers=H)
        ok2 = r2.status_code == 200 and r2.json().get("success") is True
        check("GET /suggest?customer_code -> 200 success", ok2, f"{r2.status_code} {r2.text[:160]}")
        if ok2:
            got2 = [s["template"]["id"] for s in r2.json()["suggestions"]]
            check("anche qui l'altro tenant è escluso", ids["other_tenant"] not in got2, f"ordine={got2}")
            check(
                "i condizionali restano visibili (documento non leggibile = ignoto)",
                ids["cond_ok"] in got2,
                f"ordine={got2}",
            )

        print("\n=== H) scope guard del router reale ===")
        r3 = await client.get(f"/incidents/case_templates/suggest?customer_code={CUST_A}")
        check("senza token -> 401/403", r3.status_code in (401, 403), str(r3.status_code))

    # Senza dispose, aiomysql chiude le connessioni nel __del__ a loop già
    # chiuso e sporca l'output con RuntimeError che non sono fallimenti.
    await async_engine.dispose()
    return summary()


def summary():
    failed = [r for r in results if not r[1]]
    print(f"\n{'=' * 60}\n{len(results) - len(failed)}/{len(results)} PASS")
    for name, _, detail in failed:
        print(f"  FAIL: {name}  [{detail}]")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
