import asyncio
import os
from datetime import datetime
from datetime import timedelta
from typing import Optional

import httpx
from loguru import logger

from app.integrations.copilot_searches.schema.copilot_searches import PlatformFilter
from app.integrations.copilot_searches.schema.copilot_searches import RuleSeverity
from app.integrations.copilot_searches.schema.copilot_searches import RuleStatus
from app.integrations.copilot_searches.services.copilot_searches import rules_cache

MITRE_STIX_URL = "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/enterprise-attack/enterprise-attack.json"
MITRE_CACHE_TTL_HOURS = 24


class MitreMatrix:
    """In-memory cache of the MITRE ATT&CK Enterprise matrix structure.

    Pulls the official STIX bundle from mitre/cti and indexes tactics + techniques
    so we can cross-reference them against CoPilot Search rules.
    """

    def __init__(self) -> None:
        self._tactics: list[dict] = []
        self._techniques: dict[str, dict] = {}
        self._last_refresh: Optional[datetime] = None
        self._lock = asyncio.Lock()

    @property
    def is_stale(self) -> bool:
        if self._last_refresh is None:
            return True
        return datetime.utcnow() - self._last_refresh > timedelta(hours=MITRE_CACHE_TTL_HOURS)

    async def ensure_loaded(self) -> None:
        if self.is_stale:
            await self.refresh()

    async def refresh(self) -> None:
        async with self._lock:
            logger.info(f"Fetching MITRE ATT&CK Enterprise STIX bundle from {MITRE_STIX_URL}")
            headers = {}
            token = os.getenv("GITHUB_TOKEN")
            if token:
                headers["Authorization"] = f"Bearer {token}"

            async with httpx.AsyncClient(timeout=120.0, headers=headers) as client:
                response = await client.get(MITRE_STIX_URL)
                response.raise_for_status()
                bundle = response.json()

            self._parse_bundle(bundle)
            self._last_refresh = datetime.utcnow()
            logger.info(
                f"Loaded MITRE matrix: {len(self._tactics)} tactics, {len(self._techniques)} techniques",
            )

    def _parse_bundle(self, bundle: dict) -> None:
        tactics_by_short: dict[str, dict] = {}
        techniques: dict[str, dict] = {}

        for obj in bundle.get("objects", []):
            obj_type = obj.get("type")

            if obj.get("revoked") or obj.get("x_mitre_deprecated"):
                continue

            if obj_type == "x-mitre-tactic":
                external_id = self._get_external_id(obj)
                short_name = obj.get("x_mitre_shortname", "")
                if not external_id or not short_name:
                    continue
                tactics_by_short[short_name] = {
                    "id": external_id,
                    "name": obj.get("name", ""),
                    "short_name": short_name,
                    "url": self._get_external_url(obj),
                    "description": obj.get("description", ""),
                }

            elif obj_type == "attack-pattern":
                external_id = self._get_external_id(obj)
                if not external_id:
                    continue
                tactic_short_names = [
                    phase.get("phase_name", "")
                    for phase in obj.get("kill_chain_phases", [])
                    if phase.get("kill_chain_name") == "mitre-attack"
                ]
                techniques[external_id] = {
                    "id": external_id,
                    "name": obj.get("name", ""),
                    "url": self._get_external_url(obj),
                    "is_subtechnique": bool(obj.get("x_mitre_is_subtechnique")),
                    "tactic_short_names": tactic_short_names,
                }

        # Order tactics by the canonical kill-chain order. The STIX bundle stores
        # the official ordering in the matrix object's tactic_refs; we approximate
        # with the conventional order here as a fallback.
        canonical_order = [
            "reconnaissance",
            "resource-development",
            "initial-access",
            "execution",
            "persistence",
            "privilege-escalation",
            "defense-evasion",
            "credential-access",
            "discovery",
            "lateral-movement",
            "collection",
            "command-and-control",
            "exfiltration",
            "impact",
        ]
        ordered_tactics: list[dict] = []
        for short in canonical_order:
            if short in tactics_by_short:
                ordered_tactics.append(tactics_by_short[short])
        # Append any tactics not in the canonical list (forward-compat)
        for short, t in tactics_by_short.items():
            if short not in canonical_order:
                ordered_tactics.append(t)

        self._tactics = ordered_tactics
        self._techniques = techniques

    @staticmethod
    def _get_external_id(obj: dict) -> str:
        for ref in obj.get("external_references", []):
            if ref.get("source_name") == "mitre-attack":
                return ref.get("external_id", "")
        return ""

    @staticmethod
    def _get_external_url(obj: dict) -> str:
        for ref in obj.get("external_references", []):
            if ref.get("source_name") == "mitre-attack":
                return ref.get("url", "")
        return ""

    @property
    def tactics(self) -> list[dict]:
        return self._tactics

    @property
    def techniques(self) -> dict[str, dict]:
        return self._techniques


mitre_matrix = MitreMatrix()


