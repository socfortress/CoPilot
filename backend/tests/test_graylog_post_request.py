"""Graylog POST helper (connectors/graylog/utils/universal.py): every 2xx is a success.

Graylog 7 answers ``POST /api/streams/{id}/outputs`` with 202 Accepted and an empty body; the helper
used to accept only 200/201/204, read the empty body as JSON, and fail the call that had worked
(UBA setup on the lab, 2026-10-04). Errors with a non-JSON body keep their text.

Run with: cd backend && python -m pytest tests/test_graylog_post_request.py
"""

import asyncio
import os
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.connectors.graylog.utils.universal as universal  # noqa: E402


class Response:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text

    def json(self):
        import json

        return json.loads(self.text)


def _post(response):
    @asynccontextmanager
    async def session():
        yield None

    async def attributes(name, session):
        return {"connector_url": "http://graylog.example:9000", "connector_username": "admin", "connector_password": "x"}

    async def blocking(*args, **kwargs):
        return response

    with patch.object(universal, "get_db_session", session), patch.object(
        universal,
        "get_connector_info_from_db",
        attributes,
    ), patch.object(universal, "run_blocking", blocking):
        return asyncio.run(universal.send_post_request("/api/streams/s1/outputs", {"outputs": ["o1"]}, connector_name="Graylog"))


def test_202_accepted_with_an_empty_body_is_a_success():
    out = _post(Response(202, ""))
    assert out["success"] is True and out["data"] is None


def test_201_with_a_body_returns_it():
    assert _post(Response(201, '{"stream_id": "s2"}'))["data"] == {"stream_id": "s2"}


def test_an_error_without_a_json_body_keeps_its_text():
    with pytest.raises(HTTPException) as e:
        _post(Response(502, "Bad Gateway"))
    assert "Bad Gateway" in e.value.detail


def test_an_error_with_a_json_message_reports_it():
    with pytest.raises(HTTPException) as e:
        _post(Response(400, '{"type": "ApiError", "message": "Unable to map property"}'))
    assert "Unable to map property" in e.value.detail
