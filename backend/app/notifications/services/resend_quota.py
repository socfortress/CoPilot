"""Resend send counting — per-route throttle and deployment-wide monthly usage.

Resend's free tier is 1,000 emails/month across the **whole deployment**, not
per customer or per route, because the API key is deployment-wide. That makes it
a shared resource one noisy route can exhaust for everyone.

Both counts are derived from `notification_dispatch_log` rather than kept in a
counter column: the log is already the record of what was sent, and a separate
counter would be one more thing to keep in step.

Only `sent` rows count. A `failed` send never reached Resend, and a `skipped`
one never left the process.
"""

from __future__ import annotations

from datetime import datetime
from datetime import timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.universal_models import CustomerNotificationRoute
from app.db.universal_models import NotificationDispatchLog

RESEND_CHANNEL_KEY = "resend"


async def sends_in_last_hour(route_id: int, session: AsyncSession) -> int:
    """Successful sends for one route in the trailing hour.

    Backs the per-route `max_per_hour` throttle. Trailing window rather than a
    clock hour, so a burst can't straddle the boundary and send twice the limit.
    """
    since = datetime.utcnow() - timedelta(hours=1)
    result = await session.execute(
        select(func.count())
        .select_from(NotificationDispatchLog)
        .where(
            NotificationDispatchLog.route_id == route_id,
            NotificationDispatchLog.status == "sent",
            NotificationDispatchLog.dispatched_at >= since,
        ),
    )
    return int(result.scalar() or 0)


async def sends_this_month(session: AsyncSession, customer_code: Optional[str] = None) -> int:
    """Successful email sends this calendar month, deployment-wide by default.

    Calendar month, not trailing 30 days, because that's how Resend bills and
    resets — a trailing window would disagree with their dashboard.

    `customer_code` narrows it for display purposes only. The quota itself is
    never per-customer: every customer draws from the same account.
    """
    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)

    stmt = (
        select(func.count())
        .select_from(NotificationDispatchLog)
        .join(CustomerNotificationRoute, CustomerNotificationRoute.id == NotificationDispatchLog.route_id)
        .where(
            CustomerNotificationRoute.channel == RESEND_CHANNEL_KEY,
            NotificationDispatchLog.status == "sent",
            NotificationDispatchLog.dispatched_at >= month_start,
        )
    )
    if customer_code:
        stmt = stmt.where(CustomerNotificationRoute.customer_code == customer_code)

    result = await session.execute(stmt)
    return int(result.scalar() or 0)