def _rule_matches_filters(
    rule: dict,
    platform: Optional[PlatformFilter],
    severity: Optional[RuleSeverity],
    status: Optional[RuleStatus],
    has_graylog: Optional[bool],
    search: Optional[str],
) -> bool:
    if platform is not None and platform != PlatformFilter.ALL:
        if rule.get("_platform", "unknown") != platform.value:
            return False
    if severity is not None:
        if rule.get("response", {}).get("severity", "").lower() != severity.value:
            return False
    if status is not None:
        if rule.get("status", "").lower() != status.value:
            return False
    if has_graylog is not None:
        if rule.get("_has_graylog", False) != has_graylog:
            return False
    if search:
        s = search.lower()
        name = rule.get("name", "").lower()
        desc = rule.get("description", "").lower()
        if s not in name and s not in desc:
            return False
    return True


async def get_coverage(
    platform: Optional[PlatformFilter] = None,
    severity: Optional[RuleSeverity] = None,
    status: Optional[RuleStatus] = None,
    has_graylog: Optional[bool] = None,
    search: Optional[str] = None,
) -> dict:
    """Build the MITRE coverage map by cross-referencing rules against the matrix.

    Optional filters narrow the rules considered (platform/severity/status/has_graylog/search)
    so the matrix can show "Windows-only coverage", etc.

    Returns a payload shaped for the frontend matrix view: ordered tactic columns,
    techniques grouped under each tactic, per-technique rule counts + IDs with
    sub-techniques nested, and a flat `rules_index` mapping rule ID to a small
    summary (name, severity, platform, has_graylog) for hover previews.
    """
    await mitre_matrix.ensure_loaded()
    await rules_cache.ensure_loaded()

    # Map base technique -> {rule_ids set, subtechniques: {sub_id -> rule_ids set}}
    coverage: dict[str, dict] = {}
    rules_index: dict[str, dict] = {}

    for rule in rules_cache.get_all_rules():
        rule_id = rule.get("id", "")
        if not rule_id:
            continue
        if not _rule_matches_filters(rule, platform, severity, status, has_graylog, search):
            continue

        # Cap data_sources at 3 to keep payload small; full list is in /id/{rule_id}.
        ds = rule.get("data_source", []) or []
        rules_index[rule_id] = {
            "id": rule_id,
            "name": rule.get("name", ""),
            "severity": rule.get("response", {}).get("severity", "medium"),
            "platform": rule.get("_platform", "unknown"),
            "has_graylog": rule.get("_has_graylog", False),
            "data_sources": [s for s in ds if isinstance(s, str)][:3],
        }

        for raw_tid in rule.get("tags", {}).get("mitre_attack_id", []) or []:
            tid = raw_tid.strip().upper()
            if not tid.startswith("T"):
                continue
            base = tid.split(".")[0]
            entry = coverage.setdefault(base, {"rule_ids": set(), "subtechniques": {}})
            if "." in tid:
                sub = entry["subtechniques"].setdefault(tid, set())
                sub.add(rule_id)
            else:
                entry["rule_ids"].add(rule_id)

    # Build tactic-column structure
    techniques_meta = mitre_matrix.techniques
    tactics_out: list[dict] = []

    for tactic in mitre_matrix.tactics:
        techniques_in_tactic: list[dict] = []
        for tid, meta in techniques_meta.items():
            if meta["is_subtechnique"]:
                continue
            if tactic["short_name"] not in meta["tactic_short_names"]:
                continue

            cov = coverage.get(tid, {"rule_ids": set(), "subtechniques": {}})
            base_rule_ids = sorted(cov["rule_ids"])
            sub_entries: list[dict] = []
            total_with_subs = set(cov["rule_ids"])

            for sub_tid, sub_meta in techniques_meta.items():
                if not sub_meta["is_subtechnique"]:
                    continue
                if not sub_tid.startswith(tid + "."):
                    continue
                sub_rule_ids = sorted(cov["subtechniques"].get(sub_tid, set()))
                total_with_subs.update(sub_rule_ids)
                sub_entries.append(
                    {
                        "id": sub_tid,
                        "name": sub_meta["name"],
                        "url": sub_meta["url"],
                        "rule_count": len(sub_rule_ids),
                        "rule_ids": sub_rule_ids,
                    },
                )
            sub_entries.sort(key=lambda s: s["id"])

            techniques_in_tactic.append(
                {
                    "id": tid,
                    "name": meta["name"],
                    "url": meta["url"],
                    "rule_count": len(base_rule_ids),
                    "rule_ids": base_rule_ids,
                    "total_rule_count": len(total_with_subs),
                    "subtechniques": sub_entries,
                },
            )

        techniques_in_tactic.sort(key=lambda t: t["id"])

        tactics_out.append(
            {
                "id": tactic["id"],
                "name": tactic["name"],
                "short_name": tactic["short_name"],
                "url": tactic["url"],
                "techniques": techniques_in_tactic,
            },
        )

    total_techniques = sum(len(t["techniques"]) for t in tactics_out)
    covered_techniques = sum(1 for t in tactics_out for tech in t["techniques"] if tech["total_rule_count"] > 0)

    return {
        "success": True,
        "message": "MITRE coverage built successfully",
        "tactics": tactics_out,
        "rules_index": rules_index,
        "stats": {
            "total_tactics": len(tactics_out),
            "total_techniques": total_techniques,
            "covered_techniques": covered_techniques,
            "total_rules": len(rules_index),
            "matrix_last_refreshed": mitre_matrix._last_refresh,
            "rules_last_refreshed": rules_cache.last_refresh,
        },
    }
