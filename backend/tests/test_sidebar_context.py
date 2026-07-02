from datetime import datetime
from datetime import timedelta

from app.status.services.context_indicators import _is_scheduler_job_stale


def test_scheduler_job_stale_when_never_ran() -> None:
    now = datetime(2026, 1, 1, 12, 0, 0)
    assert _is_scheduler_job_stale(last_success=None, time_interval_minutes=15, now=now) is True


def test_scheduler_job_stale_when_overdue() -> None:
    now = datetime(2026, 1, 1, 12, 0, 0)
    last_success = now - timedelta(minutes=40)
    assert _is_scheduler_job_stale(last_success=last_success, time_interval_minutes=15, now=now) is True


def test_scheduler_job_healthy_when_recent() -> None:
    now = datetime(2026, 1, 1, 12, 0, 0)
    last_success = now - timedelta(minutes=10)
    assert _is_scheduler_job_stale(last_success=last_success, time_interval_minutes=15, now=now) is False
