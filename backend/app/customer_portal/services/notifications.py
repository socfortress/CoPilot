"""Email and in-app notifications for Customer Portal users (#1282).

CoPilot's notification engine (``app/notifications/``) is the SOC's: routes a
customer's operator configures, sending to fixed addresses or to an assignee. This
module is the portal user's side of it — each user chooses what reaches them, in the
bell and by email — and shares only the message templates and the SMTP sender.

**Opt-in twice.** Nothing is written for a customer whose switch
(``customer_portal_notification_settings``) is off, and each user's choices
(``customer_portal_notification_pref``) default to the bell only: email is theirs to
turn on.

**One row per user and notification** (``customer_portal_notification``), unique on
(user, ``dedupe_key``). It is the bell's feed and the email queue at once, so a
retried or concurrent emission can never notify anyone twice, and an email's fate is
recorded next to the notification it belongs to.

**Never wider than the portal.** Recipients are the customer's portal users, and an
alert reaches only those the portal's own visibility lets see it
(``alert_visibility_filters_for_user``, the one definition every portal read uses; by
policy a customer user sees every alert of their customer, tags included). The person
who caused an event is never told about it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Dict
from typing import FrozenSet
from typing import Iterable
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple

from loguru import logger
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.auth.models.users import UserCustomerAccess
from app.db.universal_models import CustomerPortalNotification
from app.db.universal_models import CustomerPortalNotificationPref
from app.db.universal_models import CustomerPortalNotificationSettings
from app.incidents.models import Alert
from app.incidents.services.alert_severity import SEVERITY_LEVELS
from app.incidents.services.alert_severity import normalize_severity
from app.incidents.services.alert_severity import severity_rank
from app.middleware.customer_access import customer_access_handler
from app.time_utils import now_utc
from app.time_utils import to_naive_utc

# ── Vocabulary ────────────────────────────────────────────────────────────────

EVENT_ALERT_CREATED = "alert_created"
EVENT_WAITING_ON_YOU = "waiting_on_you"
EVENT_CASE_CLOSED = "case_closed"
EVENT_REPORT_READY = "report_ready"

#: Every event a portal user can be told about, in the order the profile lists them.
EVENTS: Tuple[str, ...] = (EVENT_ALERT_CREATED, EVENT_WAITING_ON_YOU, EVENT_CASE_CLOSED, EVENT_REPORT_READY)

EMAIL_OFF = "off"
EMAIL_IMMEDIATE = "immediate"
EMAIL_DIGEST = "digest"
EMAIL_MODES: Tuple[str, ...] = (EMAIL_OFF, EMAIL_IMMEDIATE, EMAIL_DIGEST)

#: ``email_mode`` of a row that sends no email.
EMAIL_NONE = "none"

STATUS_PENDING = "pending"
STATUS_SENDING = "sending"
STATUS_SENT = "sent"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"

#: New alerts from this severity up, until the user picks another threshold.
DEFAULT_MIN_SEVERITY = "High"

#: The bell's page size cap.
MAX_FEED_PAGE = 50

#: The UTC hour the daily digest goes out, unless ``PORTAL_NOTIFICATION_DIGEST_HOUR`` says otherwise.
DEFAULT_DIGEST_HOUR = 7

ENTITY_ALERT = "alert"
ENTITY_CASE = "case"
ENTITY_REPORT = "report"


def digest_hour() -> int:
    """The UTC hour of the daily digest (``PORTAL_NOTIFICATION_DIGEST_HOUR``, 0–23, default 7)."""
    raw = (os.getenv("PORTAL_NOTIFICATION_DIGEST_HOUR") or "").strip()
    try:
        hour = int(raw) if raw else DEFAULT_DIGEST_HOUR
    except ValueError:
        logger.warning(f"PORTAL_NOTIFICATION_DIGEST_HOUR={raw!r} is not an hour; using {DEFAULT_DIGEST_HOUR}.")
        return DEFAULT_DIGEST_HOUR
    if not 0 <= hour <= 23:
        logger.warning(f"PORTAL_NOTIFICATION_DIGEST_HOUR={hour} is outside 0–23; using {DEFAULT_DIGEST_HOUR}.")
        return DEFAULT_DIGEST_HOUR
    return hour


def email_configured() -> bool:
    """Whether SMTP is set up, the only way a portal user's email can leave."""
    from app.auth.services.security_admin import smtp_configured

    return smtp_configured()


