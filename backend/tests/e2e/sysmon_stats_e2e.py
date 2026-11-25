r"""End to end: CoPilot's weekly Sysmon noise reports, through sysmon-sync, into the installer repository's suggestion gates.

Local only; nothing touches a remote host. Skipped unless these are set:

    SYSMON_SYNC_DIR     a sysmon-sync checkout (its in-process test harness receives the reports)
    SYSMON_SYNC_PYTHON  a Python with sysmon-sync's requirements-dev (its Development section)
    CKA_DIR             a Client-Kickstart-Automated checkout (its `sysmonctl suggest check` judges the candidates)
    CKA_PYTHON          optional, default python3 (3.11 or later)

    cd backend && SYSMON_SYNC_DIR=... SYSMON_SYNC_PYTHON=... CKA_DIR=... \
      MYSQL_USER=test MYSQL_PASSWORD=test MYSQL_ROOT_PASSWORD=test MYSQL_URL=127.0.0.1:9 JWT_SECRET=ci-dummy \
      python tests/e2e/sysmon_stats_e2e.py

1. Build (this process): three fake CoPilots A, B and C, each with its own license key, report secret, SQLite tables,
   MinIO and indexer, run the real scheduled tick (collector, redactor, report builder, the vendored validator) for
   ISO weeks 2026-W46 and 2026-W47 over synthetic Sysmon alerts. The reports' exact bytes are captured at the HTTP
   layer and written to /tmp/stats-e2e/. Seeded patterns: P1 a vendor DNS query on 5 endpoints in A, B and C, both
   weeks; P2 a vendor updater writing an .exe under a service account's AppData (the redacted value holds <user>);
   P3 a vendor helper started by WmiPrvSE.exe (a ProcessCreate, no command line); P4 a vendor DNS query in A only
   (P4b in A and B); P5 a NetworkConnect to a vendor host; P6 an alert at rule level 10; P7 a .local DNS query; P8 the EDR's own
   install folder (a different InstallDirName in each CoPilot: the code, an admin hint, discovered from the stored
   config). Locally: P6 and P7 are absent, P8 carries __INSTALLDIRNAME__, no payload holds a customer code, name, host
   name or license key, and sysmon-sync's own validator (loaded from SYSMON_SYNC_DIR) accepts every report.
2. Service (sysmon-sync's venv, a subprocess, tests/e2e/sysmon_stats_sysmon_sync_driver.py): the probe while reports are
   off (404) and on (401), every report posted as the exact bytes (200, nothing rejected), a withdraw of C's second
   customer (200) and a repost right after it (409), a deliberately unredacted report (422 identity-leak), then the
   candidates.
3. CKA: `sysmonctl suggest check` on the candidates: nothing invalid; P1 survives as a global suggestion; P2 is dropped
   (a placeholder in the narrowest rule); P3 goes to a person (processcreate-never-drafted; older CKA: dropped as
   baseline-incomplete); P4 (one owner) is dropped as an unknown customer's and P4b (two owners) deferred below the
   threshold: neither is suggested; P5 and P8 only have to load.
4. Feedback: the probe answers and the 422 go back through CoPilot's classifier (not accepting / accepting; refused and
   the pause).
"""
import asyncio
import hashlib
import importlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from datetime import timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("JWT_SECRET", "e2e-only-secret-not-the-compromised-default")

WORK = Path(os.environ.get("STATS_E2E_DIR", "/tmp/stats-e2e"))
SYSMON_SYNC_DIR = os.environ.get("SYSMON_SYNC_DIR", "").strip()
SYSMON_SYNC_PYTHON = os.environ.get("SYSMON_SYNC_PYTHON", "").strip()
CKA_DIR = os.environ.get("CKA_DIR", "").strip()
CKA_PYTHON = os.environ.get("CKA_PYTHON", "python3")
TODAY = "2026-11-24"

