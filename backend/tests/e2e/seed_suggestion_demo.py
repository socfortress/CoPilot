"""Seed di dati dimostrativi per provare a mano i suggerimenti template (#935).

Serve a rendere il test manuale possibile: senza template che parlino di
ransomware/MITRE e senza un alert taggato, il pannello mostra (correttamente)
lo stato vuoto e sembra rotto.

Crea, sul DB a cui punta la tua ``.env``:
  - il cliente DEMO935 (se manca)
  - un alert Wazuh "ransomware" con tag + contesto MITRE T1486
  - 4 template che coprono i casi interessanti: mirato, condizionale che spara,
    condizionale che NON spara, generico con storico d'uso
  - 2 case storici, per far comparire il segnale "usage"

USO
    cd backend
    .venv/bin/python tests/e2e/seed_suggestion_demo.py          # crea
    .venv/bin/python tests/e2e/seed_suggestion_demo.py --purge  # rimuove tutto

Tutte le righe sono marcate col prefisso ``demo935_`` (e cliente ``DEMO935``),
quindi ``--purge`` non tocca nient'altro. Lo script è idempotente: rilanciarlo
ripulisce e ricrea, così non accumula duplicati.

NB: scrive sul database della tua ``.env``. È pensato per un ambiente di
sviluppo, non per una installazione di produzione.
"""

import argparse
import asyncio
import datetime
import sys

from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_session import async_engine
from app.db.universal_models import Customers
from app.incidents.models import Alert
from app.incidents.models import AlertContext
from app.incidents.models import AlertTag
from app.incidents.models import AlertToTag
from app.incidents.models import Asset
from app.incidents.models import Case
from app.incidents.models import CaseTask
from app.incidents.models import CaseTemplate
from app.incidents.models import CaseTemplateTask

CUSTOMER = "DEMO935"
PREFIX = "demo935_"
NOW = datetime.datetime.utcnow()


async def purge(s: AsyncSession) -> None:
    """Rimuove solo ciò che questo script crea, dai figli verso i padri."""
    tmpl_ids = list((await s.execute(select(CaseTemplate.id).where(CaseTemplate.name.like(f"{PREFIX}%")))).scalars().all())
    case_ids = list((await s.execute(select(Case.id).where(Case.customer_code == CUSTOMER))).scalars().all())
    alert_ids = list((await s.execute(select(Alert.id).where(Alert.customer_code == CUSTOMER))).scalars().all())

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
    await s.execute(delete(AlertTag).where(AlertTag.tag.like(f"{PREFIX}%")))
    await s.commit()


