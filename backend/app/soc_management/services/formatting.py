"""Human-readable figures for the PDF reports (the frontend has its own twins in TypeScript).

Pure functions; "no data" renders as an em dash or ``n/a``, never as 0.
"""

from typing import Optional

#: Compliance at or above this is green; at or above WARN is amber; below is red.
RATE_GOOD = 95.0
RATE_WARN = 85.0

EMPTY = "—"


def duration(seconds: Optional[float]) -> str:
    """``45s`` · ``12m`` · ``1h 20m`` · ``2d 4h``."""
    if seconds is None:
        return EMPTY
    total = int(round(seconds))
    if total < 60:
        return f"{total}s"
    minutes, _ = divmod(total, 60)
    if minutes < 60:
        return f"{minutes}m"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {minutes:02d}m" if minutes else f"{hours}h"
    days, hours = divmod(hours, 24)
    return f"{days}d {hours}h" if hours else f"{days}d"


def target(minutes: Optional[int]) -> str:
    return duration(minutes * 60) if minutes is not None else "no target"


def rate(value: Optional[float]) -> str:
    return f"{value:.1f}%" if value is not None else "n/a"


def rate_class(value: Optional[float]) -> str:
    if value is None:
        return "dim"
    if value >= RATE_GOOD:
        return "rate-good"
    if value >= RATE_WARN:
        return "rate-warn"
    return "rate-bad"


def delta(current: Optional[float], previous: Optional[float]) -> str:
    """Relative change vs the previous period: ``+12%``, ``−4%``, ``new``; empty when unknown."""
    if current is None or previous is None:
        return ""
    if previous == 0:
        return "new" if current else ""
    change = (current - previous) * 100.0 / previous
    if abs(change) < 0.5:
        return "±0%"
    sign = "+" if change > 0 else "−"
    return f"{sign}{abs(change):.0f}%"