AGENT = "C:\\Program Files\\Fabrikam\\agent.exe"
HELPER = "C:\\Program Files\\Fabrikam\\helper.exe"
UPDATER = "C:\\Program Files\\Fabrikam\\updater.exe"
WMI = "C:\\Windows\\System32\\wbem\\WmiPrvSE.exe"
SYSTEM = "NT AUTHORITY\\SYSTEM"
TEMPLATE = (
    b'<Sysmon schemaversion="4.90">\n'
    b"  <EventFiltering>\n"
    b'    <RuleGroup name="" groupRelation="or">\n'
    b'      <ProcessCreate onmatch="exclude">\n'
    b'        <Image condition="begin with">C:\\Program Files\\__INSTALLDIRNAME__\\chainsaw\\</Image>\n'
    b"      </ProcessCreate>\n"
    b"    </RuleGroup>\n"
    b"  </EventFiltering>\n"
    b"</Sysmon>\n"
)

# The fake CoPilots: license key, customers (code -> name, install folder on its endpoints, how CoPilot knows it)
COPILOTS = {
    "A": {"key": "STATSA-11111-BBBBB-CCCCC", "customers": {"contoso": ("Contoso Ltd", "contoso", "code")}},
    "B": {"key": "STATSB-22222-BBBBB-CCCCC", "customers": {"northwind": ("Northwind Traders", "nwedr", "hint")}},
    "C": {
        "key": "STATSC-33333-BBBBB-CCCCC",
        "customers": {"tailspin": ("Tailspin Toys", "tailspin-edr", "discovered"), "wingtip": ("Wingtip Toys", "wingtip", "code")},
    },
}
WEEKS = {
    "2026-W46": ("2026-11-09", datetime(2026, 11, 18, 0, 30, tzinfo=timezone.utc)),
    "2026-W47": ("2026-11-16", datetime(2026, 11, 25, 0, 30, tzinfo=timezone.utc)),
}


def say(text):
    print(text, flush=True)


def fail(text):
    raise SystemExit(f"FAILED: {text}")


def docs_for(copilot, code, install_dir, monday):
    from tests.sysmon_stats_support import DAY_MS
    from tests.sysmon_stats_support import alert
    from tests.sysmon_stats_support import ms

    out = []
    start = ms(f"{monday}T09:00:00")
    for i in range(5):
        agent = f"{copilot}{code}-{i:03d}"
        host = f"{code.upper()[:4]}-WS{i:04d}"
        for day in range(7):
            ts = start + day * DAY_MS + i * 1000
            base = {"ts": ts, "agent": agent, "label": code}
            # P1
            out.append(
                alert(eid=22, Image=AGENT, QueryName="telemetry.fabrikam-example.com", QueryStatus="0", User=SYSTEM, RuleName="-", **base),
            )
            # P2: the same service account's profile on every endpoint
            out.append(
                alert(
                    eid=11,
                    Image=UPDATER,
                    TargetFilename="C:\\Users\\svc_fabupd\\AppData\\Local\\Fabrikam\\Updater\\update-helper.exe",
                    User=f"{code.upper()}\\svc_fabupd",
                    RuleName="-",
                    **base,
                ),
            )
            # P3: never with its command line, which is in the alert and must never be read
            out.append(
                alert(
                    eid=1,
                    Image=HELPER,
                    ParentImage=WMI,
                    CommandLine=f'"{HELPER}" --tenant {code} --token s3cr3t',
                    ParentCommandLine=f"{WMI} -secured -Embedding",
                    OriginalFileName="helper.exe",
                    IntegrityLevel="System",
                    User=SYSTEM,
                    RuleName="-",
                    **base,
                ),
            )
            # P5
            out.append(
                alert(
                    eid=3,
                    Image=AGENT,
                    DestinationHostname="api.fabrikam-example.com",
                    DestinationIp="203.0.113.10",
                    DestinationPort="443",
                    Protocol="tcp",
                    Initiated="true",
                    User=SYSTEM,
                    RuleName="-",
                    **base,
                ),
            )
            # P6: a detection
            out.append(alert(eid=22, level=10, Image="C:\\Windows\\Temp\\dropper.exe", QueryName="c2.example-bad.net", User=SYSTEM, **base))
            # P7: an internal name
            out.append(alert(eid=22, Image=AGENT, QueryName=f"fs01.{code}.local", User=SYSTEM, **base))
            # P8: the EDR's own install folder
            out.append(
                alert(
                    eid=1,
                    Image=f"C:\\Program Files\\{install_dir}\\chainsaw\\chainsaw.exe",
                    ParentImage="C:\\Windows\\System32\\svchost.exe",
                    User=SYSTEM,
                    RuleName="-",
                    **base,
                ),
            )
            # A per-endpoint file named after the host, and a person's account: neither may leave
            out.append(
                alert(
                    eid=11,
                    Image=AGENT,
                    TargetFilename=f"C:\\ProgramData\\Fabrikam\\Agent\\cache\\{host}.json",
                    User=f"{code.upper()}\\j.doe{i}",
                    **base,
                ),
            )
            if copilot == "A":
                # P4
                out.append(
                    alert(eid=22, Image=AGENT, QueryName="cdn-a.fabrikam-example.com", QueryStatus="0", User=SYSTEM, RuleName="-", **base),
                )
            if copilot in ("A", "B"):
                # P4b: two owners, one short of a global suggestion
                out.append(
                    alert(eid=22, Image=AGENT, QueryName="cdn-ab.fabrikam-example.com", QueryStatus="0", User=SYSTEM, RuleName="-", **base),
                )
    return out