def naive_now() -> datetime:
    """Now as the naive UTC the DATETIME columns hold, for comparisons with stored values."""
    return to_naive_utc(now_utc())


# ── Preferences (pure) ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Preference:
    """What one user wants for one event: the stored row, or the defaults."""

    event: str
    in_app: bool = True
    email: str = EMAIL_OFF
    min_severity: Optional[str] = None

    @property
    def threshold(self) -> str:
        """The lowest alert severity that notifies (new alerts only)."""
        return self.min_severity or DEFAULT_MIN_SEVERITY


def default_preference(event: str) -> Preference:
    """In the bell, not by email: the user turns email on (#1282)."""
    return Preference(event=event, min_severity=DEFAULT_MIN_SEVERITY if event == EVENT_ALERT_CREATED else None)


def effective_preferences(rows: Iterable[CustomerPortalNotificationPref]) -> Dict[str, Preference]:
    """Every event's preference: the user's own where saved, the defaults elsewhere.

    A stored value the code no longer knows (an email mode, a severity) reads as the
    default rather than failing the whole profile.
    """
    prefs = {event: default_preference(event) for event in EVENTS}
    for row in rows:
        if row.event not in prefs:
            continue
        email = row.email if row.email in EMAIL_MODES else EMAIL_OFF
        severity = normalize_severity(row.min_severity) if row.event == EVENT_ALERT_CREATED else None
        prefs[row.event] = Preference(
            event=row.event,
            in_app=bool(row.in_app),
            email=email,
            min_severity=severity or (DEFAULT_MIN_SEVERITY if row.event == EVENT_ALERT_CREATED else None),
        )
    return prefs


# ── Events ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PortalEvent:
    """One thing that happened, about to be offered to a customer's portal users.

    ``dedupe_key`` decides what counts as the same notification: the unique key on
    (user, dedupe_key) is what makes a second emission a no-op. ``actor_user_id`` is
    never notified. ``only_user_ids`` narrows the recipients (a report a portal user
    asked for is that user's alone).
    """

    event: str
    customer_code: str
    entity_type: str
    entity_id: int
    dedupe_key: str
    title: str
    body: Optional[str] = None
    severity: Optional[str] = None
    actor_user_id: Optional[int] = None
    only_user_ids: Optional[FrozenSet[int]] = field(default=None)


@dataclass(frozen=True)
class Delivery:
    """How one notification reaches one user."""

    in_app: bool
    email_mode: str  # EMAIL_NONE | EMAIL_IMMEDIATE | EMAIL_DIGEST


def delivery_for(pref: Preference, event: PortalEvent) -> Optional[Delivery]:
    """How (and whether) ``event`` reaches a user with ``pref``. Pure.

    None when the user asked for nothing, or when a new alert is below their
    threshold. An alert without a stored severity uses the deployment default, the
    way every alert filter does (``severity_of``), so it is never silently dropped.
    """
    if event.event == EVENT_ALERT_CREATED and severity_rank(event.severity) < severity_rank(pref.threshold):
        return None
    email_mode = EMAIL_NONE if pref.email == EMAIL_OFF else pref.email
    if not pref.in_app and email_mode == EMAIL_NONE:
        return None
    return Delivery(in_app=pref.in_app, email_mode=email_mode)


def wants(user_id: int, event: PortalEvent) -> bool:
    """Whether ``user_id`` is a recipient of ``event`` at all, before preferences. Pure."""
    if event.actor_user_id is not None and user_id == event.actor_user_id:
        return False
    if event.only_user_ids is not None and user_id not in event.only_user_ids:
        return False
    return True


