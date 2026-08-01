"""Channel provider registry.

The single place that knows which delivery channels exist. Adding a channel is
one module plus one line here — no migration, no dispatch-loop edit, and (once
#1018 lands) no route-form work either, because the form renders from each
provider's declared config schema.

Kept deliberately small: the registry maps ``key -> provider instance``, and
providers are stateless singletons (per-dispatch state lives on
``DispatchContext``).
"""

from __future__ import annotations

from typing import Dict
from typing import List
from typing import Optional

from app.notifications.channels.base import ChannelProvider
from app.notifications.channels.base import DispatchContext
from app.notifications.channels.base import SendResult
from app.notifications.channels.resend import ResendChannel
from app.notifications.channels.shuffle import ShuffleChannel
from app.notifications.channels.teams import TeamsChannel
from app.notifications.channels.webhook import WebhookChannel

_PROVIDERS: List[ChannelProvider] = [
    ShuffleChannel(),
    WebhookChannel(),
    ResendChannel(),
    TeamsChannel(),
]

CHANNEL_REGISTRY: Dict[str, ChannelProvider] = {p.key: p for p in _PROVIDERS}


def get_channel(key: str) -> Optional[ChannelProvider]:
    """Look up a provider, or None for an unknown channel.

    Returns None rather than raising so the dispatch loop can record an
    unsupported channel as a per-route failure — a misconfigured row surfaces in
    the dispatch log instead of aborting the batch.
    """
    return CHANNEL_REGISTRY.get(key)


def channel_keys() -> List[str]:
    return list(CHANNEL_REGISTRY.keys())


__all__ = [
    "CHANNEL_REGISTRY",
    "ChannelProvider",
    "DispatchContext",
    "SendResult",
    "channel_keys",
    "get_channel",
]
