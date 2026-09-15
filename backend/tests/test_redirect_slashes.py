"""
Unmatched paths must be a 404, never a redirect (#1133).

Starlette's default `redirect_slashes` answers an unmatched `/x/` with a 307 whose
Location is rebuilt from the ASGI scope. Behind nginx that is an absolute
`http://<host>/api/x` (uvicorn trusts X-Forwarded-Proto only from 127.0.0.1), the
browser follows it across origins and drops the Authorization header, the backend
answers 401, and the frontend logs the user out. Typing `C:\\` into the Ctrl+K
palette was enough to trigger it: the browser rewrites the backslash into a slash.

Run with: cd backend && python -m pytest tests/test_redirect_slashes.py
"""

import os

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi.testclient import TestClient  # noqa: E402

TITLE_ROUTE = "/api/incidents/db_operations/alerts/title"


def _client():
    import copilot

    # No `with` block: the lifespan (migrations, MySQL, MinIO) must not run here.
    return TestClient(copilot.app, base_url="https://copilot.example")


def test_redirect_slashes_is_disabled():
    import copilot

    assert copilot.app.router.redirect_slashes is False


def test_a_browser_rewritten_backslash_is_a_404_not_a_redirect():
    client = _client()

    for path in (f"{TITLE_ROUTE}/C:/", f"{TITLE_ROUTE}/C://"):
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 404, f"{path} -> {response.status_code}"
        assert "location" not in response.headers, f"{path} still redirects to {response.headers.get('location')}"


def test_an_encoded_backslash_reaches_the_title_route():
    """The path the fixed frontend sends resolves to the route (auth rejects it, not routing)."""
    client = _client()

    response = client.get(f"{TITLE_ROUTE}/C%3A%5C%5C", follow_redirects=False)

    assert response.status_code in (401, 403), response.text
    assert "location" not in response.headers
