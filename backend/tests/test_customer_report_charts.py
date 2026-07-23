"""Unit tests for the customer-report matplotlib chart builders.

The charts are rendered server-side to base64 PNG ``data:`` URIs that get
embedded as ``<img>`` tags in the report. These tests assert the happy path
produces a valid PNG data URI and that the empty-data path degrades to a
placeholder image rather than raising.

Run with: cd backend && python -m pytest tests/test_customer_report_charts.py
"""
import base64

from app.incidents.services.customer_report_charts import donut_png
from app.incidents.services.customer_report_charts import evolution_png
from app.incidents.services.customer_report_charts import hbar_png

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _is_png_data_uri(uri: str) -> bool:
    if not uri.startswith("data:image/png;base64,"):
        return False
    raw = base64.b64decode(uri.split(",", 1)[1])
    return raw.startswith(_PNG_MAGIC)


def test_donut_renders_png_data_uri():
    assert _is_png_data_uri(donut_png([("Media", 764), ("Alta", 571), ("Baja", 116)]))


def test_donut_status_aware_renders():
    assert _is_png_data_uri(donut_png([("OPEN", 7), ("CLOSED", 9)], status_aware=True))


def test_donut_empty_is_placeholder_png():
    # Zero/empty data must still produce a valid PNG (empty-period safety).
    assert _is_png_data_uri(donut_png([]))
    assert _is_png_data_uri(donut_png([("a", 0), ("b", 0)]))


def test_hbar_renders_png_and_truncates_long_labels():
    # A very long label must not raise; the chart still renders.
    long_label = "Detección de Password Spraying vía SMTP Legacy (BAV2ROPC) involving multiple users"
    assert _is_png_data_uri(hbar_png([(long_label, 383), ("Command and control", 208)]))


def test_hbar_empty_is_placeholder_png():
    assert _is_png_data_uri(hbar_png([]))


def test_evolution_renders_png():
    assert _is_png_data_uri(evolution_png(["2026-05", "2026-06"], [10, 6]))


def test_evolution_empty_is_placeholder_png():
    assert _is_png_data_uri(evolution_png([], []))