def email_problem(user: User) -> Optional[str]:
    """Why an email for this user cannot be sent, or None."""
    if getattr(user, "disabled_at", None) is not None:
        return "The account is disabled"
    if not email_configured():
        return "SMTP is not configured"
    if not getattr(user, "email", None):
        return "The user has no email address"
    return None


# ── The per-customer switch ───────────────────────────────────────────────────


async def get_settings(customer_code: str, session: AsyncSession) -> Optional[CustomerPortalNotificationSettings]:
    result = await session.execute(
        select(CustomerPortalNotificationSettings).where(CustomerPortalNotificationSettings.customer_code == customer_code),
    )
    return result.scalars().first()


async def upsert_settings(
    customer_code: str,
    enabled: bool,
    session: AsyncSession,
    user_id: Optional[int] = None,
) -> CustomerPortalNotificationSettings:
    """Create or update a customer's switch. Caller commits."""
    settings = await get_settings(customer_code, session)
    if settings is None:
        settings = CustomerPortalNotificationSettings(customer_code=customer_code)
        session.add(settings)
    settings.enabled = enabled
    settings.updated_at = now_utc()
    settings.updated_by = user_id
    return settings


async def is_enabled(customer_code: str, session: AsyncSession) -> bool:
    settings = await get_settings(customer_code, session)
    return bool(settings and settings.enabled)


async def enabled_customer_codes(user: User, session: AsyncSession) -> List[str]:
    """The customers ``user`` may see whose portal notifications are on."""
    accessible = await customer_access_handler.get_user_accessible_customers(user, session)
    query = select(CustomerPortalNotificationSettings.customer_code).where(CustomerPortalNotificationSettings.enabled.is_(True))
    if "*" not in accessible:
        if not accessible:
            return []
        query = query.where(CustomerPortalNotificationSettings.customer_code.in_(accessible))
    return sorted((await session.execute(query)).scalars().all())


# ── A user's choices ──────────────────────────────────────────────────────────


async def load_preferences(user_ids: Sequence[int], session: AsyncSession) -> Dict[int, Dict[str, Preference]]:
    """Every listed user's effective preferences, in one query."""
    if not user_ids:
        return {}
    result = await session.execute(select(CustomerPortalNotificationPref).where(CustomerPortalNotificationPref.user_id.in_(user_ids)))
    rows_by_user: Dict[int, List[CustomerPortalNotificationPref]] = {user_id: [] for user_id in user_ids}
    for row in result.scalars().all():
        rows_by_user.setdefault(row.user_id, []).append(row)
    return {user_id: effective_preferences(rows) for user_id, rows in rows_by_user.items()}


async def save_preferences(user_id: int, prefs: Sequence[Preference], session: AsyncSession) -> Dict[str, Preference]:
    """Store the user's choices, one row per event sent. Caller commits."""
    result = await session.execute(select(CustomerPortalNotificationPref).where(CustomerPortalNotificationPref.user_id == user_id))
    existing = {row.event: row for row in result.scalars().all()}
    for pref in prefs:
        row = existing.get(pref.event)
        if row is None:
            row = CustomerPortalNotificationPref(user_id=user_id, event=pref.event)
            session.add(row)
            existing[pref.event] = row
        row.in_app = pref.in_app
        row.email = pref.email
        row.min_severity = pref.min_severity if pref.event == EVENT_ALERT_CREATED else None
        row.updated_at = now_utc()
    return effective_preferences(existing.values())


# ── Fan-out ───────────────────────────────────────────────────────────────────


async def portal_users_of(customer_code: str, session: AsyncSession) -> List[User]:
    """The customer's portal users: active ``customer_user`` accounts assigned to it (a disabled
    account is told nothing, #1296)."""
    result = await session.execute(
        select(User)
        .join(UserCustomerAccess, UserCustomerAccess.user_id == User.id)
        .where(
            UserCustomerAccess.customer_code == customer_code,
            User.role_id == RoleEnum.customer_user.value,
            User.disabled_at.is_(None),
        )
        .order_by(User.id),
    )
    return list(result.scalars().unique().all())


