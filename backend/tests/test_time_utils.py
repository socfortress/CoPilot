"""``now_utc()`` replaces the deprecated, naive ``datetime.utcnow()``.

Run with: cd backend && python -m pytest tests/test_time_utils.py
"""

import os
from datetime import timedelta
from datetime import timezone
from pathlib import Path

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.customer_portal as customer_portal  # noqa: E402
from app.db.universal_models import CustomerPortalAiReportSettings  # noqa: E402
from app.db.universal_models import CustomerPortalBranding  # noqa: E402
from app.db.universal_models import CustomerPortalSettings  # noqa: E402
from app.time_utils import now_utc  # noqa: E402


def test_now_utc_is_timezone_aware_utc():
    assert now_utc().utcoffset() == timedelta(0)
    assert now_utc().tzinfo is timezone.utc


def test_it_is_stored_as_the_same_wall_clock_time_utcnow_produced():
    from pymysql.converters import escape_datetime

    moment = now_utc()
    assert escape_datetime(moment) == escape_datetime(moment.replace(tzinfo=None))


@pytest.mark.parametrize("model", [CustomerPortalSettings, CustomerPortalBranding, CustomerPortalAiReportSettings])
def test_portal_models_default_to_aware_utc(model):
    assert model(customer_code="ACME").updated_at.tzinfo is timezone.utc


def test_customer_portal_no_longer_calls_utcnow():
    package = Path(list(customer_portal.__path__)[0])
    offenders = [str(path.relative_to(package)) for path in package.rglob("*.py") if "utcnow" in path.read_text()]
    assert offenders == []
