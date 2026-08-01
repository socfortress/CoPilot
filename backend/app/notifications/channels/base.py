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

import json
from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import ClassVar
from typing import Dict
from typing import Optional
from typing import Set
from typing import Type

from pydantic import BaseModel
from pydantic import ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.schema.events import NotificationEvent


class SendResult(BaseModel):
    """Outcome of one delivery attempt.

    Generalizes the ``(status, error, latency_ms, shuffle_execution_id)`` tuple
    the dispatchers returned. ``provider_reference`` is the vendor-agnostic name
    for that last slot — Shuffle's execution id, and later Resend's message id.
    It maps straight onto the dispatch log's column of the same name.
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


class ChannelConfig(BaseModel):
    """Base for a provider's ``config`` shape.

    ``extra="forbid"`` on purpose: a typo'd key should be a 400 at save time,
    not a setting that silently does nothing until someone debugs why their
    webhook has no auth header.
    """

    model_config = ConfigDict(extra="forbid")


class ChannelProvider(ABC):
    """One delivery channel.

    Subclasses are instantiated once at import time and registered by ``key``.
    They must be stateless — see ``DispatchContext``.
    """

    #: Value stored in ``customer_notification_route.channel``.
    key: ClassVar[str]

    #: Human label for the route form's channel picker.
    display_name: ClassVar[str]

    #: Validates ``customer_notification_route.config``. The API validates
    #: against this at save time and the route form renders from its JSON
    #: schema, so a new channel needs neither a migration nor bespoke form work.
    config_schema: ClassVar[Type[ChannelConfig]]

    #: Which ``recipient_mode`` values make sense here. A webhook targets a
    #: fixed URL so it cannot resolve an assignee; email can.
    supports_recipient_modes: ClassVar[Set[str]] = {"static"}

    #: Config keys holding secrets. Encrypted at rest and redacted on read in
    #: #1020; declared here so providers own the classification.
    secret_fields: ClassVar[Set[str]] = set()

    def parse_config(self, route: Any) -> ChannelConfig:
        """Validate and return this route's config.

        Raises ``ValueError`` on malformed JSON or a shape mismatch. Providers
        call this at the top of ``send`` and convert failures into a logged
        per-route failure rather than letting them abort the batch.
        """
        raw = getattr(route, "config", None)
        if not raw:
            return self.config_schema()
        try:
            data = json.loads(raw)
        except ValueError as e:
            raise ValueError(f"config is not valid JSON: {e}") from e
        if not isinstance(data, dict):
            raise ValueError("config must be a JSON object")
        return self.config_schema.model_validate(data)

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