async def can_see(user: User, event: PortalEvent, session: AsyncSession) -> bool:
    """Whether ``user`` may see what ``event`` is about, by the portal's own rules.

    Customer access is already given (recipients are the customer's portal users); an
    alert also goes through the portal's alert visibility, so a narrower rule there
    applies here too.
    """
    if event.entity_type != ENTITY_ALERT:
        return True
    filters = await alert_visibility(user, event.customer_code, session)
    if filters is None:
        return False
    result = await session.execute(select(Alert.id).where(Alert.id == event.entity_id, *filters))
    return result.first() is not None


async def alert_visibility(user: User, customer_code: str, session: AsyncSession):
    from app.incidents.services.db_operations import alert_visibility_filters_for_user

    return await alert_visibility_filters_for_user(user, session, [customer_code])


async def fan_out(event: PortalEvent, session: AsyncSession) -> List[int]:
    """Write ``event``'s notifications, one per user who asked for it. Commits.

    Returns the ids of the rows waiting for an immediate email. Nothing is written
    while the customer's switch is off, and a row that already exists for a user (same
    dedupe key) is left as it is.
    """
    if not await is_enabled(event.customer_code, session):
        return []
    users = [user for user in await portal_users_of(event.customer_code, session) if wants(user.id, event)]
    prefs = await load_preferences([user.id for user in users], session)

    immediate: List[int] = []
    for user in users:
        delivery = delivery_for(prefs[user.id][event.event], event)
        if delivery is None or not await can_see(user, event, session):
            continue
        row = new_row(user, event, delivery)
        try:
            async with session.begin_nested():
                session.add(row)
                await session.flush()
        except IntegrityError:
            # Already notified (a retry, a concurrent emission): the first one stands.
            continue
        if row.email_mode == EMAIL_IMMEDIATE and row.email_status == STATUS_PENDING:
            immediate.append(row.id)
    await session.commit()
    return immediate


def new_row(user: User, event: PortalEvent, delivery: Delivery) -> CustomerPortalNotification:
    """The row ``event`` leaves for ``user``. An email that cannot go out says why."""
    status = None
    problem = None
    if delivery.email_mode != EMAIL_NONE:
        problem = email_problem(user)
        status = STATUS_SKIPPED if problem else STATUS_PENDING
    return CustomerPortalNotification(
        user_id=user.id,
        customer_code=event.customer_code,
        event=event.event,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        dedupe_key=event.dedupe_key[:191],
        title=event.title[:255],
        body=event.body,
        severity=event.severity,
        in_app=delivery.in_app,
        created_at=now_utc(),
        email_mode=delivery.email_mode,
        email_status=status,
        email_error=problem,
    )


# ── Email ─────────────────────────────────────────────────────────────────────


async def claim(row_id: int, session: AsyncSession) -> bool:
    """Take a pending email for sending. Only one caller ever wins a row."""
    result = await session.execute(
        update(CustomerPortalNotification)
        .where(CustomerPortalNotification.id == row_id, CustomerPortalNotification.email_status == STATUS_PENDING)
        .values(email_status=STATUS_SENDING),
    )
    await session.commit()
    return result.rowcount == 1


async def finish(row_ids: Sequence[int], status: str, error: Optional[str], session: AsyncSession) -> None:
    await session.execute(
        update(CustomerPortalNotification)
        .where(CustomerPortalNotification.id.in_(list(row_ids)))
        .values(email_status=status, email_error=(error or None) and error[:500], emailed_at=now_utc()),
    )
    await session.commit()


async def still_deliverable(row: CustomerPortalNotification, user: Optional[User], session: AsyncSession) -> Optional[str]:
    """Why an email queued earlier must not go out now, or None.

    The switch may have been turned off, the user removed from the customer, or their
    address taken away since the notification was written.
    """
    if user is None:
        return "The user no longer exists"
    if not await is_enabled(row.customer_code, session):
        return "Notifications are turned off for this customer"
    if not await customer_access_handler.check_customer_access(user, row.customer_code, session):
        return "The user no longer has access to this customer"
    return email_problem(user)


