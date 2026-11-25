"""Step 2 of tests/e2e/sysmon_stats_e2e.py, run by sysmon-sync's own Python with cwd=SYSMON_SYNC_DIR: its in-process
harness (tests.helpers.Harness, a fake clock and license server) receives the reports CoPilot built, byte for byte.

    SYSMON_SYNC_DIR=... $SYSMON_SYNC_PYTHON -I tests/e2e/sysmon_stats_sysmon_sync_driver.py /tmp/stats-e2e

Writes service-results.json (each answer's status and JSON) and candidates.json into the work directory.
"""
import json
import os
import sys
from datetime import datetime
from datetime import timezone
from pathlib import Path

SYSMON_SYNC_DIR = os.environ["SYSMON_SYNC_DIR"]
sys.path.insert(0, SYSMON_SYNC_DIR)

from tests.helpers import Harness  # noqa: E402
from tests.reports_helpers import candidates as get_candidates  # noqa: E402
from tests.reports_helpers import paid_license  # noqa: E402
from tests.reports_helpers import post_report  # noqa: E402
from tests.reports_helpers import reports_env  # noqa: E402
from tests.reports_helpers import seed  # noqa: E402
from tests.reports_helpers import withdraw  # noqa: E402


def ts(text):
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp()


def answer(response):
    try:
        body = response.json()
    except ValueError:
        body = None
    return {"status": response.status_code, "body": body}


def main(work: Path) -> int:
    manifest = json.loads((work / "manifest.json").read_text())
    (work / "service").mkdir(parents=True, exist_ok=True)
    harness = Harness(work / "service")
    keys = []
    for i, (name, info) in enumerate(sorted(manifest["copilots"].items())):
        paid_license(harness, info["license_key"], 101 + i)
        keys.append(info["license_key"])
    env = reports_env()
    # Each CoPilot polled GET /v1/sysmon/default 60 days before: an environment old enough to count
    seed(harness, keys, days_before=60, **env)
    harness.clock.now = ts("2026-11-24T09:00:00")
    results = {}

    # (i) The probe CoPilot sends (no license key, an empty body): reports off, then on
    with harness.client(REPORT_ID_KEY=env["REPORT_ID_KEY"]) as c:
        results["probe_disabled"] = answer(c.post("/v1/sysmon/report", content=b"{}", headers={"Content-Type": "application/json"}))
    assert results["probe_disabled"] == {"status": 404, "body": {"detail": "reports are not enabled"}}, results["probe_disabled"]

    with harness.client(**env) as c:
        results["probe_enabled"] = answer(c.post("/v1/sysmon/report", content=b"{}", headers={"Content-Type": "application/json"}))
        assert results["probe_enabled"]["status"] == 401, results["probe_enabled"]

        # (ii) Every report, as the exact bytes CoPilot built
        results["reports"] = []
        for item in manifest["reports"]:
            raw = (work / item["file"]).read_bytes()
            r = post_report(c, None, item["license_key"], raw=raw)
            got = answer(r)
            results["reports"].append({**{k: item[k] for k in ("copilot", "week", "file")}, **got})
            assert r.status_code == 200, (item["file"], r.text)
            assert got["body"]["patterns"]["rejected"] == 0, (item["file"], got["body"])
        print(f"{len(manifest['reports'])} reports stored, none rejected")

        # (iii) C's second customer opts out: withdraw, then a report right after it is dropped
        c_info = manifest["copilots"]["C"]
        second = c_info["pseudonyms"]["wingtip"]
        r = withdraw(c, c_info["license_key"], second)
        results["withdraw"] = answer(r)
        assert r.status_code == 200 and r.json()["reports_deleted"] >= 1, r.text
        repost = next(item for item in manifest["reports"] if item["customer"] == second)
        r = post_report(c, None, c_info["license_key"], raw=(work / repost["file"]).read_bytes())
        results["repost_after_withdraw"] = answer(r)
        assert r.status_code == 409 and r.json()["reason"] == "withdrawn", r.text
        print(f"withdraw of C's second customer deleted {results['withdraw']['body']['reports_deleted']} report(s); a repost answered 409")

        # (iv) A report CoPilot's redactor would never build: a profile folder left in
        first = manifest["reports"][0]
        doc = json.loads((work / first["file"]).read_bytes())
        doc["customer"] = "cust_" + "d" * 32
        doc["patterns"].append(
            {
                "event_id": 11,
                "fields": {"Image": "C:\\Program Files\\Fabrikam\\agent.exe", "TargetFilename": "C:\\Users\\jdoe\\AppData\\Local\\x.tmp"},
                "events": 9,
                "endpoints": 3,
                "days": 1,
            },
        )
        r = post_report(c, doc, first["license_key"])
        results["unredacted"] = answer(r)
        assert r.status_code == 422 and r.json()["reason"] == "identity-leak", r.text
        print("an unredacted report answered 422 identity-leak")

        # (v) The candidates the installer repo's weekly workflow fetches
        r = get_candidates(c, "weeks=4")
        assert r.status_code == 200, r.text
        (work / "candidates.json").write_bytes(r.content)
        print(f"{len(r.json()['candidates'])} candidates")

    (work / "service-results.json").write_text(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
