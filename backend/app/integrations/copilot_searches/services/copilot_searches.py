import asyncio
import copy
import json
import os
import re
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Optional

import httpx
import yaml
from loguru import logger
from pydantic import ValidationError


def _github_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _custom_repo_headers(token: Optional[str]) -> dict[str, str]:
    """Headers for a per-tenant custom repo — its own read token when provided,
    otherwise fall back to the shared GITHUB_TOKEN (rate-limit / public access)."""
    headers = {"Accept": "application/vnd.github+json"}
    tok = token or os.getenv("GITHUB_TOKEN")
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    return headers


from app.connectors.wazuh_indexer.utils.universal import (
    create_wazuh_indexer_client_async,
)
from app.integrations.copilot_searches.schema.copilot_searches import AggregationConfig
from app.integrations.copilot_searches.schema.copilot_searches import (
    AggregationFunction,
)
from app.integrations.copilot_searches.schema.copilot_searches import (
    ExecuteGraylogQueryRequest,
)
from app.integrations.copilot_searches.schema.copilot_searches import (
    ExecuteSearchRequest,
)
from app.integrations.copilot_searches.schema.copilot_searches import (
    ExecuteSearchResponse,
)
from app.integrations.copilot_searches.schema.copilot_searches import GraylogQuery
from app.integrations.copilot_searches.schema.copilot_searches import (
    GraylogQueryResponse,
)
from app.integrations.copilot_searches.schema.copilot_searches import ParameterSchema
from app.integrations.copilot_searches.schema.copilot_searches import PlatformFilter
from app.integrations.copilot_searches.schema.copilot_searches import (
    ProvisionGraylogAlertRequest,
)
from app.integrations.copilot_searches.schema.copilot_searches import (
    ProvisionGraylogAlertResponse,
)
from app.integrations.copilot_searches.schema.copilot_searches import RuleDetail
from app.integrations.copilot_searches.schema.copilot_searches import RuleSeverity
from app.integrations.copilot_searches.schema.copilot_searches import RuleStatus
from app.integrations.copilot_searches.schema.copilot_searches import RuleSummary
from app.integrations.copilot_searches.schema.copilot_searches import SearchHit
from app.integrations.copilot_searches.schema.copilot_searches import (
    SearchValidationError,
)
from app.integrations.copilot_searches.services.cache_support import (
    BackgroundRefreshMixin,
)
from app.integrations.monitoring_alert.schema.provision import (
    GraylogAlertProvisionConfig,
)
from app.integrations.monitoring_alert.schema.provision import (
    GraylogAlertProvisionFieldSpecItem,
)
from app.integrations.monitoring_alert.schema.provision import (
    GraylogAlertProvisionModel,
)
from app.integrations.monitoring_alert.schema.provision import (
    GraylogAlertProvisionNotificationSettings,
)
from app.integrations.monitoring_alert.schema.provision import (
    GraylogAlertProvisionProvider,
)
from app.integrations.monitoring_alert.services.provision import (
    provision_alert_definition,
)

# =============================================================================
# Configuration
# =============================================================================

GITHUB_REPO = "socfortress/CoPilot-Search-Queries"
GITHUB_BRANCH = "main"
GITHUB_API_BASE = "https://api.github.com"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com"

# Cache settings
CACHE_TTL_MINUTES = 30


# =============================================================================
# Detection categories
# =============================================================================
#
# The CoPilot-Search-Queries repo is laid out as detections/<source_folder>/<rule>.yaml
# — the folder IS the log source a detection reads (see
# https://github.com/socfortress/CoPilot-Search-Queries/tree/main/detections).
# `_category` is that folder verbatim, which makes it the one filter dimension
# that can never drift from the repo: new folder upstream = new filter option on
# the next cache refresh, no code change. Contrast `_platform` below, which is a
# best-effort OS guess kept only for the rule badge and the /linux, /windows,
# /powershell convenience routes.

DETECTIONS_ROOT = "detections"
UNCATEGORIZED = "uncategorized"

# Folders whose auto-humanized label would read badly. Everything else goes
# through _humanize_category (underscores -> spaces, title case, EID uppercase).
CATEGORY_LABEL_OVERRIDES = {
    "entra_id": "Entra ID",
    "sharepoint_onedrive": "SharePoint / OneDrive",
    "eid_12_13_14_registry_events": "EID 12/13/14 Registry Events",
    "eid_17_18_pipe_events": "EID 17/18 Pipe Events",
    "eid_19_20_21_wmi_events": "EID 19/20/21 WMI Events",
    "eid_23_26_file_delete": "EID 23/26 File Delete",
    "eid_27_28_29_file_block": "EID 27/28/29 File Block",
    "eid_22_dns_query": "EID 22 DNS Query",
    "eid_15_file_create_stream_hash": "EID 15 File Create Stream Hash",
    "eid_16_sysmon_config_changed": "EID 16 Sysmon Config Changed",
    "web": "Web",
}

# Grouping is presentation only — it buckets the ~33 folders so the dropdown
# stays scannable. Membership is by folder name; anything unrecognised (a folder
# added upstream after this list was written) lands in "Other" and still works.
GROUP_SYSMON = "Sysmon"
GROUP_WINDOWS_LOGS = "Windows Event Logs"
GROUP_POWERSHELL = "PowerShell"
GROUP_LINUX = "Linux"
GROUP_M365 = "Microsoft 365"
GROUP_OTHER = "Other"

CATEGORY_GROUP_ORDER = [
    GROUP_SYSMON,
    GROUP_WINDOWS_LOGS,
    GROUP_POWERSHELL,
    GROUP_LINUX,
    GROUP_M365,
    GROUP_OTHER,
]

POWERSHELL_CATEGORIES = {"eid_4103_module_logging", "eid_4104_script_block_logging"}
WINDOWS_LOG_CATEGORIES = {
    "application_eventlog",
    "security_eventlog",
    "system_eventlog",
    "defender_operational",
    "task_scheduler_operational",
}
LINUX_CATEGORIES = {"auditd", "syslog", "tetragon"}
M365_CATEGORIES = {"entra_id", "exchange", "sharepoint_onedrive"}