async def send_immediate(row_ids: Sequence[int], session: AsyncSession) -> None:
    """Send the claimed immediate emails, recording each outcome on its row."""
    from app.auth.services.security_admin import send_email
    from app.customer_portal.services.notification_email import (
        render_notification_email,
    )

    for row_id in row_ids:
        if not await claim(row_id, session):
            continue
        row = await session.get(CustomerPortalNotification, row_id)
        user = await session.get(User, row.user_id) if row else None
        if row is None:
            continue
        problem = await still_deliverable(row, user, session)
        if problem:
            await finish([row_id], STATUS_SKIPPED, problem, session)
            continue
        try:
            subject, text, html = await render_notification_email(row, user, session)
            await send_email(str(user.email), subject, text, html)
        except Exception as e:  # noqa: BLE001 — one failed email must not stop the others
            logger.warning(f"Portal notification email {row_id} to user {row.user_id} failed: {type(e).__name__}: {e}")
            await finish([row_id], STATUS_FAILED, f"{type(e).__name__}: {e}", session)
            continue
        await finish([row_id], STATUS_SENT, None, session)


# ── The daily digest ──────────────────────────────────────────────────────────


def digest_due(now: datetime, last_sent: Optional[datetime], hour: int) -> bool:
    """Whether a user's digest is due. Pure; all times naive UTC.

    Due from today's digest hour on, once: a run that missed the hour still sends that
    day, and a user who already had today's digest waits for tomorrow's.
    """
    due_at = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if now < due_at:
        return False
    return last_sent is None or last_sent < due_at


async def send_digests(session: AsyncSession, now: Optional[datetime] = None) -> int:
    """Send every due digest. Returns how many emails went out.

    One email per user per day at most, holding every notification queued for the
    digest since the last one. Rows that can no longer be delivered are marked
    skipped with the reason.
    """
    from app.auth.services.security_admin import send_email
    from app.customer_portal.services.notification_email import render_digest_email

    now = now or naive_now()
    hour = digest_hour()
    pending = select(CustomerPortalNotification.user_id).where(
        CustomerPortalNotification.email_mode == EMAIL_DIGEST,
        CustomerPortalNotification.email_status == STATUS_PENDING,
    )
    user_ids = sorted(set((await session.execute(pending)).scalars().all()))

    sent = 0
    for user_id in user_ids:
        last_sent = (
            await session.execute(
                select(func.max(CustomerPortalNotification.emailed_at)).where(
                    CustomerPortalNotification.user_id == user_id,
                    CustomerPortalNotification.email_mode == EMAIL_DIGEST,
                    CustomerPortalNotification.email_status == STATUS_SENT,
                ),
            )
        ).scalar()
        if not digest_due(now, last_sent, hour):
            continue

        # Claim this user's queue: only rows still pending, so a second run takes nothing.
        await session.execute(
            update(CustomerPortalNotification)
            .where(
                CustomerPortalNotification.user_id == user_id,
                CustomerPortalNotification.email_mode == EMAIL_DIGEST,
                CustomerPortalNotification.email_status == STATUS_PENDING,
            )
            .values(email_status=STATUS_SENDING),
        )
        await session.commit()
        rows = list(
            (
                await session.execute(
                    select(CustomerPortalNotification)
                    .where(
                        CustomerPortalNotification.user_id == user_id,
                        CustomerPortalNotification.email_mode == EMAIL_DIGEST,
                        CustomerPortalNotification.email_status == STATUS_SENDING,
                    )
                    .order_by(CustomerPortalNotification.id),
                )
            )
            .scalars()
            .all(),
        )
        if not rows:
            continue

        user = await session.get(User, user_id)
        deliverable: List[CustomerPortalNotification] = []
        for row in rows:
            problem = await still_deliverable(row, user, session)
            if problem:
                await finish([row.id], STATUS_SKIPPED, problem, session)
            else:
                deliverable.append(row)
        if not deliverable:
            continue

        ids = [row.id for row in deliverable]
        try:
            subject, text, html = await render_digest_email(deliverable, user, session)
            await send_email(str(user.email), subject, text, html)
        except Exception as e:  # noqa: BLE001 — one user's failure must not stop the others
            logger.warning(f"Portal notification digest for user {user_id} failed: {type(e).__name__}: {e}")
            await finish(ids, STATUS_FAILED, f"{type(e).__name__}: {e}", session)
            continue
        await finish(ids, STATUS_SENT, None, session)
        sent += 1
    return sent