async def build_copilot(name, spec, mp, audit_rows):
    import httpx
    from sqlalchemy import select

    from app.active_response.services.sysmon_stats import runner
    from app.db.universal_models import SysmonStatsCustomerSettings
    from app.db.universal_models import SysmonStatsIdentity
    from tests.sysmon_stats_support import World

    docs = []
    for code, (_, install_dir, _) in spec["customers"].items():
        for _, (monday, _) in WEEKS.items():
            docs += docs_for(name, code, install_dir, monday)
    stored = {}
    for code, (_, install_dir, how) in spec["customers"].items():
        if code == "northwind":
            stored[code] = TEMPLATE.replace(b"__INSTALLDIRNAME__", install_dir.encode()) + b"<!-- edited here -->\n"
        elif code != "wingtip":
            stored[code] = TEMPLATE.replace(b"__INSTALLDIRNAME__", install_dir.encode())
    world = World(mp, docs, stored_configs=stored)
    hosts = {code: [f"{code.upper()[:4]}-WS{i:04d}" for i in range(5)] for code in spec["customers"]}
    await world.setup({code: v[0] for code, v in spec["customers"].items()}, license_key=spec["key"], hostnames=hosts)
    world.minio.objects[("sysmon-config-defaults", "sysmon_config.xml")] = TEMPLATE
    crlf = TEMPLATE.replace(b"\n", b"\r\n")
    world.minio.objects[("sysmon-config-defaults", "sync.json")] = json.dumps(
        {
            "sequence": 56,
            "commit": "a" * 40,
            "content_sha256": hashlib.sha256(TEMPLATE).hexdigest(),
            "content_sha256_crlf": hashlib.sha256(crlf).hexdigest(),
        },
    ).encode()
    async with world.db.session() as s:
        for code, (_, install_dir, how) in spec["customers"].items():
            if how == "hint":
                s.add(SysmonStatsCustomerSettings(customer_code=code, sharing_enabled=True, install_dir_name=install_dir))
        await s.commit()
    captured = []

    async def handle(request):
        if request.url.path == "/v1/sysmon/report" and "authorization" in request.headers:
            captured.append(bytes(request.content))
            return httpx.Response(
                200,
                json={
                    "result": "stored",
                    "replaced": False,
                    "patterns": {"received": 0, "accepted": 0, "rejected": 0},
                    "rejected_by_reason": {},
                },
            )
        if request.url.path == "/v1/sysmon/report":
            return httpx.Response(401, json={"detail": "missing license key"})
        return httpx.Response(200, json={"result": "withdrawn", "reports_deleted": 0})

    reports = []
    for week, (_, now) in WEEKS.items():
        before = len(captured)
        async with world.db.session() as session:
            result = await runner.run_tick(session, now=now, transport=httpx.MockTransport(handle))
        if result.outcome.value != "completed" or any(c.outcome.value != "sent" for c in result.customers):
            fail(
                f"CoPilot {name} {week}: {result.outcome.value} {[(c.customer_code, c.outcome.value, c.message) for c in result.customers]}",
            )
        for raw in captured[before:]:
            doc = json.loads(raw)
            reports.append({"copilot": name, "week": week, "customer": doc["customer"], "raw": raw})
    async with world.db.session() as s:
        secret = (await s.execute(select(SysmonStatsIdentity.report_secret))).scalar_one()
    from app.active_response.services.sysmon_stats.identity import customer_pseudonym

    pseudonyms = {code: customer_pseudonym(bytes.fromhex(secret), code) for code in spec["customers"]}
    return reports, pseudonyms, world