def _humanize_category(folder: str) -> str:
    """Turn a folder name into a display label ('eid_01_process_creation' -> 'EID 01 Process Creation')."""
    words = folder.replace("-", "_").split("_")
    return " ".join("EID" if w.lower() == "eid" else w.capitalize() if w.islower() or w.isupper() else w for w in words if w)


def category_label(folder: str) -> str:
    """Display label for a detections/ folder."""
    return CATEGORY_LABEL_OVERRIDES.get(folder.lower(), _humanize_category(folder))


def category_group(folder: str) -> str:
    """Presentation bucket for a detections/ folder."""
    key = folder.lower()
    if key in POWERSHELL_CATEGORIES:
        return GROUP_POWERSHELL
    if key.startswith("eid_"):
        return GROUP_SYSMON
    if key in WINDOWS_LOG_CATEGORIES:
        return GROUP_WINDOWS_LOGS
    if key in LINUX_CATEGORIES:
        return GROUP_LINUX
    if key in M365_CATEGORIES:
        return GROUP_M365
    return GROUP_OTHER


def category_from_path(file_path: str) -> str:
    """Extract the detections/<folder>/ segment from a rule's repo path."""
    parts = file_path.strip("/").split("/")
    if len(parts) >= 3 and parts[0] == DETECTIONS_ROOT:
        return parts[1]
    return UNCATEGORIZED


# =============================================================================
# Rules Cache
# =============================================================================


