"""
In-memory cache for Wazuh Manager rules — powers the "Wazuh Rules" tab of the
Detections Catalog.

Why this exists separately from ``RulesCache`` (CoPilot Searches):
- Different source: Wazuh Manager REST API, not a GitHub repo. We reuse the
  existing connector wrapper ``get_wazuh_rules()`` so there's only one place
  in the codebase that knows how to call ``GET /rules``.
- Different cadence: Wazuh rules change only on operator action (XML upload,
  rule enable/disable). A long TTL (1 hour) is generous; the data is
  effectively static between operator events.
- Different failure mode: the Wazuh Manager may be unconfigured or down on a
  given deployment. We must NOT raise out of the catalog code path in that
  case — the Stories tab and the rest of CoPilot keep working without the
  Wazuh tab. The cache holds an ``unavailable_reason`` string so the UI can
  render an explanatory empty state instead of a generic error.

Auth note:
The wrapped connector route (``/wazuh_manager/rules``) is admin-only via
``Security(...scopes=["admin"])``. The catalog deliberately calls the underlying
service function ``get_wazuh_rules()`` instead, because scope checks live on
the route handler, not the service. That keeps the catalog viewable by
analysts / customer_user roles without loosening the Wazuh management surface.
"""

import asyncio
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from loguru import logger

# Long TTL by design — Wazuh rules don't change without operator action. A
# manual ``refresh()`` is exposed for the rare "I just uploaded a rule file"
# case; we don't poll aggressively.
CACHE_TTL_MINUTES = 60


class WazuhRulesCache:
    """
    Single-source-of-truth in-memory copy of the Wazuh Manager ruleset, keyed
    by integer rule ID, with the same ``ensure_loaded`` / ``refresh`` /
    ``last_refresh`` surface as the CoPilot Searches ``RulesCache`` so the
    catalog aggregator code can treat them symmetrically.
    """

    def __init__(self) -> None:
        # rule_id (int) -> raw rule dict (the Wazuh API "affected_items" entry)
        self._rules: Dict[int, Dict[str, Any]] = {}
        self._last_refresh: Optional[datetime] = None
        # When Wazuh is unreachable / not configured, populated with a short
        # human-readable reason so the catalog UI can show an empty state
        # instead of bubbling a 5xx. None means "last load succeeded".
        self._unavailable_reason: Optional[str] = None
        self._lock = asyncio.Lock()

    # ---- introspection ----------------------------------------------------

    @property
    def is_stale(self) -> bool:
        if self._last_refresh is None:
            return True
        return (datetime.utcnow() - self._last_refresh) > timedelta(minutes=CACHE_TTL_MINUTES)

    @property
    def last_refresh(self) -> Optional[datetime]:
        return self._last_refresh

    @property
    def rules_count(self) -> int:
        return len(self._rules)

    @property
    def is_available(self) -> bool:
        """True if the last load succeeded — i.e. the catalog can render rule rows."""
        return self._unavailable_reason is None

    @property
    def unavailable_reason(self) -> Optional[str]:
        return self._unavailable_reason

    # ---- loading ----------------------------------------------------------

    async def ensure_loaded(self) -> None:
        """Lazy-load on first access; refresh on TTL expiry. Never raises."""
        if self.is_stale:
            await self.refresh()

    async def refresh(self) -> int:
        """
        Pull the full Wazuh ruleset into memory in one shot.

        Returns the number of rules loaded (0 if Wazuh is unavailable).
        Never raises — failures are captured in ``unavailable_reason`` and
        the existing cached snapshot (if any) is left in place rather than
        wiped, so a transient Wazuh outage doesn't blank the UI.
        """
        # Local import to avoid a hard dependency at module import time —
        # keeps copilot_searches importable even on deployments where the
        # wazuh_manager package isn't usable (e.g. unit tests).
        from app.connectors.wazuh_manager.services.rules import get_wazuh_rules

        async with self._lock:
            logger.info("Refreshing Wazuh rules cache from Wazuh Manager…")
            try:
                # limit=100000 is the Wazuh API ceiling; one call gets the
                # entire ruleset for any realistic deployment (~3–5k rules).
                # offset stays at 0.
                response = await get_wazuh_rules(limit=100000, offset=0)
            except Exception as exc:  # noqa: BLE001 — we deliberately catch all
                self._unavailable_reason = _short_reason(exc)
                logger.warning(
                    f"Wazuh rules cache refresh failed: {self._unavailable_reason}. "
                    "Keeping previously cached snapshot (if any).",
                )
                # Still mark refresh time so we don't hammer Wazuh on every
                # request when it's down; user can force ``refresh()`` to retry.
                self._last_refresh = datetime.utcnow()
                return len(self._rules)

            # Success — fully replace the cache. Don't merge: we want
            # disabled / deleted rules to disappear too.
            new_rules: Dict[int, Dict[str, Any]] = {}
            for item in response.results:
                # The schema is Pydantic — convert to plain dict so downstream
                # aggregators get a uniform shape (.dict() not .model_dump()
                # because both work in v2 and the older spelling reads less
                # surprising to anyone who hasn't tracked the v1→v2 rename).
                rule_dict = item.model_dump(by_alias=False)
                rid = rule_dict.get("id")
                if isinstance(rid, int):
                    new_rules[rid] = rule_dict

            self._rules = new_rules
            self._unavailable_reason = None
            self._last_refresh = datetime.utcnow()
            logger.info(f"Loaded {len(self._rules)} Wazuh rules into cache")
            return len(self._rules)

    # ---- accessors --------------------------------------------------------

    def get_all_rules(self) -> List[Dict[str, Any]]:
        """Return every cached rule as a plain dict (caller-owned, safe to mutate)."""
        return list(self._rules.values())

    def get_rule(self, rule_id: int) -> Optional[Dict[str, Any]]:
        return self._rules.get(rule_id)


def _short_reason(exc: BaseException) -> str:
    """
    Trim noisy exception messages down to a UI-friendly one-liner.

    Wazuh connector errors typically wrap an httpx/HTTPException and include
    full URLs + stack-trace-ish detail. We want something the empty-state
    component can show inline without exploding the layout.
    """
    raw = str(exc).strip() or exc.__class__.__name__
    # Common cases — keep them short and actionable.
    lower = raw.lower()
    if "connection" in lower or "timed out" in lower or "timeout" in lower:
        return "Wazuh Manager is not reachable."
    if "401" in raw or "403" in raw or "unauthor" in lower:
        return "Wazuh Manager rejected the credentials."
    if "not configured" in lower or "not found" in lower:
        return "Wazuh Manager connector is not configured."
    # Generic fallback — truncate aggressively so it fits in a tooltip.
    return raw[:160] + ("…" if len(raw) > 160 else "")


# Module-level singleton — symmetrical with ``rules_cache`` in copilot_searches.
wazuh_rules_cache = WazuhRulesCache()
