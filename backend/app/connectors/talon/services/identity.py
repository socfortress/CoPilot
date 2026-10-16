"""The five identity headers CoPilot sends on every talon-analyst v2 request (talon-analyst SPEC §8
"v2 API" Identity, §5.3, D40, D41, D55; plan M5-5a).

talon-analyst trusts these headers on a request that carries the API key: they are how it knows
who the user is and which customers and alert tags they may see. So they are computed here, fresh
for every request, from the user the JWT names and from CoPilot's own access rules, never from the
request, and ``utils/v2_client.py`` builds every upstream header from scratch, so a header the
browser sent never reaches talon-analyst.

- ``X-Talon-User``: ``str(user.id)``, as v1 stamps ``user_id`` (``services/talon.py``), so v1 and v2
  share the user's chat memory.
- ``X-Talon-Role``: ``RoleEnum(user.role_id).name``, the user's one role. Not the JWT's scopes: a
  responder's token carries ``responder`` and ``analyst``, and talon-analyst wants exactly one.
- ``X-Talon-Customers``: ``get_user_accessible_customers``; an admin's ``["*"]`` is ``*``. A code
  outside talon-analyst's grammar is dropped and logged: one such code would otherwise make every
  v2 request of the user a 400, and dropping it narrows what the user sees, never widens it.
- ``X-Talon-Tags`` / ``X-Talon-Untagged``: ``tag_access_handler.build_alert_query_filters``.
  ``{"*"}`` (tag RBAC off, or an unrestricted role) is ``*``; otherwise the sorted tag ids, or empty
  for none. ``include_untagged`` is ``true`` or ``false``.

The formats are talon-analyst's ``talon/api/identity.py`` and ``talon/tenancy/access.py``.
"""
import re
from typing import Dict
from typing import Iterable
from typing import List

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.incidents.middleware.tag_access import tag_access_handler
from app.middleware.customer_access import customer_access_handler

USER_HEADER = "X-Talon-User"
ROLE_HEADER = "X-Talon-Role"
CUSTOMERS_HEADER = "X-Talon-Customers"
TAGS_HEADER = "X-Talon-Tags"
UNTAGGED_HEADER = "X-Talon-Untagged"
#: Every identity header, in the order they are sent. Nothing else named ``X-Talon-*`` is ever sent.
IDENTITY_HEADERS = (USER_HEADER, ROLE_HEADER, CUSTOMERS_HEADER, TAGS_HEADER, UNTAGGED_HEADER)

ALL = "*"
#: The roles talon-analyst lets chat (its ``ROLES``). A ``customer_user`` or the scheduler never
#: reaches these routes (they are admin/analyst scoped); refusing here too keeps that true if a
#: scope ever changes.
CHAT_ROLES = frozenset({"admin", "analyst", "responder"})

#: talon-analyst's customer-code grammar (``talon.config.parse_customer_codes``): 1 to 64
#: characters, letters, digits, ``.``, ``_`` and ``-``, starting with a letter or digit.
TALON_CUSTOMER_CODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
#: The reserved chat-memory wing, never a customer (talon-analyst ``CHAT_MEMORY_WING``, D34). It has
#: spaces, so the grammar already refuses it; checked as well so the two rules can't drift apart.
CHAT_MEMORY_WING = "talon chat memory"
#: talon-analyst's tag id range (CoPilot's tag id is a signed 32-bit INT).
TAG_ID_MAX = 2_147_483_647


def is_talon_customer_code(code: object) -> bool:
    """Whether talon-analyst accepts ``code`` as one customer code, exactly as written."""
    return isinstance(code, str) and bool(TALON_CUSTOMER_CODE.fullmatch(code)) and code.strip().casefold() != CHAT_MEMORY_WING


def talon_role(user: User) -> str:
    """The user's one CoPilot role by name; a role talon-analyst doesn't let chat is a 403 here."""
    try:
        name = RoleEnum(user.role_id).name
    except ValueError:
        name = None
    if name not in CHAT_ROLES:
        raise HTTPException(status_code=403, detail="This role may not chat with Talon")
    return name


def customers_header(user: User, role: str, accessible: Iterable[str]) -> str:
    """``X-Talon-Customers`` from the user's accessible customers.

    ``*`` only for an admin (talon-analyst refuses it for anyone else); a non-admin's ``*`` can't
    happen today and is dropped like any other bad entry, so the user sees none of it.
    """
    codes = list(accessible)
    if ALL in codes and role == "admin":
        return ALL
    kept: List[str] = []
    dropped: List[str] = []
    for code in codes:
        (kept if code != ALL and is_talon_customer_code(code) else dropped).append(code)
    if dropped:
        logger.warning(
            f"Talon v2: dropped {len(dropped)} customer code(s) outside talon-analyst's grammar for user {user.id}: "
            + ", ".join(repr(code) for code in sorted(map(str, dropped))),
        )
    return ",".join(sorted(set(kept)))


def tags_header(accessible_tags: Iterable[object]) -> str:
    """``X-Talon-Tags`` from ``build_alert_query_filters``' ``accessible_tags``: ``*`` or sorted ids."""
    tags = set(accessible_tags)
    if ALL in tags:
        return ALL
    ids = sorted({tag for tag in tags if isinstance(tag, int) and not isinstance(tag, bool) and 1 <= tag <= TAG_ID_MAX})
    if len(ids) != len(tags):  # not a tag id talon-analyst could read: leaving it out only narrows the filter
        logger.warning(f"Talon v2: dropped {len(tags) - len(ids)} tag id(s) talon-analyst can't read")
    return ",".join(str(tag) for tag in ids)


async def talon_identity_headers(user: User, session: AsyncSession) -> Dict[str, str]:
    """The five ``X-Talon-*`` headers for ``user``, computed now from CoPilot's access rules."""
    role = talon_role(user)
    accessible = await customer_access_handler.get_user_accessible_customers(user, session)
    filters = await tag_access_handler.build_alert_query_filters(user, session)
    return {
        USER_HEADER: str(user.id),
        ROLE_HEADER: role,
        CUSTOMERS_HEADER: customers_header(user, role, accessible),
        TAGS_HEADER: tags_header(filters["accessible_tags"]),
        UNTAGGED_HEADER: "true" if filters["include_untagged"] else "false",
    }
