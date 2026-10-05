"""Duration statistics.

The headline figure is the **median**, not the mean: one bulk close of five hundred
week-old noise alerts moves a mean by hours and a median by nothing. The mean is still
reported (the issue asks for averages, and managers compare it to contracts written in
averages), next to the 90th percentile that shows the tail the median hides.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable
from typing import List
from typing import Optional
from typing import Sequence


@dataclass(frozen=True)
class DurationStats:
    count: int = 0
    mean: Optional[float] = None
    median: Optional[float] = None
    p90: Optional[float] = None


def percentile(sorted_values: Sequence[float], q: float) -> Optional[float]:
    """Linear-interpolated percentile (``q`` in [0, 100]) of already-sorted values."""
    if not sorted_values:
        return None
    if not 0 <= q <= 100:
        raise ValueError("q must be within [0, 100]")
    position = (len(sorted_values) - 1) * q / 100.0
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(sorted_values[lower])
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def describe(seconds: Iterable[Optional[float]]) -> DurationStats:
    """Stats over durations in seconds; ``None`` and negative values are ignored.

    A negative duration means a clock skew between the event and the row it is measured
    from; dropping it is safer than letting it pull an average below zero.
    """
    values: List[float] = sorted(v for v in seconds if v is not None and v >= 0)
    if not values:
        return DurationStats()
    return DurationStats(
        count=len(values),
        mean=round(sum(values) / len(values), 1),
        median=round(percentile(values, 50), 1),
        p90=round(percentile(values, 90), 1),
    )
