"""This CoPilot's report secret, the customer pseudonyms and the per-customer send time (jitter).

The ``customer`` of a report is ``cust_`` + the first 32 hex of HMAC-SHA256(report secret, a label + the customer code),
as sysmon-sync's README ("How CoPilot reports") asks. The secret is 32 random bytes CoPilot generates once and keeps in
its database (``sysmon_stats_identity``); it is never keyed with the license key, which SOCFortress sees and could then
use to recompute pseudonyms from guessed customer codes. The secret is never logged, returned or audited.
"""
import hashlib
import hmac
import re
import secrets
from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.universal_models import SysmonStatsIdentity

CUSTOMER_LABEL = b"socfortress-sysmon-report-customer/1\x00"
JITTER_LABEL = b"socfortress-sysmon-report-jitter/1\x00"
_SECRET_RE = re.compile(r"[0-9a-f]{64}")
# The send time is Monday 01:00 UTC plus 0..47 hours: between Monday 01:00 and Tuesday 23:59
JITTER_START_HOURS = 1
JITTER_SPAN_HOURS = 47


def customer_pseudonym(secret: bytes, customer_code: str) -> str:
    """The customer's id in this CoPilot's reports: cust_ + 32 lowercase hex. The code exactly as stored."""
    digest = hmac.new(secret, CUSTOMER_LABEL + customer_code.encode("utf-8"), hashlib.sha256).hexdigest()
    return "cust_" + digest[:32]


def week_label(monday: date) -> str:
    iso = monday.isocalendar()
    return f"{iso[0]:04d}-W{iso[1]:02d}"


def due_time(secret: bytes, customer_code: str, week: str, week_monday: date) -> datetime:
    """When this CoPilot sends ``week``'s report for the customer: the Monday after the week, 01:00 UTC, plus a
    deterministic 0..47 hours (per CoPilot and customer), so a fleet of CoPilots does not report at once."""
    digest = hmac.new(
        secret,
        JITTER_LABEL + week.encode("ascii") + b"\x00" + customer_code.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    hours = int.from_bytes(digest[:4], "big") % (JITTER_SPAN_HOURS * 3600)
    start = datetime(week_monday.year, week_monday.month, week_monday.day, tzinfo=timezone.utc) + timedelta(days=7)
    return start + timedelta(hours=JITTER_START_HOURS, seconds=hours)


async def load_secret(session: AsyncSession, create: bool = True) -> Optional[bytes]:
    """
    The report secret, created on first use when ``create`` (committed). Two replicas creating it at once: the second
    INSERT fails on the primary key and the winner's secret is read instead. None when there is none and ``create`` is
    off, or the stored one is unusable (logged without its value).
    """
    row = (await session.execute(select(SysmonStatsIdentity).where(SysmonStatsIdentity.id == 1))).scalars().first()
    if row is not None:
        return _usable(row.report_secret)
    if not create:
        return None
    session.add(SysmonStatsIdentity(id=1, report_secret=secrets.token_hex(32), created_at=_naive_now()))
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
    row = (await session.execute(select(SysmonStatsIdentity).where(SysmonStatsIdentity.id == 1))).scalars().first()
    return _usable(row.report_secret) if row is not None else None


def _usable(value: Optional[str]) -> Optional[bytes]:
    if not isinstance(value, str) or not _SECRET_RE.fullmatch(value):
        logger.error("Sysmon stats: the stored report secret is not 64 lowercase hex; no report is sent")
        return None
    return bytes.fromhex(value)


def _naive_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
