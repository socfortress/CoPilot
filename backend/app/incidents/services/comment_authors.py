"""The role of whoever wrote an alert's or a case's comments, for the comment list's role badges.

A comment carries its author only as ``user_name``, so the role is read from the ``user`` table
when the list is shown, never stored on the comment: a user whose role changes shows the new one.
Only the authors of the comments of an alert or case the caller can read are named, after the
same checks as reading that alert or case, so this answers nothing about anyone else.
"""

from typing import Dict
from typing import Iterable

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.incidents.services.db_operations import get_alert_by_id
from app.incidents.services.db_operations import get_case_by_id
from app.middleware.customer_access import customer_access_handler


async def roles_by_username(usernames: Iterable[str], session: AsyncSession) -> Dict[str, str]:
    """Each existing user's role name (``admin``, ``analyst``, ``customer_user``…) by username.

    A name that is no user (an ingest pipeline's signature, a deleted account) is left out.
    """
    names = sorted({name for name in usernames if name})
    if not names:
        return {}
    rows = (await session.execute(select(User.username, User.role_id).where(User.username.in_(names)))).all()
    roles = {}
    for username, role_id in rows:
        try:
            roles[username] = RoleEnum(role_id).name
        except ValueError:
            continue
    return roles


async def alert_comment_authors(alert_id: int, user: User, session: AsyncSession) -> Dict[str, str]:
    """The roles of the authors of an alert's comments, checked like reading the alert."""
    alert = await get_alert_by_id(alert_id, session, user=user)
    if not await customer_access_handler.check_customer_access(user, alert.customer_code, session):
        raise HTTPException(status_code=403, detail=f"Access denied to alert {alert_id} - insufficient customer permissions")
    return await roles_by_username((comment.user_name for comment in alert.comments or []), session)


async def case_comment_authors(case_id: int, user: User, session: AsyncSession) -> Dict[str, str]:
    """The roles of the authors of a case's comments, checked like reading the case."""
    case = await get_case_by_id(case_id, session)
    if not await customer_access_handler.check_customer_access(user, case.customer_code, session):
        raise HTTPException(status_code=403, detail=f"Access denied to case {case_id} - insufficient customer permissions")
    return await roles_by_username((comment.user_name for comment in case.comments or []), session)