# ── The bell ──────────────────────────────────────────────────────────────────


async def feed_filters(user: User, session: AsyncSession) -> Optional[list]:
    """The rows the user's bell may show, or None for none.

    Only their own in-app rows, and only for customers they still have whose
    notifications are still on: removing a user from a customer, or turning the switch
    off, takes the customer's notifications out of the bell too.
    """
    codes = await enabled_customer_codes(user, session)
    if not codes:
        return None
    return [
        CustomerPortalNotification.user_id == user.id,
        CustomerPortalNotification.in_app.is_(True),
        CustomerPortalNotification.customer_code.in_(codes),
    ]


async def list_feed(
    user: User,
    session: AsyncSession,
    limit: int = 20,
    before_id: Optional[int] = None,
) -> Tuple[List[CustomerPortalNotification], bool, int]:
    """A page of the user's bell, newest first: (rows, has_more, unread)."""
    filters = await feed_filters(user, session)
    if filters is None:
        return [], False, 0
    limit = max(1, min(limit, MAX_FEED_PAGE))
    query = select(CustomerPortalNotification).where(*filters)
    if before_id is not None:
        query = query.where(CustomerPortalNotification.id < before_id)
    rows = list((await session.execute(query.order_by(CustomerPortalNotification.id.desc()).limit(limit + 1))).scalars().all())
    unread = await unread_count(user, session, filters)
    return rows[:limit], len(rows) > limit, unread


async def unread_count(user: User, session: AsyncSession, filters: Optional[list] = None) -> int:
    filters = filters if filters is not None else await feed_filters(user, session)
    if filters is None:
        return 0
    result = await session.execute(
        select(func.count(CustomerPortalNotification.id)).where(*filters, CustomerPortalNotification.read_at.is_(None)),
    )
    return int(result.scalar() or 0)


async def mark_read(user: User, session: AsyncSession, ids: Optional[Sequence[int]] = None) -> int:
    """Mark the user's notifications read: the listed ones, or every one. Commits.

    Scoped to the caller's own rows, so an id from someone else's bell changes nothing.
    """
    query = update(CustomerPortalNotification).where(
        CustomerPortalNotification.user_id == user.id,
        CustomerPortalNotification.read_at.is_(None),
    )
    if ids is not None:
        if not ids:
            return 0
        query = query.where(CustomerPortalNotification.id.in_(list(ids)))
    result = await session.execute(query.values(read_at=now_utc()))
    await session.commit()
    return int(result.rowcount or 0)


# ── Keys ──────────────────────────────────────────────────────────────────────


def minute_marker(moment: Optional[datetime] = None) -> str:
    """A per-occurrence marker for an event without a stamp of its own: the minute it happened."""
    moment = to_naive_utc(moment) if moment else naive_now()
    return moment.replace(second=0, microsecond=0).isoformat()


def stamp_marker(stamp: Optional[datetime]) -> str:
    """A stored timestamp as a dedupe marker, falling back to the current minute."""
    return to_naive_utc(stamp).replace(microsecond=0).isoformat() if stamp else minute_marker()


def severity_label(severity: Optional[str]) -> str:
    """``severity`` as one of SEVERITY_LEVELS, for titles."""
    return normalize_severity(severity) or SEVERITY_LEVELS[3]