class RulesCache(BackgroundRefreshMixin):
    """
    In-memory cache for detection rules fetched from GitHub.

    Handles fetching, parsing, and caching YAML rules from the repository.
    """

    def __init__(self):
        self._rules: dict[str, dict] = {}  # id -> rule data
        self._rules_by_name: dict[str, str] = {}  # normalized name -> id
        self._last_refresh: Optional[datetime] = None
        self._lock = asyncio.Lock()
        # Per-source fetch outcome from the last refresh, so a broken custom repo
        # (revoked token, renamed repo) is visible in the UI instead of its rules
        # just silently vanishing. [{repo, provenance, owner, ok, rules_loaded, error, fetched_at}]
        self._source_status: list[dict] = []

    @property
    def source_status(self) -> list[dict]:
        """Fetch outcome per repo source from the last refresh."""
        return list(self._source_status)

    @property
    def is_stale(self) -> bool:
        """Check if cache needs refresh."""
        if self._last_refresh is None:
            return True
        age = datetime.utcnow() - self._last_refresh
        return age > timedelta(minutes=CACHE_TTL_MINUTES)

    @property
    def cache_age_minutes(self) -> Optional[float]:
        """Get cache age in minutes."""
        if self._last_refresh is None:
            return None
        age = datetime.utcnow() - self._last_refresh
        return age.total_seconds() / 60

    @property
    def last_refresh(self) -> Optional[datetime]:
        """Get last refresh timestamp."""
        return self._last_refresh

    @property
    def rules_count(self) -> int:
        """Get number of cached rules."""
        return len(self._rules)

    async def ensure_loaded(self):
        """Ensure rules are loaded, refreshing if stale."""
        if self.is_stale:
            await self.refresh()

    async def refresh(self) -> int:
        """
        Refresh rules cache from GitHub repository.

        Returns:
            Number of rules loaded
        """
        async with self._lock:
            logger.info("Refreshing rules cache from GitHub...")

            rules = await self._fetch_all_rules()

            self._rules = {}
            self._rules_by_name = {}

            for rule in rules:
                rule_id = rule.get("id", "")
                rule_name = rule.get("name", "")

                # Catalog is loaded first; a custom repo re-using an id must not
                # silently clobber the canonical rule. Keep the first, warn on dupes.
                if rule_id and rule_id in self._rules:
                    logger.warning(
                        f"Duplicate rule id {rule_id} from {rule.get('_provenance')} repo "
                        f"(owner={rule.get('_owner_customer_code')}) — keeping the first, skipping this one.",
                    )
                    continue

                self._rules[rule_id] = rule

                # Index by normalized name for lookup
                normalized_name = self._normalize_name(rule_name)
                self._rules_by_name[normalized_name] = rule_id

            self._last_refresh = datetime.utcnow()
            logger.info(f"Loaded {len(self._rules)} rules from GitHub")

            return len(self._rules)

    async def _build_sources(self) -> list[dict]:
        """The repos to pull: the canonical catalog first, then each configured
        per-tenant custom repo (from MinIO). Catalog first so it wins id collisions."""
        sources: list[dict] = [
            {
                "repo": GITHUB_REPO,
                "branch": GITHUB_BRANCH,
                "headers": _github_headers(),
                "provenance": "catalog",
                "owner": None,
            },
        ]
        try:
            from app.integrations.copilot_searches.services.custom_repos import (
                list_custom_repos,
            )

            for cfg in await list_custom_repos():
                if cfg.get("enabled") and cfg.get("repo"):
                    sources.append(
                        {
                            "repo": cfg["repo"],
                            "branch": cfg.get("branch") or "main",
                            "headers": _custom_repo_headers(cfg.get("token")),
                            "provenance": "custom",
                            "owner": cfg.get("customer_code"),
                        },
                    )
        except Exception as e:  # noqa: BLE001 — a bad custom config must not break the catalog
            logger.warning(f"Could not load custom repo configs: {e}")
        return sources

    async def _fetch_all_rules(self) -> list[dict]:
        """Fetch YAML rules from the canonical catalog + every configured custom repo."""
        rules: list[dict] = []
        statuses: list[dict] = []
        for src in await self._build_sources():
            entry = {
                "repo": src["repo"],
                "provenance": src["provenance"],
                "owner": src.get("owner"),
                "fetched_at": datetime.utcnow().isoformat() + "Z",
            }
            try:
                repo_rules = await self._fetch_repo_rules(src)
                rules.extend(repo_rules)
                entry.update(ok=True, rules_loaded=len(repo_rules), error=None)
                logger.info(f"Loaded {len(repo_rules)} {src['provenance']} rules from {src['repo']}")
            except Exception as e:  # noqa: BLE001 — one repo failing must not sink the rest
                entry.update(ok=False, rules_loaded=0, error=str(e))
                logger.warning(f"Failed to fetch rules from {src['repo']}: {e}")
            statuses.append(entry)
        self._source_status = statuses
        return rules

    async def _fetch_repo_rules(self, src: dict) -> list[dict]:
        """Fetch all detection YAMLs from a single repo source (catalog or custom)."""
        rules: list[dict] = []
        async with httpx.AsyncClient(timeout=30.0, headers=src["headers"]) as client:
            tree_url = f"{GITHUB_API_BASE}/repos/{src['repo']}/git/trees/{src['branch']}?recursive=1"
            response = await client.get(tree_url)
            response.raise_for_status()
            tree_data = response.json()

            yaml_files = [
                item
                for item in tree_data.get("tree", [])
                if item["path"].startswith("detections/") and item["path"].endswith((".yaml", ".yml")) and item["type"] == "blob"
            ]
            logger.info(f"Found {len(yaml_files)} YAML files in {src['repo']}")

            # Bounded concurrency — firing thousands at once exhausts the pool and
            # trips GitHub throttling.
            semaphore = asyncio.Semaphore(12)

            async def _fetch_bounded(path: str):
                async with semaphore:
                    return await self._fetch_yaml_file(client, src, path)

            tasks = [_fetch_bounded(file_info["path"]) for file_info in yaml_files]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.warning(f"Failed to fetch rule: {result}")
                elif result is not None:
                    rules.append(result)

        return rules

    async def _fetch_yaml_file(
        self,
        client: httpx.AsyncClient,
        src: dict,
        file_path: str,
    ) -> Optional[dict]:
        """Fetch and parse a single YAML file from a repo source."""
        try:
            raw_url = f"{GITHUB_RAW_BASE}/{src['repo']}/{src['branch']}/{file_path}"

            response = await client.get(raw_url)
            response.raise_for_status()

            raw_yaml = response.text
            rule_data = yaml.safe_load(raw_yaml)

            if not isinstance(rule_data, dict):
                logger.warning(f"Invalid YAML structure in {file_path}")
                return None

            # Add metadata
            rule_data["_file_path"] = file_path
            rule_data["_raw_yaml"] = raw_yaml
            rule_data["_category"] = category_from_path(file_path)
            rule_data["_platform"] = self._detect_platform(file_path, rule_data)
            rule_data["_has_graylog"] = "graylog" in rule_data and bool(rule_data.get("graylog", {}).get("query"))
            rule_data["_provenance"] = src.get("provenance", "catalog")
            rule_data["_owner_customer_code"] = src.get("owner")

            return rule_data

        except Exception as e:
            logger.warning(f"Error fetching {file_path}: {e}")
            return None

    def _detect_platform(self, file_path: str, rule_data: dict) -> str:
        """Detect the platform / source category for a rule from its folder.

        Works with the flat detections/<source_folder>/ layout AND the nested
        windows|linux|cloud/... layout. Most specific wins: PowerShell EID
        folders and Microsoft 365 source folders are checked before the
        generic Windows/Cloud buckets so they aren't swallowed.
        """
        p = f"/{file_path.lower().strip('/')}/"

        if "eid_4103" in p or "eid_4104" in p or "/powershell/" in p:
            return "powershell"

        m365 = ("entra_id", "exchange", "sharepoint_onedrive", "threat_intelligence")
        if "/microsoft_365/" in p or "/office365/" in p or "/office 365/" in p or any(f"/{f}/" in p for f in m365):
            return "office365"

        if "/linux/" in p or any(f"/{f}/" in p for f in ("auditd", "syslog", "tetragon")):
            return "linux"

        if "/web/" in p:
            return "web"

        win_folders = (
            "application_eventlog",
            "defender_operational",
            "security_eventlog",
            "system_eventlog",
            "task_scheduler_operational",
            "multi_event",
        )
        if "/windows/" in p or "/sysmon/" in p or "/eid_" in p or any(f"/{f}/" in p for f in win_folders):
            return "windows"

        tags = rule_data.get("tags", {})
        asset_type = tags.get("asset_type", "").lower()
        if "linux" in asset_type:
            return "linux"
        if "windows" in asset_type:
            return "windows"

        name_lower = rule_data.get("name", "").lower()
        if "powershell" in name_lower:
            return "powershell"
        if "cve" in name_lower:
            return "cve"
        if "linux" in name_lower:
            return "linux"
        if "windows" in name_lower:
            return "windows"

        products = tags.get("product", [])
        product_text = " ".join(products).lower() if isinstance(products, list) else str(products).lower()
        security_domain = str(tags.get("security_domain", "")).lower()
        if any(key in product_text for key in ("office 365", "office365", "o365", "m365")):
            return "office365"
        if "cloud" in asset_type or security_domain == "cloud":
            return "cloud"

        return "unknown"

    def _normalize_name(self, name: str) -> str:
        """Normalize rule name for lookup."""
        return name.lower().strip().replace(" ", "_").replace("-", "_")

    def get_all_rules(self) -> list[dict]:
        """Get all cached rules."""
        return list(self._rules.values())

    def get_rule_by_id(self, rule_id: str) -> Optional[dict]:
        """Get a rule by its ID."""
        return self._rules.get(rule_id)

    def get_rule_by_name(self, name: str) -> Optional[dict]:
        """Get a rule by its name (fuzzy match)."""
        normalized = self._normalize_name(name)

        # Exact match
        if normalized in self._rules_by_name:
            rule_id = self._rules_by_name[normalized]
            return self._rules.get(rule_id)

        # Partial match
        for stored_name, rule_id in self._rules_by_name.items():
            if normalized in stored_name or stored_name in normalized:
                return self._rules.get(rule_id)

        return None

    def get_categories(self) -> list[dict]:
        """
        List the detections/ folders present in the cache, with counts.

        Drives the Data Source filter — derived from the loaded rules rather than
        a hardcoded enum, so a folder added upstream shows up after a refresh.
        """
        counts: dict[str, int] = {}
        for rule in self._rules.values():
            folder = rule.get("_category") or UNCATEGORIZED
            counts[folder] = counts.get(folder, 0) + 1

        categories = [
            {
                "value": folder,
                "label": category_label(folder),
                "group": category_group(folder),
                "count": count,
            }
            for folder, count in counts.items()
        ]
        categories.sort(
            key=lambda c: (
                CATEGORY_GROUP_ORDER.index(c["group"]),
                -c["count"],
                c["label"].lower(),
            ),
        )
        return categories

    def filter_rules(
        self,
        platform: PlatformFilter = PlatformFilter.ALL,
        category: Optional[str] = None,
        status: Optional[RuleStatus] = None,
        severity: Optional[RuleSeverity] = None,
        mitre_id: Optional[str] = None,
        search: Optional[str] = None,
        has_graylog: Optional[bool] = None,
        provenance: Optional[str] = None,
    ) -> list[dict]:
        """Filter rules based on criteria."""
        results = []
        category_key = category.lower() if category else None

        for rule in self._rules.values():
            # Platform filter
            if platform != PlatformFilter.ALL:
                rule_platform = rule.get("_platform", "unknown")
                if rule_platform != platform.value:
                    continue

            # Category (detections/ folder) filter — matched case-insensitively
            # because the repo mixes cases (Entra_id, Exchange vs auditd).
            if category_key is not None:
                rule_category = (rule.get("_category") or UNCATEGORIZED).lower()
                if rule_category != category_key:
                    continue

            # Status filter
            if status is not None:
                rule_status = rule.get("status", "").lower()
                if rule_status != status.value:
                    continue

            # Severity filter
            if severity is not None:
                rule_severity = rule.get("response", {}).get("severity", "").lower()
                if rule_severity != severity.value:
                    continue

            # MITRE ATT&CK filter
            if mitre_id is not None:
                mitre_ids = rule.get("tags", {}).get("mitre_attack_id", [])
                if not any(mitre_id.upper() in m.upper() for m in mitre_ids):
                    continue

            # Text search (name, description)
            if search is not None:
                search_lower = search.lower()
                name = rule.get("name", "").lower()
                description = rule.get("description", "").lower()
                if search_lower not in name and search_lower not in description:
                    continue

            # Graylog query filter
            if has_graylog is not None:
                rule_has_graylog = rule.get("_has_graylog", False)
                if rule_has_graylog != has_graylog:
                    continue

            # Provenance filter (catalog = shared repo, custom = a client's repo)
            if provenance is not None:
                if (rule.get("_provenance") or "catalog") != provenance:
                    continue

            results.append(rule)

        return results

    def get_stats(self) -> dict:
        """Get statistics about cached rules."""
        stats = {
            "total_rules": len(self._rules),
            "by_platform": {},
            "by_category": {},
            "by_status": {},
            "by_severity": {},
            "by_mitre_tactic": {},
            "rules_with_graylog": 0,
        }

        for rule in self._rules.values():
            # By platform
            platform = rule.get("_platform", "unknown")
            stats["by_platform"][platform] = stats["by_platform"].get(platform, 0) + 1

            # By category (detections/ folder)
            category = rule.get("_category") or UNCATEGORIZED
            stats["by_category"][category] = stats["by_category"].get(category, 0) + 1

            # By status
            status = rule.get("status", "unknown")
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

            # By severity
            severity = rule.get("response", {}).get("severity", "unknown")
            stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1

            # By MITRE tactic (extract tactic from technique ID)
            mitre_ids = rule.get("tags", {}).get("mitre_attack_id", [])
            for mitre_id in mitre_ids:
                # Extract base technique (e.g., T1136 from T1136.001)
                base_technique = mitre_id.split(".")[0] if "." in mitre_id else mitre_id
                stats["by_mitre_tactic"][base_technique] = stats["by_mitre_tactic"].get(base_technique, 0) + 1

            # Count rules with Graylog queries
            if rule.get("_has_graylog", False):
                stats["rules_with_graylog"] += 1

        return stats


