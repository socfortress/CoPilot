"""The channel provider contract.

Before this, delivery was an ``if/elif`` on ``route.channel`` inside
``dispatch()``, with a dedicated column set per channel on the route table.
Adding a channel meant a migration plus another branch — and #1000 needs four
more channels.

A provider owns everything channel-specific: how to read its config, how to
build the outgoing request, and what a successful send looks like. The dispatch
loop stays generic.

**In this phase providers still read the existing per-channel columns.** Moving
that configuration into a JSON ``config`` column is #1018 — deliberately a
separate change so the abstraction is proven against real dispatch behaviour
before a migration commits data to it.
"""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import ClassVar
from typing import Dict
from typing import Optional

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.schema.events import NotificationEvent


class SendResult(BaseModel):
    """Outcome of one delivery attempt.

    Generalizes the ``(status, error, latency_ms, shuffle_execution_id)`` tuple
    the dispatchers returned. ``provider_reference`` is the vendor-agnostic name
    for that last slot — Shuffle's execution id, and later Resend's message id.
    The dispatch-log *column* is still ``shuffle_execution_id`` until #1019
    renames it; the mapping happens in the dispatch loop.
    """

    status: str  # 'sent' | 'failed' | 'skipped'
    error_message: Optional[str] = None
    latency_ms: Optional[int] = None
    provider_reference: Optional[str] = None

    @classmethod
    def failed(cls, message: str, latency_ms: Optional[int] = 0) -> "SendResult":
        return cls(status="failed", error_message=message, latency_ms=latency_ms)

    @classmethod
    def skipped(cls, message: str, latency_ms: Optional[int] = 0) -> "SendResult":
        return cls(status="skipped", error_message=message, latency_ms=latency_ms)


class DispatchContext:
    """Per-dispatch-call shared state.

    Providers are stateless singletons held in the registry, so anything cached
    for the duration of one ``dispatch()`` call must live here rather than on
    the provider — otherwise concurrent dispatches would share it.

    ``memoize`` preserves the pre-refactor property that expensive lookups
    (the Shuffle connector row, an alert's AI report) are fetched at most once
    per dispatch call even when several routes need them. It is lazier than the
    code it replaces, which pre-fetched Shuffle credentials by scanning matched
    routes up front; the number of DB reads is the same or lower.
    """

    def __init__(self, session: AsyncSession, event: NotificationEvent) -> None:
        self.session = session
        self.event = event
        self._memo: Dict[str, Any] = {}

    async def memoize(self, key: str, factory: Callable[[], Awaitable[Any]]) -> Any:
        if key not in self._memo:
            self._memo[key] = await factory()
        return self._memo[key]


class ChannelProvider(ABC):
    """One delivery channel.

    Subclasses are instantiated once at import time and registered by ``key``.
    They must be stateless — see ``DispatchContext``.
    """

    #: Value stored in ``customer_notification_route.channel``.
    key: ClassVar[str]

    #: Human label for the route form's channel picker.
    display_name: ClassVar[str]

    @abstractmethod
    async def send(
        self,
        *,
        route: Any,
        event: NotificationEvent,
        rendered_body: str,
        ctx: DispatchContext,
    ) -> SendResult:
        """Deliver one notification.

        Must not raise: return ``SendResult.failed(...)`` instead. The dispatch
        loop does catch exceptions as a backstop, but a provider that raises
        produces a generic "Dispatcher exception" message in the log rather than
        something an operator can act on.

        ``route`` is the ORM row. Read what you need from it **before** the
        first ``await`` — an expired SQLAlchemy object triggers an implicit
        refresh on attribute access, which throws ``MissingGreenlet`` under
        ``AsyncSession``.
        """

    async def after_send(self, *, route: Any, result: SendResult, ctx: DispatchContext) -> None:
        """Optional side effect after a successful send, inside the same commit.

        Used by Shuffle to stamp ``last_used_at`` on the integration row. Called
        only when ``result.status == "sent"``.
        """
        return None
