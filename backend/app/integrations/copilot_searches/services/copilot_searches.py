import asyncio
import copy
import json
import re
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx
import yaml
from loguru import logger

from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client_async
from app.integrations.copilot_searches.schema.copilot_searches import (
    ExecuteSearchRequest,
    ExecuteSearchResponse,
    ParameterSchema,
    PlatformFilter,
    RuleDetail,
    RuleSeverity,
    RuleStatus,
    RuleSummary,
    SearchHit,
    SearchValidationError,
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
# Rules Cache
# =============================================================================

class RulesCache:
    """
    In-memory cache for detection rules fetched from GitHub.

    Handles fetching, parsing, and caching YAML rules from the repository.
    """

    def __init__(self):
        self._rules: dict[str, dict] = {}  # id -> rule data
        self._rules_by_name: dict[str, str] = {}  # normalized name -> id
        self._last_refresh: Optional[datetime] = None
        self._lock = asyncio.Lock()

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

                self._rules[rule_id] = rule

                # Index by normalized name for lookup
                normalized_name = self._normalize_name(rule_name)
                self._rules_by_name[normalized_name] = rule_id

            self._last_refresh = datetime.utcnow()
            logger.info(f"Loaded {len(self._rules)} rules from GitHub")

            return len(self._rules)

    async def _fetch_all_rules(self) -> list[dict]:
        """Fetch all YAML rules from GitHub repository."""
        rules = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get the directory tree for detections
            tree_url = (
                f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/git/trees/{GITHUB_BRANCH}"
                f"?recursive=1"
            )

            response = await client.get(tree_url)
            response.raise_for_status()

            tree_data = response.json()

            # Filter for YAML files in detections directory
            yaml_files = [
                item
                for item in tree_data.get("tree", [])
                if item["path"].startswith("detections/")
                and item["path"].endswith(".yaml")
                and item["type"] == "blob"
            ]

            logger.info(f"Found {len(yaml_files)} YAML files in repository")

            # Fetch each YAML file
            tasks = [
                self._fetch_yaml_file(client, file_info["path"])
                for file_info in yaml_files
            ]

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
        file_path: str,
    ) -> Optional[dict]:
        """Fetch and parse a single YAML file from GitHub."""
        try:
            raw_url = f"{GITHUB_RAW_BASE}/{GITHUB_REPO}/{GITHUB_BRANCH}/{file_path}"

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
            rule_data["_platform"] = self._detect_platform(file_path, rule_data)

            return rule_data

        except Exception as e:
            logger.warning(f"Error fetching {file_path}: {e}")
            return None

    def _detect_platform(self, file_path: str, rule_data: dict) -> str:
        """Detect the platform (Linux/Windows) for a rule."""
        path_lower = file_path.lower()

        # Check path first
        if "/linux/" in path_lower:
            return "linux"
        if "/windows/" in path_lower:
            return "windows"

        # Check tags
        asset_type = rule_data.get("tags", {}).get("asset_type", "").lower()
        if "linux" in asset_type:
            return "linux"
        if "windows" in asset_type:
            return "windows"

        # Check rule name
        name_lower = rule_data.get("name", "").lower()
        if "linux" in name_lower:
            return "linux"
        if "windows" in name_lower or "powershell" in name_lower:
            return "windows"

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

    def filter_rules(
        self,
        platform: PlatformFilter = PlatformFilter.ALL,
        status: Optional[RuleStatus] = None,
        severity: Optional[RuleSeverity] = None,
        mitre_id: Optional[str] = None,
        search: Optional[str] = None,
    ) -> list[dict]:
        """Filter rules based on criteria."""
        results = []

        for rule in self._rules.values():
            # Platform filter
            if platform != PlatformFilter.ALL:
                rule_platform = rule.get("_platform", "unknown")
                if rule_platform != platform.value:
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

            results.append(rule)

        return results

    def get_stats(self) -> dict:
        """Get statistics about cached rules."""
        stats = {
            "total_rules": len(self._rules),
            "by_platform": {},
            "by_status": {},
            "by_severity": {},
            "by_mitre_tactic": {},
        }

        for rule in self._rules.values():
            # By platform
            platform = rule.get("_platform", "unknown")
            stats["by_platform"][platform] = stats["by_platform"].get(platform, 0) + 1

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
                stats["by_mitre_tactic"][base_technique] = (
                    stats["by_mitre_tactic"].get(base_technique, 0) + 1
                )

        return stats


# =============================================================================
# Helper Functions
# =============================================================================


def rule_to_summary(rule: dict) -> RuleSummary:
    """Convert a raw rule dict to a RuleSummary model."""
    tags = rule.get("tags", {})
    response = rule.get("response", {})

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
        mitre_attack_id=tags.get("mitre_attack_id", []),
        analytic_story=tags.get("analytic_story", []),
        cve=tags.get("cve", []),
        file_path=rule.get("_file_path", ""),
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
    )


# =============================================================================
# Global Cache Instance
# =============================================================================

rules_cache = RulesCache()


# =============================================================================
# Service Functions
# =============================================================================


async def get_rules_list(
    platform: PlatformFilter = PlatformFilter.ALL,
    status: Optional[RuleStatus] = None,
    severity: Optional[RuleSeverity] = None,
    mitre_id: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> dict:
    """
    Get filtered list of detection rules.

    Args:
        platform: Filter by platform (linux, windows, all)
        status: Filter by rule status
        severity: Filter by severity level
        mitre_id: Filter by MITRE ATT&CK technique ID
        search: Text search in name/description
        skip: Number of rules to skip
        limit: Maximum rules to return

    Returns:
        Dictionary with total, filtered count, platform, and rules list
    """
    await rules_cache.ensure_loaded()

    # Filter rules
    filtered_rules = rules_cache.filter_rules(
        platform=platform,
        status=status,
        severity=severity,
        mitre_id=mitre_id,
        search=search,
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
        "by_status": stats["by_status"],
        "by_severity": stats["by_severity"],
        "by_mitre_tactic": stats["by_mitre_tactic"],
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