# =============================================================================
# Helper Functions
# =============================================================================


def rule_to_summary(rule: dict) -> RuleSummary:
    """Convert a raw rule dict to a RuleSummary model."""
    tags = rule.get("tags", {})
    response = rule.get("response", {})

    aggregation = rule.get("aggregation")
    has_aggregation = bool(isinstance(aggregation, dict) and aggregation.get("enabled"))

    return RuleSummary(
        id=rule.get("id", ""),
        name=rule.get("name", ""),
        version=rule.get("version", 1),
        status=rule.get("status", "unknown"),
        type=rule.get("type", "unknown"),
        description=rule.get("description", ""),
        author=rule.get("author", ""),
        date=rule.get("date", ""),
        severity=response.get("severity", "medium"),
        risk_score=response.get("risk_score", 0),
        platform=rule.get("_platform", "unknown"),
        category=rule.get("_category") or UNCATEGORIZED,
        category_label=category_label(rule.get("_category") or UNCATEGORIZED),
        mitre_attack_id=tags.get("mitre_attack_id", []),
        analytic_story=tags.get("analytic_story", []),
        cve=tags.get("cve", []),
        file_path=rule.get("_file_path", ""),
        has_graylog_query=rule.get("_has_graylog", False),
        has_aggregation=has_aggregation,
        provenance=rule.get("_provenance", "catalog"),
        owner_customer_code=rule.get("_owner_customer_code"),
    )