async def seed(s: AsyncSession) -> dict:
    if not (await s.execute(select(Customers).where(Customers.customer_code == CUSTOMER))).scalars().first():
        s.add(
            Customers(
                customer_code=CUSTOMER,
                customer_name="Demo 935 (suggerimenti template)",
                contact_first_name="Demo",
                contact_last_name="935",
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

    alert = Alert(
        alert_name="Ransomware encryption behaviour on FILESRV01",
        alert_description="Mass file rename with known extension, possible encryption in progress",
        status="OPEN",
        alert_creation_time=NOW,
        customer_code=CUSTOMER,
        source="wazuh",
        severity="Critical",
        escalated=False,
    )
    s.add(alert)
    await s.commit()

    tag = AlertTag(tag=f"{PREFIX}ransomware")
    s.add(tag)
    await s.commit()
    s.add(AlertToTag(alert_id=alert.id, tag_id=tag.id))

    ctx = AlertContext(
        source="wazuh",
        context={
            "rule_mitre_id": ["T1486"],
            "rule_mitre_technique": "Data Encrypted for Impact",
            "rule_groups": "windows,ransomware,syslog",
            "data_win_system_eventID": "11",
            "rule_id": "554",
            "rule_level": "12",
        },
    )
    s.add(ctx)
    await s.commit()

    s.add(
        Asset(
            alert_linked=alert.id,
            asset_name="FILESRV01",
            alert_context_id=ctx.id,
            agent_id="demo935-1",
            velociraptor_id="",
            customer_code=CUSTOMER,
            index_name="wazuh-alerts-4.x-demo",
            index_id="demo935doc",
        ),
    )
    await s.commit()

    def tmpl(name, **kw):
        kw.setdefault("customer_code", None)
        kw.setdefault("source", None)
        kw.setdefault("is_default", False)
        kw.setdefault("match_field", None)
        kw.setdefault("match_value", None)
        return CaseTemplate(name=name, created_by="demo-seed", created_at=NOW, updated_at=NOW, **kw)

    targeted = tmpl(
        f"{PREFIX}Ransomware containment",
        description="Contain an encrypting host and preserve evidence",
        customer_code=CUSTOMER,
        source="wazuh",
    )
    cond_ok = tmpl(
        f"{PREFIX}Sysmon file-create deep dive",
        description="Applies only when the Sysmon event is a file creation (eventID 11)",
        source="wazuh",
        match_field="data_win_system_eventID",
        match_value="11",
    )
    cond_fail = tmpl(
        f"{PREFIX}Sysmon process-create deep dive",
        description="Applies only to process creation (eventID 4688) — should NOT be suggested here",
        source="wazuh",
        match_field="data_win_system_eventID",
        match_value="4688",
    )
    generic = tmpl(f"{PREFIX}Generic triage", description="Baseline checks for any alert", is_default=True)

    for t in (targeted, cond_ok, cond_fail, generic):
        s.add(t)
    await s.commit()

    s.add(CaseTemplateTask(template_id=targeted.id, title="Isolate the affected host", order_index=0, mandatory=True))
    s.add(
        CaseTemplateTask(
            template_id=targeted.id,
            title="Identify the encryption scope",
            description="Ransomware payload and blast-radius analysis",
            guidelines="Maps to MITRE T1486 (Data Encrypted for Impact). List encrypted shares before restoring.",
            order_index=1,
            mandatory=True,
        ),
    )
    s.add(CaseTemplateTask(template_id=targeted.id, title="Notify the customer", order_index=2))
    s.add(CaseTemplateTask(template_id=cond_ok.id, title="Review the created file and its parent process", order_index=0))
    s.add(CaseTemplateTask(template_id=cond_fail.id, title="Review the command line", order_index=0))
    s.add(CaseTemplateTask(template_id=generic.id, title="Confirm the alert is not a false positive", order_index=0))
    s.add(CaseTemplateTask(template_id=generic.id, title="Document the findings", order_index=1))
    await s.commit()

    # Storico d'uso: 2 case che hanno già applicato il template generico, così
    # nel pannello compare il segnale "Applied to 2 case(s) for DEMO935".
    gen_task = (await s.execute(select(CaseTemplateTask).where(CaseTemplateTask.template_id == generic.id).limit(1))).scalars().first()
    for i in range(2):
        c = Case(
            case_name=f"{PREFIX}historic case {i + 1}",
            case_description="Seeded to demonstrate the usage-history signal",
            case_creation_time=NOW,
            case_status="CLOSED",
            customer_code=CUSTOMER,
            escalated=False,
        )
        s.add(c)
        await s.commit()
        s.add(
            CaseTask(
                case_id=c.id,
                template_task_id=gen_task.id,
                title=gen_task.title,
                mandatory=False,
                order_index=0,
                status="DONE",
                created_by="demo-seed",
                created_at=NOW,
                updated_at=NOW,
            ),
        )
    await s.commit()

    return {
        "alert_id": alert.id,
        "targeted": targeted.id,
        "cond_ok": cond_ok.id,
        "cond_fail": cond_fail.id,
        "generic": generic.id,
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description="Seed/purge demo data for case-template suggestions (#935)")
    parser.add_argument("--purge", action="store_true", help="rimuove i dati demo ed esce")
    args = parser.parse_args()

    # expire_on_commit=False: il seed riusa gli id dopo ogni commit e col
    # default scatterebbe un refresh sincrono in contesto async
    # (MissingGreenlet, vedi CLAUDE.md).
    async with AsyncSession(async_engine, expire_on_commit=False) as s:
        await purge(s)
        if args.purge:
            print(f"Dati demo rimossi (cliente {CUSTOMER}, prefisso {PREFIX}).")
            await async_engine.dispose()
            return 0

        ids = await seed(s)

    await async_engine.dispose()
    print(
        "\n".join(
            [
                "",
                f"Seed completato sul cliente {CUSTOMER}.",
                "",
                f"  Alert da aprire in UI: #{ids['alert_id']}  (Incident Management -> Alerts, filtra per customer {CUSTOMER})",
                "",
                "  Template creati:",
                f"    #{ids['cond_ok']:<4} Sysmon file-create deep dive   <- condizione SPARA (eventID 11): deve stare in CIMA",
                f"    #{ids['targeted']:<4} Ransomware containment         <- punteggio più alto, ma sotto al condizionale",
                f"    #{ids['generic']:<4} Generic triage                 <- mostra il segnale 'usage' (2 case)",
                f"    #{ids['cond_fail']:<4} Sysmon process-create deep dive <- condizione NON spara: NON deve comparire",
                "",
                "Ora apri l'alert e premi 'Create case'.",
                "Per rimuovere tutto:  .venv/bin/python tests/e2e/seed_suggestion_demo.py --purge",
                "",
            ],
        ),
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