def service_validator():
    root = Path(SYSMON_SYNC_DIR) / "app" / "reports"
    spec = importlib.util.spec_from_file_location("_sysmon_sync_reports", root / "__init__.py", submodule_search_locations=[str(root)])
    module = importlib.util.module_from_spec(spec)
    sys.modules["_sysmon_sync_reports"] = module
    spec.loader.exec_module(module)
    return importlib.import_module("_sysmon_sync_reports.contract")


def step1():
    import pytest

    from app.audit.services import audit as audit_service

    say("Step 1: three fake CoPilots build their W46 and W47 reports with the real tick")
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    manifest = {"copilots": {}, "reports": []}
    audit_rows = []
    all_reports = []
    for name, spec in COPILOTS.items():
        mp = pytest.MonkeyPatch()

        async def persist(entries):
            audit_rows.extend(entries)

        mp.setattr(audit_service, "_persist", persist)
        try:
            reports, pseudonyms, _ = asyncio.run(build_copilot(name, spec, mp, audit_rows))
        finally:
            mp.undo()
        manifest["copilots"][name] = {"license_key": spec["key"], "pseudonyms": pseudonyms}
        for i, item in enumerate(reports):
            file = f"report-{name}-{item['week']}-{i}.json"
            (WORK / file).write_bytes(item["raw"])
            manifest["reports"].append(
                {"copilot": name, "license_key": spec["key"], "week": item["week"], "customer": item["customer"], "file": file},
            )
            all_reports.append((name, item))
    (WORK / "manifest.json").write_text(json.dumps(manifest, indent=1))
    say(f"  {len(all_reports)} reports written to {WORK}")

    # Local assertions on the exact bytes
    contract = service_validator()
    forbidden = [spec["key"] for spec in COPILOTS.values()]
    for spec in COPILOTS.values():
        for code, (cname, _, _) in spec["customers"].items():
            forbidden += [code, cname, code.upper()[:4] + "-WS"]
    forbidden += ["s3cr3t", "--tenant", "203.0.113.10", "svc_fabupd", "j.doe", "-Embedding"]
    p8 = 0
    for name, item in all_reports:
        raw = item["raw"]
        text = raw.decode("utf-8")
        for word in forbidden:
            if word.lower() in text.lower():
                fail(f"a report of CoPilot {name} holds {word!r}")
        if "c2.example-bad.net" in text or ".local" in text:
            fail(f"a report of CoPilot {name} holds P6 or P7")
        if "CommandLine" in text or "DestinationIp" in text:
            fail(f"a report of CoPilot {name} holds a command line or a destination IP")
        doc = contract.strict_loads(raw)
        parsed = contract.validate_report(doc)
        if parsed.rejected:
            fail(f"sysmon-sync's validator dropped patterns of CoPilot {name}: {[p.to_json() for p in parsed.rejected]}")
        p8 += sum(1 for p in doc["patterns"] if p["fields"].get("Image") == "C:\\Program Files\\__INSTALLDIRNAME__\\chainsaw\\chainsaw.exe")
    if p8 != len(all_reports):
        fail(f"P8 (the install folder as __INSTALLDIRNAME__) is in {p8} of {len(all_reports)} reports")
    for row in audit_rows:
        blob = json.dumps(row.model_dump(), default=str)
        if any(spec["key"] in blob for spec in COPILOTS.values()) or "fabrikam-example" in blob:
            fail("an audit row holds a license key or a value")
    say(f"  local checks passed: no identity, P6/P7 absent, P8 tokenized in every report, {len(audit_rows)} audit rows without values")
    return manifest