def rule_to_detail(rule: dict) -> RuleDetail:
    """Convert a raw rule dict to a RuleDetail model."""
    # Parse parameters
    params = []
    for name, param_data in rule.get("parameters", {}).items():
        params.append(
            ParameterSchema(
                name=name,
                description=param_data.get("description", ""),
                type=param_data.get("type", "string"),
                required=param_data.get("required", False),
                default=param_data.get("default"),
                example=param_data.get("example"),
            ),
        )

    # Parse Graylog query if present
    graylog = None
    graylog_data = rule.get("graylog")
    if graylog_data and isinstance(graylog_data, dict) and graylog_data.get("query"):
        graylog = GraylogQuery(query=graylog_data.get("query", ""))

    # Parse aggregation block if present. Tolerant here — a malformed block must
    # not break the detail view; provisioning is where it's strictly validated.
    aggregation = None
    aggregation_data = rule.get("aggregation")
    if isinstance(aggregation_data, dict):
        try:
            aggregation = AggregationConfig(**aggregation_data)
        except ValidationError:
            aggregation = None

    return RuleDetail(
        id=rule.get("id", ""),
        name=rule.get("name", ""),
        version=rule.get("version", 1),
        schema_version=rule.get("schema_version", "1.0"),
        status=rule.get("status", "unknown"),
        type=rule.get("type", "unknown"),
        description=rule.get("description", ""),
        author=rule.get("author", ""),
        date=rule.get("date", ""),
        data_source=rule.get("data_source", []),
        search=rule.get("search", {}),
        parameters=params,
        how_to_implement=rule.get("how_to_implement", ""),
        known_false_positives=rule.get("known_false_positives", ""),
        references=rule.get("references", []),
        response=rule.get("response", {}),
        tags=rule.get("tags", {}),
        file_path=rule.get("_file_path", ""),
        raw_yaml=rule.get("_raw_yaml", ""),
        graylog=graylog,
        aggregation=aggregation,
        provenance=rule.get("_provenance", "catalog"),
        owner_customer_code=rule.get("_owner_customer_code"),
    )


def _convert_seconds_to_milliseconds(seconds: int) -> int:
    """Convert seconds to milliseconds."""
    return seconds * 1000


def _get_alert_source_from_rule(rule: dict) -> str:
    """
    Determine the alert source based on rule metadata.

    Args:
        rule: The rule dictionary

    Returns:
        Alert source string (e.g., "WAZUH", "LINUX_AUDITD", etc.)
    """
    # Check data_source field
    data_sources = rule.get("data_source", [])
    if data_sources:
        # Use first data source, normalized
        source = data_sources[0].upper().replace(" ", "_").replace("-", "_")
        return source

    # Check platform
    platform = rule.get("_platform", "unknown")
    if platform == "linux":
        return "LINUX"
    if platform == "windows":
        return "WINDOWS"

    return "COPILOT_SEARCH"


def _get_priority_from_severity(severity: str) -> int:
    """
    Map rule severity to Graylog priority.

    Args:
        severity: Rule severity (low, medium, high, critical)

    Returns:
        Graylog priority (1=Low, 2=Normal, 3=High)
    """
    severity_map = {
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 3,
    }
    return severity_map.get(severity.lower(), 2)


# =============================================================================
# Aggregation helpers
# =============================================================================


def _parse_duration_to_ms(value: Any) -> int:
    """
    Parse a duration into milliseconds.

    Accepts an int/float (treated as seconds) or a string with an optional unit
    suffix — ``s`` seconds, ``m`` minutes, ``h`` hours, ``d`` days. A bare
    numeric string is treated as seconds. Raises ValueError on anything else.
    """
    # bool is an int subclass — reject it explicitly so True/False can't slip through.
    if isinstance(value, bool):
        raise ValueError(f"Invalid duration: {value!r}")
    if isinstance(value, (int, float)):
        seconds = float(value)
    else:
        text = str(value).strip().lower()
        if not text:
            raise ValueError("Duration must not be empty")
        units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        try:
            if text[-1] in units:
                seconds = float(text[:-1]) * units[text[-1]]
            else:
                seconds = float(text)
        except ValueError:
            raise ValueError(f"Invalid duration: {value!r}")
    if seconds <= 0:
        raise ValueError(f"Duration must be positive: {value!r}")
    return int(seconds * 1000)


def _get_rule_aggregation(rule: dict) -> Optional[AggregationConfig]:
    """
    Parse and validate the optional ``aggregation`` block on a rule.

    Returns a validated ``AggregationConfig`` when the block is present and
    ``enabled=True``. Returns None when the block is missing or disabled — in
    which case the rule provisions as a plain single-event filter alert. Raises
    ValueError (surfaced as HTTP 400 by the route) when the block is present but
    malformed, so a bad detection fails loudly instead of silently degrading.
    """
    raw = rule.get("aggregation")
    if not isinstance(raw, dict):
        return None
    try:
        config = AggregationConfig(**raw)
    except ValidationError as exc:
        raise ValueError(f"Invalid aggregation block: {exc}")
    return config if config.enabled else None


def _build_aggregation_series_and_conditions(
    aggregation: AggregationConfig,
) -> tuple[list[dict], dict]:
    """
    Translate an ``AggregationConfig`` into a Graylog ``series`` list and
    ``conditions`` expression for an ``aggregation-v1`` event definition.

    - ``count``          -> series type ``count`` (no field)
    - ``distinct_count`` -> series type ``card`` over ``aggregation.field``

    The condition compares the single series against ``threshold`` using the
    configured operator, e.g. ``count() > 21``. The series ``id`` and the
    condition's ``ref`` must match — Graylog resolves the threshold against the
    series by that id.
    """
    series_id = "copilot-agg-0"
    if aggregation.function == AggregationFunction.DISTINCT_COUNT:
        series = [{"id": series_id, "type": "card", "field": aggregation.field}]
    else:
        series = [{"id": series_id, "type": "count", "field": None}]

    # Graylog Expr type ids (org.graylog.events.conditions.Expr) are exact:
    # a numeric literal is "number" (NOT "number-value"), a series reference is
    # "number-ref", and the operator is the raw symbol (">", ">=", ...). Graylog
    # rejects any other id with "Could not resolve type id ... as a subtype of
    # NumberExpression".
    conditions = {
        "expression": {
            "expr": aggregation.condition,
            "left": {"expr": "number-ref", "ref": series_id},
            "right": {"expr": "number", "value": aggregation.threshold},
        },
    }
    return series, conditions


# =============================================================================
# Global Cache Instance
# =============================================================================

rules_cache = RulesCache()


# =============================================================================
# Service Functions
# =============================================================================


