"""The identity headers CoPilot sends on every talon-analyst v2 request (talon-analyst SPEC §8
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

A Customer Portal user's requests (talon-analyst D97) get an identity of their own,
``portal_identity_headers``: role ``customer``, their own customers, tags ``*``, and a sixth header,
``X-Talon-Read-Only``. The SOC builder above refuses a ``customer_user``, so a portal user reaches
talon-analyst only through the portal builder.

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
from app.auth.services.read_only import read_only_customer_codes
from app.incidents.middleware.tag_access import tag_access_handler
from app.middleware.customer_access import customer_access_handler

USER_HEADER = "X-Talon-User"
ROLE_HEADER = "X-Talon-Role"
CUSTOMERS_HEADER = "X-Talon-Customers"
TAGS_HEADER = "X-Talon-Tags"
UNTAGGED_HEADER = "X-Talon-Untagged"
READ_ONLY_HEADER = "X-Talon-Read-Only"
#: Every identity header, in the order they are sent. Nothing else named ``X-Talon-*`` is ever sent.
IDENTITY_HEADERS = (USER_HEADER, ROLE_HEADER, CUSTOMERS_HEADER, TAGS_HEADER, UNTAGGED_HEADER)
#: The portal identity's headers (talon-analyst D97, FR-CHAT-9): the five, plus ``X-Talon-Read-Only``,
#: which talon-analyst requires on its ``/v2/portal/`` routes and ignores everywhere else.
PORTAL_IDENTITY_HEADERS = (*IDENTITY_HEADERS, READ_ONLY_HEADER)
#: The portal user's ``X-Talon-Role``: a value of its own, never ``customer_user``, so a portal user
#: reaches talon-analyst only through ``portal_identity_headers`` and only its portal routes.
PORTAL_ROLE = "customer"

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
#: talon-analyst refuses more tag ids than this in one header (``TAGS_MAX``): every v2 request of
#: such a user is then a 400, which fails closed. Warned about so an operator can see why.
TAGS_MAX = 1000
#: Customer codes past which the header gets large enough to worry about (no talon-analyst limit;
#: a proxy's header-size limit would refuse the request, which also fails closed).
CUSTOMERS_WARN = 500


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
    kept = sorted(set(kept))
    if len(kept) > CUSTOMERS_WARN:
        logger.warning(f"Talon v2: user {user.id} has {len(kept)} customers; a header that large may be refused upstream")
    return ",".join(kept)


def tags_header(accessible_tags: Iterable[object]) -> str:
    """``X-Talon-Tags`` from ``build_alert_query_filters``' ``accessible_tags``: ``*`` or sorted ids."""
    tags = set(accessible_tags)
    if ALL in tags:
        return ALL
    ids = sorted({tag for tag in tags if isinstance(tag, int) and not isinstance(tag, bool) and 1 <= tag <= TAG_ID_MAX})
    if len(ids) != len(tags):  # not a tag id talon-analyst could read: leaving it out only narrows the filter
        logger.warning(f"Talon v2: dropped {len(tags) - len(ids)} tag id(s) talon-analyst can't read")
    if len(ids) > TAGS_MAX:
        logger.warning(f"Talon v2: {len(ids)} tag ids is over talon-analyst's {TAGS_MAX}: its v2 routes will refuse this user (400)")
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


#: The ops notification poller's ``X-Talon-User`` (plan OJ-5). Not a CoPilot user id (those are
#: numbers, ``str(user.id)``), so talon-analyst's logs can never take it for a person.
OPS_POLLER_USER = "copilot-ops-poller"


def ops_poller_identity() -> Dict[str, str]:
    """The identity CoPilot's ops notification job sends talon-analyst (talon-analyst SPEC §5.7
    "Notifications"; plan OJ-5). The one v2 request CoPilot makes for no signed-in user.

    Every other server-to-server v2 call acts for a real user (the approver, the requester), with that
    user's headers computed now. The poller acts for nobody: it reads the findings nobody has been
    told about yet, across every customer and the platform, and records that it told the SOC. So it
    needs ``X-Talon-Customers: *``, which talon-analyst accepts only with ``X-Talon-Role: admin``. It
    is CoPilot vouching for itself, with the same API key that already authenticates every call.

    What keeps it narrow is the caller, not the headers: only ``services/talon_ops_notify.py`` uses
    it, and only for ``GET /v2/ops/findings`` (open, not notified), ``GET /v2/ops/jobs`` (the jobs'
    titles, for the summary) and ``POST /v2/ops/findings/{id}/notified``. It never acknowledges,
    mutes, reopens or runs anything, and no route takes it. Only an admin may add, run, start, pause,
    reschedule or delete the poller's job (``schedulers/routes/scheduler.py:refuse_unless_admin_for``)."""
    return {
        USER_HEADER: OPS_POLLER_USER,
        ROLE_HEADER: "admin",
        CUSTOMERS_HEADER: ALL,
        TAGS_HEADER: ALL,
        UNTAGGED_HEADER: "true",
    }


# ── the portal identity (talon-analyst D97, FR-CHAT-9; plan PC-3) ─────────────


class PortalIdentityRefused(Exception):
    """No portal identity can be built for this user: not a portal user, or no customer."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


async def portal_identity_headers(user: User, session: AsyncSession) -> Dict[str, str]:
    """The six ``X-Talon-*`` headers of a Customer Portal user's request to talon-analyst's
    ``/v2/portal/`` routes, computed now from CoPilot's own rules, never from the request.

    - ``X-Talon-User``: ``str(user.id)``, as for the SOC.
    - ``X-Talon-Role``: ``customer``. Only a ``customer_user`` (by the database role, not the token)
      gets one; anyone else is refused (``not_portal_role``), as the SOC builder refuses them.
    - ``X-Talon-Customers``: the user's own customers (``user_customer_access``), never ``*``; a code
      outside talon-analyst's grammar is dropped. None left is ``customer_not_accessible``.
    - ``X-Talon-Tags: *`` and ``X-Talon-Untagged: true``, always: ``customer_user`` is one of the tag
      handler's ``UNRESTRICTED_ROLES`` (a customer sees every alert of its own customer), and
      talon-analyst refuses any other value on its portal routes.
    - ``X-Talon-Read-Only``: the user's customers they may only read (``user_customer_access.read_only``,
      #1312), a subset of ``X-Talon-Customers``, empty for none.
    """
    if getattr(user, "role_id", None) != RoleEnum.customer_user.value:
        raise PortalIdentityRefused("not_portal_role")
    accessible = [code for code in await customer_access_handler.get_user_accessible_customers(user, session) if code != ALL]
    customers = customers_header(user, "customer", accessible)
    if not customers:
        raise PortalIdentityRefused("customer_not_accessible")
    kept = set(customers.split(","))
    read_only = sorted(code for code in await read_only_customer_codes(user, session) if code in kept)
    return {
        USER_HEADER: str(user.id),
        ROLE_HEADER: PORTAL_ROLE,
        CUSTOMERS_HEADER: customers,
        TAGS_HEADER: ALL,
        UNTAGGED_HEADER: "true",
        READ_ONLY_HEADER: ",".join(read_only),
    }
