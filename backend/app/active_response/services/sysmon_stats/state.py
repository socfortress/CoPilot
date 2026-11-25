"""The MinIO records of the weekly Sysmon noise statistics, beside the default sync's sync.json.

- ``stats-state.json``: the service's state, the last tick, the pause, the releases seen, and per ISO week and customer
  the outcome of its report (counts and hashes only). Only the last STATE_WEEKS_KEPT weeks are kept. Written only by a
  tick or Send now, under the named lock; the routes only read it.
- ``stats-withdraw/<pseudonym>.json``: one withdraw still to be sent, created by an opt-out, a decommission or a
  customer deletion, and deleted once SOCFortress confirms it. One object per pseudonym, so no read-modify-write races,
  and it outlives the customer's row.

Neither ever holds a value of a report, a payload or the license key.
"""
import json
import re
from typing import List
from typing import Optional

from loguru import logger
from pydantic import ValidationError

from app.active_response.schema.sysmon_stats import StatsState
from app.active_response.schema.sysmon_stats import StatsWithdrawRequest
from app.active_response.services.sysmon_stats import settings
from app.data_store.data_store_operations import SYSMON_STATS_STATE_OBJECT
from app.data_store.data_store_operations import SYSMON_STATS_WITHDRAW_PREFIX
from app.data_store.data_store_operations import delete_sysmon_defaults_object
from app.data_store.data_store_operations import list_sysmon_defaults_objects
from app.data_store.data_store_operations import read_sysmon_defaults_object
from app.data_store.data_store_operations import write_sysmon_defaults_object

_WITHDRAW_NAME_RE = re.compile(r"cust_[0-9a-f]{32}\.json")


def _json_bytes(model) -> bytes:
    return json.dumps(model.model_dump(mode="json", by_alias=True), indent=2, sort_keys=True).encode("utf-8")


async def read_state() -> StatsState:
    """stats-state.json; a fresh state when there is none, or it cannot be read as one (logged). A MinIO failure raises."""
    raw = await read_sysmon_defaults_object(SYSMON_STATS_STATE_OBJECT)
    if raw is None:
        return StatsState()
    try:
        return StatsState.model_validate(json.loads(raw))
    except (ValueError, UnicodeDecodeError, ValidationError):
        logger.warning(f"Sysmon stats: {SYSMON_STATS_STATE_OBJECT} is not a state record; starting from an empty one")
        return StatsState()


def prune(state: StatsState) -> None:
    for week in sorted(state.weeks)[: -settings.STATE_WEEKS_KEPT or None]:
        state.weeks.pop(week, None)
    if len(state.releases) > settings.RELEASES_KEPT:
        for key in sorted(state.releases, key=lambda k: int(k) if k.isdigit() else -1)[: -settings.RELEASES_KEPT]:
            state.releases.pop(key, None)


async def write_state(state: StatsState) -> None:
    prune(state)
    await write_sysmon_defaults_object(SYSMON_STATS_STATE_OBJECT, _json_bytes(state), "application/json")


def withdraw_object(customer: str) -> str:
    return f"{SYSMON_STATS_WITHDRAW_PREFIX}{customer}.json"


async def read_withdraw(customer: str) -> Optional[StatsWithdrawRequest]:
    raw = await read_sysmon_defaults_object(withdraw_object(customer))
    if raw is None:
        return None
    try:
        return StatsWithdrawRequest.model_validate(json.loads(raw))
    except (ValueError, UnicodeDecodeError, ValidationError):
        logger.warning("Sysmon stats: a queued withdraw could not be read; it is kept and sent by its name")
        return None


async def write_withdraw(request: StatsWithdrawRequest) -> None:
    await write_sysmon_defaults_object(withdraw_object(request.customer), _json_bytes(request), "application/json")


async def delete_withdraw(customer: str) -> None:
    await delete_sysmon_defaults_object(withdraw_object(customer))


async def list_withdraws() -> List[str]:
    """The pseudonyms with a queued withdraw."""
    names = await list_sysmon_defaults_objects(SYSMON_STATS_WITHDRAW_PREFIX)
    out = []
    for name in names:
        base = name[len(SYSMON_STATS_WITHDRAW_PREFIX) :] if name.startswith(SYSMON_STATS_WITHDRAW_PREFIX) else name
        if _WITHDRAW_NAME_RE.fullmatch(base):
            out.append(base[: -len(".json")])
    return sorted(out)
