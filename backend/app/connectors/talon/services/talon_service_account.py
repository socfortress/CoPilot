"""Who talon-analyst's CoPilot service account is, and the routes it may never use (talon-analyst
plan EA-4b; SPEC D77).

The service account is an analyst, assigned only to the live customers. Its one way to start
anything on an endpoint is ``POST /api/artifacts/collect/start``, held to its auto-run allowlist
(``talon_collections``). Every other route an analyst (or, whatever its role, a responder or admin)
can use to **start** something through Velociraptor refuses it with a 403, so the allowlist can't be
stepped around (``refuse_talon_service_account``):

- ``/api/artifacts/collect`` (through ``start_collection_as`` with the analyst policy, which also
  covers an approved Talon collection), ``/collect/file/agent/{agent_id}``, ``/command``,
  ``/quarantine``;
- ``/api/file-analysis/velociraptor/enumerate`` and ``/submit`` (a ``FileFinder`` collection);
- ``/api/agents/{agent_id}/delete``, ``/bulk/delete``, ``/bulk/delete/filter`` (Velociraptor's
  ``Server.Utils.DeleteClient``);
- ``/api/copilot_mcp/query`` (an MCP agent, the Velociraptor server among them);
- ``/api/copilot_action/invoke``;
- deciding a Talon v2 action proposal (``talon_action_execution.check_d47``).

Routes that only read stay open to it. **Who it is**: the user whose id the setting recorded when an
admin last saved it (``collect_service_user_id``, so a rename doesn't take it out), the user named
by ``collect_service_username``, and the user named ``talon-analyst``, names compared
case-insensitively, whatever the role. The recorded id is cleared when that user is deleted
(``forget_deleted_user``) and, at startup, when it no longer belongs to a user with the name
(``recheck_recorded_user_id``), so a reused id never gates someone else.
"""
from typing import Any
from typing import FrozenSet
from typing import Optional

from fastapi import Depends
from fastapi import HTTPException
from loguru import logger
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.connectors.talon.models.talon_v2 import TalonConnectorSettings
from app.connectors.talon.utils.v2_client import TALON_CONNECTOR
from app.db.db_session import get_db

#: The service user's name in CoPilot's docs (CLAUDE.md, "AI analyst pipeline"): always held to the
#: gate, so the gate holds before an admin names the user.
DEFAULT_SERVICE_USERNAME = "talon-analyst"
REFUSED = "The Talon service account may start collections only through /api/artifacts/collect/start"


async def settings_row(session: AsyncSession) -> Optional[TalonConnectorSettings]:
    result = await session.execute(select(TalonConnectorSettings).where(TalonConnectorSettings.connector_name == TALON_CONNECTOR))
    row = result.scalars().first()
    return row if isinstance(row, TalonConnectorSettings) else None


def effective_username(row: Optional[TalonConnectorSettings]) -> str:
    return (row.collect_service_username if row is not None else None) or DEFAULT_SERVICE_USERNAME


def service_usernames(row: Optional[TalonConnectorSettings]) -> FrozenSet[str]:
    """The names held to the gate, case-folded: ``talon-analyst`` and the configured one."""
    return frozenset(name.casefold() for name in {DEFAULT_SERVICE_USERNAME, effective_username(row)})


def is_service_account(user: Any, row: Optional[TalonConnectorSettings]) -> bool:
    """By the recorded id or by name (module docstring)."""
    recorded = row.collect_service_user_id if row is not None else None
    if recorded is not None and getattr(user, "id", None) == recorded:
        return True
    username = getattr(user, "username", None)
    return isinstance(username, str) and username.casefold() in service_usernames(row)


async def is_talon_service_account(user: Any, session: AsyncSession) -> bool:
    return is_service_account(user, await settings_row(session))


async def refuse_talon_service_account(user: Any, session: AsyncSession) -> None:
    """403 for the service account; nothing for anyone else."""
    if await is_talon_service_account(user, session):
        logger.warning(f"Refused the Talon service account {getattr(user, 'username', '?')} on a route that starts endpoint work")
        raise HTTPException(status_code=403, detail=REFUSED)


async def refuse_talon_service_account_dependency(
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """``refuse_talon_service_account`` as a route dependency (after the route's scope check)."""
    await refuse_talon_service_account(current_user, session)


async def user_id_for(session: AsyncSession, username: str) -> Optional[int]:
    """The id of the one user with ``username`` (case-insensitive), or None for none or several."""
    rows = (await session.execute(select(User.id, User.username).where(func.lower(User.username) == username.lower()))).all()
    matches = [uid for uid, name in rows if isinstance(name, str) and name.casefold() == username.casefold()]
    return matches[0] if len(matches) == 1 else None


async def recheck_recorded_user_id(session: AsyncSession, row: TalonConnectorSettings) -> bool:
    """Clear the recorded service-user id unless it still belongs to a user with the service
    account's name, so a reused id never gates someone else. True when it was cleared."""
    recorded = row.collect_service_user_id
    if recorded is None:
        return False
    user = await session.get(User, recorded)
    name = effective_username(row)
    if user is not None and isinstance(user.username, str) and user.username.casefold() == name.casefold():
        return False
    row.collect_service_user_id = None
    await session.commit()
    logger.warning(
        f"Talon collection setting: the recorded service-account user id {recorded} no longer belongs to a user named '{name}'; "
        "cleared. If the account was renamed, save the setting again with its new name.",
    )
    return True


async def forget_deleted_user(session: AsyncSession, user_id: int) -> None:
    """A deleted user's id is no longer the service account's (``auth.services.universal.delete_user``,
    in its transaction): cleared, so the id, if ever reused, gates nobody."""
    await session.execute(
        update(TalonConnectorSettings)
        .where(TalonConnectorSettings.collect_service_user_id == user_id)
        .values(collect_service_user_id=None),
    )


async def warn_if_service_user_missing(engine) -> None:
    """At startup: re-check the recorded user id (``recheck_recorded_user_id``), and once the
    collection setting is in use, warn when no user has the service account's name (the allowlist
    then guards nobody by name). Never fatal."""
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            row = await settings_row(session)
            if row is None:
                return
            await recheck_recorded_user_id(session, row)
            if row.collect_service_username is None and row.collect_allowed_artifacts is None:
                return
            name = effective_username(row)
            if await user_id_for(session, name) is None:
                logger.warning(
                    f"Talon collection setting: no single CoPilot user is named '{name}', the Talon service account's name. "
                    "Check Talon v2 settings, collections (PUT /api/talon/v2/settings/collections).",
                )
    except Exception as e:  # noqa: BLE001 - a startup check, never a startup failure
        logger.warning(f"Talon collection setting: the service account check at startup failed ({type(e).__name__})")