async def get_categories_list() -> list[dict]:
    """
    List the available detection categories (detections/ folders) with counts.

    Returns:
        List of {value, label, group, count} dicts, group-ordered.
    """
    await rules_cache.ensure_loaded()
    return rules_cache.get_categories()


async def get_rules_list(
    platform: PlatformFilter = PlatformFilter.ALL,
    category: Optional[str] = None,
    status: Optional[RuleStatus] = None,
    severity: Optional[RuleSeverity] = None,
    mitre_id: Optional[str] = None,
    search: Optional[str] = None,
    has_graylog: Optional[bool] = None,
    provenance: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> dict:
    """
    Get filtered list of detection rules.

    Args:
        platform: Filter by platform (linux, windows, powershell, all)
        category: Filter by detections/ folder (e.g. eid_01_process_creation)
        status: Filter by rule status
        severity: Filter by severity level
        mitre_id: Filter by MITRE ATT&CK technique ID
        search: Text search in name/description
        has_graylog: Filter for rules with Graylog queries
        skip: Number of rules to skip
        limit: Maximum rules to return

    Returns:
        Dictionary with total, filtered count, platform, category, and rules list

    Raises:
        ValueError: If category is not a folder present in the cache (surfaced as
            HTTP 400) — a typo returning an empty list looks identical to a folder
            with no rules, which is a miserable thing to debug from the UI.
    """
    await rules_cache.ensure_loaded()

    if category is not None:
        known = {c["value"].lower() for c in rules_cache.get_categories()}
        if category.lower() not in known:
            raise ValueError(
                f"Unknown category '{category}'. See GET /copilot_searches/categories for the available folders.",
            )

    # Filter rules
    filtered_rules = rules_cache.filter_rules(
        platform=platform,
        category=category,
        status=status,
        severity=severity,
        mitre_id=mitre_id,
        search=search,
        has_graylog=has_graylog,
        provenance=provenance,
    )

    # Sort by name
    filtered_rules.sort(key=lambda r: r.get("name", "").lower())

    # Paginate
    total_filtered = len(filtered_rules)
    paginated = filtered_rules[skip : skip + limit]

    # Convert to summaries
    summaries = [rule_to_summary(rule) for rule in paginated]

    return {
        "total": rules_cache.rules_count,
        "filtered": total_filtered,
        "platform": platform.value,
        "category": category,
        "rules": summaries,
    }


async def get_rule_by_id(rule_id: str) -> Optional[RuleDetail]:
    """
    Get full details of a rule by its ID.

    Args:
        rule_id: The rule ID

    Returns:
        RuleDetail or None if not found
    """
    await rules_cache.ensure_loaded()

    rule = rules_cache.get_rule_by_id(rule_id)

    if rule is None:
        return None

    return rule_to_detail(rule)


async def get_rules_by_ids(ids: list[str]) -> tuple[list[RuleSummary], list[str]]:
    """
    Fetch many rule summaries by ID in one shot.

    Returns (found_summaries, missing_ids).
    """
    await rules_cache.ensure_loaded()

    found: list[RuleSummary] = []
    missing: list[str] = []
    for rule_id in ids:
        rule = rules_cache.get_rule_by_id(rule_id)
        if rule is None:
            missing.append(rule_id)
        else:
            found.append(rule_to_summary(rule))
    return found, missing


async def get_rule_by_name(rule_name: str) -> Optional[RuleDetail]:
    """
    Get full details of a rule by its name (fuzzy match).

    Args:
        rule_name: The rule name (supports fuzzy matching)

    Returns:
        RuleDetail or None if not found
    """
    await rules_cache.ensure_loaded()

    rule = rules_cache.get_rule_by_name(rule_name)

    if rule is None:
        return None

    return rule_to_detail(rule)


async def get_rules_stats() -> dict:
    """
    Get statistics about loaded detection rules.

    Returns:
        Dictionary with rule statistics
    """
    await rules_cache.ensure_loaded()

    stats = rules_cache.get_stats()

    return {
        "total_rules": stats["total_rules"],
        "by_platform": stats["by_platform"],
        "by_category": stats["by_category"],
        "by_status": stats["by_status"],
        "by_severity": stats["by_severity"],
        "by_mitre_tactic": stats["by_mitre_tactic"],
        "rules_with_graylog": stats["rules_with_graylog"],
        "last_refreshed": rules_cache.last_refresh,
        "cache_ttl_minutes": CACHE_TTL_MINUTES,
    }


async def refresh_rules_cache() -> dict:
    """
    Manually refresh the rules cache from GitHub.

    Returns:
        Dictionary with refresh results
    """
    rules_loaded = await rules_cache.refresh()

    return {
        "success": True,
        "message": "Rules cache refreshed successfully",
        "rules_loaded": rules_loaded,
        "timestamp": datetime.utcnow(),
    }


async def get_cache_health() -> dict:
    """
    Get health/status information about the rules cache.

    Returns:
        Dictionary with cache health information
    """
    return {
        "status": "healthy" if not rules_cache.is_stale else "stale",
        "rules_loaded": rules_cache.rules_count,
        "cache_age_minutes": rules_cache.cache_age_minutes,
        "github_repo": GITHUB_REPO,
    }


# =============================================================================
# Search Execution Functions
# =============================================================================


def _substitute_parameters(obj: Any, parameters: dict[str, Any]) -> Any:
    """
    Recursively substitute ${PARAM_NAME} placeholders in a query object.

    Args:
        obj: The object to substitute parameters in (dict, list, or str)
        parameters: Dictionary of parameter names to values

    Returns:
        The object with parameters substituted
    """
    if isinstance(obj, str):
        # Find all ${PARAM_NAME} patterns and replace them
        pattern = r"\$\{([^}]+)\}"

        def replacer(match):
            param_name = match.group(1)
            if param_name in parameters:
                value = parameters[param_name]
                # If the entire string is just the placeholder, return the value directly
                # This preserves types (int, bool, etc.)
                if match.group(0) == obj:
                    return value
                # Otherwise, convert to string for embedding
                return str(value)
            # Return original if parameter not found
            return match.group(0)

        # Check if entire string is a single placeholder
        full_match = re.fullmatch(pattern, obj)
        if full_match:
            param_name = full_match.group(1)
            if param_name in parameters:
                return parameters[param_name]

        # Otherwise do string substitution
        return re.sub(pattern, replacer, obj)

    elif isinstance(obj, dict):
        return {key: _substitute_parameters(value, parameters) for key, value in obj.items()}

    elif isinstance(obj, list):
        return [_substitute_parameters(item, parameters) for item in obj]

    else:
        return obj


def _validate_parameters(
    rule: dict,
    provided_params: dict[str, Any],
) -> tuple[dict[str, Any], list[SearchValidationError]]:
    """
    Validate and merge provided parameters with defaults.

    Args:
        rule: The rule definition
        provided_params: Parameters provided by the user

    Returns:
        Tuple of (merged_params, validation_errors)
    """
    errors: list[SearchValidationError] = []
    merged_params: dict[str, Any] = {}

    rule_params = rule.get("parameters", {})

    for param_name, param_def in rule_params.items():
        is_required = param_def.get("required", False)
        default_value = param_def.get("default")

        if param_name in provided_params:
            # User provided the parameter
            merged_params[param_name] = provided_params[param_name]
        elif default_value is not None:
            # Use default value
            merged_params[param_name] = default_value
        elif is_required:
            # Required parameter missing
            errors.append(
                SearchValidationError(
                    parameter=param_name,
                    message=f"Required parameter '{param_name}' is missing. {param_def.get('description', '')}",
                ),
            )

    return merged_params, errors


async def execute_rule_search(
    request: ExecuteSearchRequest,
) -> ExecuteSearchResponse:
    """
    Execute a search against the Wazuh indexer using a rule definition.

    Args:
        request: The search execution request

    Returns:
        ExecuteSearchResponse with search results

    Raises:
        ValueError: If the rule is not found or validation fails
    """
    await rules_cache.ensure_loaded()

    # Get the rule
    rule = rules_cache.get_rule_by_id(request.rule_id)
    if rule is None:
        raise ValueError(f"Rule with ID '{request.rule_id}' not found")

    # Add INDEX_PATTERN to provided parameters
    all_params = {**request.parameters, "INDEX_PATTERN": request.index_pattern}

    # Validate parameters
    merged_params, validation_errors = _validate_parameters(rule, all_params)

    if validation_errors:
        error_messages = [f"{e.parameter}: {e.message}" for e in validation_errors]
        raise ValueError(f"Parameter validation failed: {'; '.join(error_messages)}")

    # Get the search definition from the rule
    search_def = rule.get("search", {})
    if not search_def:
        raise ValueError(f"Rule '{request.rule_id}' does not contain a search definition")

    # Build the query with parameter substitution
    query = search_def.get("query", {})
    substituted_query = _substitute_parameters(copy.deepcopy(query), merged_params)

    # Build the full search body
    search_body: dict[str, Any] = {
        "query": substituted_query,
    }

    # Add size (from request override, rule definition, or default)
    if request.size is not None:
        search_body["size"] = request.size
    elif "size" in search_def:
        search_body["size"] = search_def["size"]
    else:
        search_body["size"] = 100

    # Add sort if defined
    if "sort" in search_def:
        search_body["sort"] = _substitute_parameters(
            copy.deepcopy(search_def["sort"]),
            merged_params,
        )

    # Add _source if defined
    if "_source" in search_def:
        search_body["_source"] = search_def["_source"]

    logger.info(f"Executing search for rule '{request.rule_id}' on index '{request.index_pattern}'")
    logger.debug(f"Search body: {json.dumps(search_body, indent=2)}")

    # Create the async Elasticsearch client
    es_client = await create_wazuh_indexer_client_async()

    try:
        # Execute the search
        response = await es_client.search(
            index=request.index_pattern,
            body=search_body,
        )

        # Parse the response
        hits_data = response.get("hits", {})
        total_hits = hits_data.get("total", {})
        if isinstance(total_hits, dict):
            total_count = total_hits.get("value", 0)
        else:
            total_count = total_hits

        hits = []
        for hit in hits_data.get("hits", []):
            hits.append(
                SearchHit(
                    index=hit.get("_index", ""),
                    id=hit.get("_id", ""),
                    score=hit.get("_score"),
                    source=hit.get("_source", {}),
                ),
            )

        return ExecuteSearchResponse(
            success=True,
            message="Search executed successfully",
            rule_id=request.rule_id,
            rule_name=rule.get("name", ""),
            total_hits=total_count,
            returned_hits=len(hits),
            took_ms=response.get("took", 0),
            hits=hits,
            query_executed=search_body,
        )

    except Exception as e:
        logger.error(f"Search execution failed: {e}")
        raise ValueError(f"Search execution failed: {str(e)}")

    finally:
        # Close the client
        await es_client.close()


# =============================================================================
# Graylog Query Functions
# =============================================================================


async def generate_graylog_query(
    request: ExecuteGraylogQueryRequest,
) -> GraylogQueryResponse:
    """
    Generate a Graylog query string from a rule with parameter substitution.

    Args:
        request: The Graylog query request

    Returns:
        GraylogQueryResponse with the substituted query

    Raises:
        ValueError: If the rule is not found or has no Graylog query
    """
    await rules_cache.ensure_loaded()

    # Get the rule
    rule = rules_cache.get_rule_by_id(request.rule_id)
    if rule is None:
        raise ValueError(f"Rule with ID '{request.rule_id}' not found")

    # Check if rule has Graylog query
    graylog_data = rule.get("graylog")
    if not graylog_data or not isinstance(graylog_data, dict):
        raise ValueError(f"Rule '{request.rule_id}' does not contain a Graylog query")

    original_query = graylog_data.get("query", "")
    if not original_query:
        raise ValueError(f"Rule '{request.rule_id}' has an empty Graylog query")

    # Validate parameters
    merged_params, validation_errors = _validate_parameters(rule, request.parameters)

    if validation_errors:
        error_messages = [f"{e.parameter}: {e.message}" for e in validation_errors]
        raise ValueError(f"Parameter validation failed: {'; '.join(error_messages)}")

    # Substitute parameters in the Graylog query
    substituted_query = _substitute_parameters(original_query, merged_params)

    logger.info(f"Generated Graylog query for rule '{request.rule_id}'")

    return GraylogQueryResponse(
        success=True,
        message="Graylog query generated successfully",
        rule_id=request.rule_id,
        rule_name=rule.get("name", ""),
        graylog_query=substituted_query,
        original_query=original_query,
    )


# =============================================================================
# Graylog Alert Provisioning Functions
# =============================================================================


async def provision_graylog_alert_from_rule(
    request: ProvisionGraylogAlertRequest,
) -> ProvisionGraylogAlertResponse:
    """
    Provision a Graylog event definition from a CoPilot Search rule.

    This takes a rule with a Graylog query and creates a Graylog event definition
    that will alert when the query matches.

    Args:
        request: The provisioning request

    Returns:
        ProvisionGraylogAlertResponse with the result

    Raises:
        ValueError: If the rule is not found or has no Graylog query
    """
    await rules_cache.ensure_loaded()

    # Get the rule
    rule = rules_cache.get_rule_by_id(request.rule_id)
    if rule is None:
        raise ValueError(f"Rule with ID '{request.rule_id}' not found")

    # Check if rule has Graylog query
    graylog_data = rule.get("graylog")
    if not graylog_data or not isinstance(graylog_data, dict):
        raise ValueError(f"Rule '{request.rule_id}' does not contain a Graylog query")

    graylog_query = graylog_data.get("query", "")
    if not graylog_query:
        raise ValueError(f"Rule '{request.rule_id}' has an empty Graylog query")

    # Get rule metadata
    rule_name = rule.get("name", request.rule_id)
    rule_description = rule.get("description", "")
    rule_severity = rule.get("response", {}).get("severity", "medium")
    alert_source = _get_alert_source_from_rule(rule)

    # Determine the alert title
    alert_title = request.custom_title if request.custom_title else rule_name.upper().replace(" ", " - ")

    # Determine priority from rule severity or request
    priority = request.priority if request.priority != 2 else _get_priority_from_severity(rule_severity)

    logger.info(f"Provisioning Graylog alert for rule '{request.rule_id}' with title '{alert_title}'")

    # Resolve aggregation vs single-event provisioning. A rule carrying an
    # `aggregation` block with enabled=True becomes a Graylog aggregation event
    # definition (count()/card() over group_by, within `window`, firing on the
    # threshold condition). Any other rule keeps the original per-event
    # filter-alert shape byte-for-byte (empty series/group_by, no condition).
    aggregation = _get_rule_aggregation(rule)
    if aggregation is not None:
        agg_series, agg_conditions = _build_aggregation_series_and_conditions(aggregation)
        agg_group_by = aggregation.group_by
        search_within_ms = _parse_duration_to_ms(aggregation.window)
        execute_every_ms = (
            _parse_duration_to_ms(aggregation.execute_every)
            if aggregation.execute_every
            else _convert_seconds_to_milliseconds(request.execute_every_seconds)
        )
        logger.info(
            f"Rule '{request.rule_id}' provisioned as AGGREGATION event definition "
            f"(function={aggregation.function.value}, group_by={agg_group_by}, "
            f"search_within_ms={search_within_ms}, condition={aggregation.condition} {aggregation.threshold})",
        )
    else:
        agg_series = []
        agg_group_by = []
        agg_conditions = {"expression": None}
        search_within_ms = _convert_seconds_to_milliseconds(request.search_within_seconds)
        execute_every_ms = _convert_seconds_to_milliseconds(request.execute_every_seconds)

    # Build the Graylog event definition model
    alert_model = GraylogAlertProvisionModel(
        title=alert_title,
        description=rule_description,
        priority=priority,
        config=GraylogAlertProvisionConfig(
            type="aggregation-v1",
            query=graylog_query,
            query_parameters=[],
            streams=request.streams,
            group_by=agg_group_by,
            series=agg_series,
            conditions=agg_conditions,
            search_within_ms=search_within_ms,
            execute_every_ms=execute_every_ms,
            event_limit=request.event_limit,
        ),
        field_spec={
            "ALERT_ID": GraylogAlertProvisionFieldSpecItem(
                data_type="string",
                providers=[
                    GraylogAlertProvisionProvider(
                        type="template-v1",
                        template="${source._id}",
                        require_values=True,
                    ),
                ],
            ),
            "CUSTOMER_CODE": GraylogAlertProvisionFieldSpecItem(
                data_type="string",
                providers=[
                    GraylogAlertProvisionProvider(
                        type="template-v1",
                        template="${source.agent_labels_customer}",
                        require_values=True,
                    ),
                ],
            ),
            "ALERT_SOURCE": GraylogAlertProvisionFieldSpecItem(
                data_type="string",
                providers=[
                    GraylogAlertProvisionProvider(
                        type="template-v1",
                        template=alert_source,
                        require_values=True,
                    ),
                ],
            ),
            "COPILOT_ALERT_ID": GraylogAlertProvisionFieldSpecItem(
                data_type="string",
                providers=[
                    GraylogAlertProvisionProvider(
                        type="template-v1",
                        template="NONE",
                        require_values=True,
                    ),
                ],
            ),
            "RULE_ID": GraylogAlertProvisionFieldSpecItem(
                data_type="string",
                providers=[
                    GraylogAlertProvisionProvider(
                        type="template-v1",
                        template=request.rule_id,
                        require_values=True,
                    ),
                ],
            ),
        },
        key_spec=[],
        notification_settings=GraylogAlertProvisionNotificationSettings(
            grace_period_ms=0,
            backlog_size=None,
        ),
        alert=True,
    )

    # Provision the alert definition
    await provision_alert_definition(alert_model)

    logger.info(f"Successfully provisioned Graylog alert '{alert_title}' for rule '{request.rule_id}'")

    return ProvisionGraylogAlertResponse(
        success=True,
        message=f"Graylog alert '{alert_title}' provisioned successfully",
        rule_id=request.rule_id,
        rule_name=rule_name,
        alert_title=alert_title,
        graylog_query=graylog_query,
    )