def step2():
    say("Step 2: sysmon-sync's in-process harness receives the exact bytes")
    driver = Path(__file__).with_name("sysmon_stats_sysmon_sync_driver.py")
    sqlite_tmp = WORK / "sqlite-tmp"
    sqlite_tmp.mkdir(exist_ok=True)
    proc = subprocess.run(
        [SYSMON_SYNC_PYTHON, "-I", str(driver), str(WORK)],
        cwd=SYSMON_SYNC_DIR,
        env={**os.environ, "SYSMON_SYNC_DIR": SYSMON_SYNC_DIR, "SQLITE_TMPDIR": str(sqlite_tmp)},
        capture_output=True,
        text=True,
        timeout=600,
    )
    if proc.returncode != 0:
        fail(f"the sysmon-sync driver failed:\n{proc.stdout[-4000:]}\n{proc.stderr[-4000:]}")
    for line in proc.stdout.splitlines():
        say(f"  {line}")
    return json.loads((WORK / "service-results.json").read_text())


CANDIDATE_NAMES = {
    ("QueryName", "telemetry.fabrikam-example.com"): "P1",
    ("TargetFilename", "C:\\Users\\<user>\\AppData\\Local\\Fabrikam\\Updater\\update-helper.exe"): "P2",
    ("ParentImage", WMI): "P3",
    ("QueryName", "cdn-a.fabrikam-example.com"): "P4",
    ("QueryName", "cdn-ab.fabrikam-example.com"): "P4b",
    ("DestinationHostname", "api.fabrikam-example.com"): "P5",
    ("Image", "C:\\Program Files\\__INSTALLDIRNAME__\\chainsaw\\chainsaw.exe"): "P8",
}


def step3():
    say("Step 3: the installer repo's suggest check on the candidates")
    path = WORK / "candidates.json"
    text = path.read_text()
    for word in ["cust_"] + [spec["key"] for spec in COPILOTS.values()] + ["contoso", "northwind", "tailspin", "wingtip", "-WS0"]:
        if word.lower() in text.lower():
            fail(f"candidates.json holds {word!r}")
    doc = json.loads(text)
    by_name = {}
    for cand in doc["candidates"]:
        for (field, value), name in CANDIDATE_NAMES.items():
            if cand["fields"].get(field) == value:
                by_name[name] = cand
    missing = {"P1", "P2", "P3", "P4", "P4b", "P5", "P8"} - set(by_name)
    if missing:
        fail(f"candidates missing: {sorted(missing)}")
    if "CommandLine" not in by_name["P3"]["absent"]:
        fail("P3 does not list its CommandLine as absent")
    audit = WORK / "audit.json"
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=CKA_DIR, capture_output=True, text=True).stdout.strip()
    proc = subprocess.run(
        [CKA_PYTHON, "-m", "tools.sysmonctl", "suggest", "check", "--candidates", str(path), "--out", str(audit), "--today", TODAY],
        cwd=CKA_DIR,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if proc.returncode != 0:
        fail(f"suggest check exited {proc.returncode}:\n{proc.stdout[-3000:]}\n{proc.stderr[-3000:]}")
    result = json.loads(audit.read_text())
    counts = result["counts"]
    if counts.get("invalid") != 0:
        fail(f"invalid candidates: {counts}")
    outcomes = {}
    for r in result["results"]:
        name = next((n for n, c in by_name.items() if c["candidate_id"] == r["candidate_id"]), None)
        if name:
            outcomes[name] = (r["outcome"], r.get("gate"), r["reason"])
    say(f"  CKA {head}: counts {counts}")
    for name in sorted(outcomes):
        say(f"  {name}: {outcomes[name]}")
    expect = {"P1": ("survivor", "global"), "P4b": ("deferred", "below-threshold")}
    for name, (outcome, reason) in expect.items():
        if (outcomes[name][0], outcomes[name][2]) != (outcome, reason):
            fail(f"{name}: expected {outcome}/{reason}, got {outcomes[name]}")
    # One owner only: CKA (c626507) reads it as one customer's pattern that sysmon/fleet.toml does not know, and drops it;
    # with two or more owners below the threshold it is deferred (P4b). Never a suggestion either way.
    if (outcomes["P4"][0], outcomes["P4"][2]) not in (("dropped", "unknown-customer"), ("deferred", "below-threshold")):
        fail(f"P4: expected not to be suggested, got {outcomes['P4']}")
    if outcomes["P2"][0] != "dropped" or outcomes["P2"][1] != "deny":
        fail(f"P2: expected dropped at the deny gate, got {outcomes['P2']}")
    if (outcomes["P3"][0], outcomes["P3"][2]) not in (("needs_person", "processcreate-never-drafted"), ("dropped", "baseline-incomplete")):
        fail(f"P3: expected needs_person/processcreate-never-drafted, got {outcomes['P3']}")
    return outcomes, counts, head


def step4(service):
    import httpx

    from app.active_response.services.sysmon_stats import client as http

    say("Step 4: sysmon-sync's answers back through CoPilot's classifier")

    def probe(answer):
        transport = httpx.MockTransport(lambda request: httpx.Response(answer["status"], json=answer["body"]))
        return asyncio.run(http.probe("https://sync.test", transport))

    off, on = probe(service["probe_disabled"]), probe(service["probe_enabled"])
    if (off, on) != (http.Probe.NOT_ACCEPTING, http.Probe.ACCEPTING):
        fail(f"probe classified as {off}, {on}")
    refused = service["unredacted"]
    result = http.classify_report(http.Answer(status=refused["status"], body=refused["body"]))
    if not (result.outcome.value == "refused" and result.latch and result.reason == "identity-leak"):
        fail(f"the 422 was classified as {result}")
    withdrawn = service["repost_after_withdraw"]
    result409 = http.classify_report(http.Answer(status=withdrawn["status"], body=withdrawn["body"]))
    if result409.outcome.value != "withdrawn" or not result409.terminal:
        fail(f"the 409 was classified as {result409}")
    say(f"  probe: reports off -> {off}, on -> {on}; 422 identity-leak -> {result.outcome.value} + pause; 409 -> {result409.outcome.value}")


def main():
    if not (SYSMON_SYNC_DIR and SYSMON_SYNC_PYTHON and CKA_DIR):
        say("SKIPPED: set SYSMON_SYNC_DIR, SYSMON_SYNC_PYTHON and CKA_DIR")
        return 0
    from loguru import logger

    logger.remove()
    logger.add(sys.stderr, level="WARNING")
    step1()
    service = step2()
    outcomes, counts, head = step3()
    step4(service)
    summary = {
        "cka_head": head,
        "counts": counts,
        "outcomes": {k: list(v) for k, v in outcomes.items()},
        "reports": len(json.loads((WORK / "manifest.json").read_text())["reports"]),
    }
    (WORK / "summary.json").write_text(json.dumps(summary, indent=1))
    say(f"PASSED: {json.dumps(summary)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
