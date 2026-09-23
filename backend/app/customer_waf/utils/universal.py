"""
HTTP transport to a SOCFortress WAF admin API.

One ``CustomerWafInstance`` row → one client: ``Authorization: Bearer wafst_…``,
TLS verified against the row's CA (or the system bundle, or not at all when the
operator turned it off). Everything CoPilot asks a WAF goes through ``waf_get`` /
``waf_request``, so the error mapping below applies uniformly.

**Error mapping is load-bearing.** A WAF 401/403 must never surface as a CoPilot
401/403: the frontend treats a 401 from our own API as a lost session and logs the
analyst out (``frontend/src/api/session-expiry.ts``). Upstream failures are
therefore 502 Bad Gateway with a ``reason`` the UI can explain — the analyst's
CoPilot session is fine, the WAF said no.

The token is decrypted per request and lives only in the outgoing header. Nothing
here logs it, the ciphertext, or the headers.
"""

import ssl
from typing import Any
from typing import Dict
from typing import Optional
from urllib.parse import urlparse

import httpx
from loguru import logger

from app.customer_waf.services.crypto import decrypt_token

API_PREFIX = "/api/v1"
DEFAULT_TIMEOUT = 15.0


class WafRequestError(Exception):
    """A WAF call failed. ``reason`` is a stable code for the UI; ``detail`` is for humans."""

    def __init__(self, reason: str, detail: str, status_code: int = 502):
        super().__init__(detail)
        self.reason = reason
        self.detail = detail
        self.status_code = status_code


def normalize_api_url(api_url: str) -> str:
    """Canonical base URL: scheme + host (+ path prefix), no trailing slash, no ``/api/v1``.

    Operators paste the admin UI URL (``https://waf:8080``), the API root, or the full
    ``…/api/v1`` — all three must address the same thing.
    """
    url = (api_url or "").strip().rstrip("/")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("api_url must be a full http:// or https:// URL, e.g. https://waf.example.com:8080")
    if url.endswith(API_PREFIX):
        url = url[: -len(API_PREFIX)]
    return url


def build_ssl_verify(verify_tls: bool, ca_cert_pem: Optional[str]):
    """httpx ``verify`` value: a context trusting the row's CA, the system bundle, or off.

    Off is the default (see ``WafInstanceCreate.verify_tls``): a stock WAF's self-signed
    certificate covers only 127.0.0.1 / localhost / admin-ui, so verification would fail
    against every fresh install. The traffic is still encrypted; what is given up is
    proof of the WAF's identity, which is acceptable on the private network or VPN the
    WAF admin API should sit on anyway.
    """
    if not verify_tls:
        return False
    if ca_cert_pem:
        # Raises ssl.SSLError on an unparsable PEM — callers validate at save time.
        return ssl.create_default_context(cadata=ca_cert_pem)
    return True


def _make_client(instance, timeout: float) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=normalize_api_url(instance.api_url),
        verify=build_ssl_verify(instance.verify_tls, instance.ca_cert_pem),
        timeout=timeout,
        headers={
            "Authorization": f"Bearer {decrypt_token(instance.service_token_encrypted)}",
            "Accept": "application/json",
        },
    )


def _upstream_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return ""
    detail = body.get("detail") if isinstance(body, dict) else None
    return detail if isinstance(detail, str) else ""


async def waf_request(
    instance,
    method: str,
    path: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json: Any = None,
    timeout: float = DEFAULT_TIMEOUT,
    api: bool = True,
    allow_disabled: bool = False,
) -> Any:
    """Call the WAF and return its decoded JSON body, or raise ``WafRequestError``.

    ``path`` is relative to ``/api/v1`` unless ``api=False`` (used for ``/health``).
    ``allow_disabled`` is for the connection test only, so an admin can check a WAF
    before switching it on.
    """
    if not instance.enabled and not allow_disabled:
        raise WafRequestError("disabled", f"WAF '{instance.name}' is disabled in CoPilot", status_code=409)

    url = f"{API_PREFIX}{path}" if api else path
    where = f"WAF {instance.id} ({instance.customer_code}/{instance.name})"
    try:
        async with _make_client(instance, timeout) as client:
            response = await client.request(method, url, params=params, json=json)
    except httpx.TimeoutException:
        logger.warning(f"{where}: timed out on {method} {url}")
        raise WafRequestError("unreachable", f"WAF '{instance.name}' did not respond within {timeout:.0f}s")
    except ssl.SSLError as e:
        raise WafRequestError("tls_error", f"TLS verification failed for WAF '{instance.name}': {e}")
    except httpx.ConnectError as e:
        # httpx wraps certificate failures in ConnectError; tell them apart for the operator.
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            raise WafRequestError(
                "tls_error",
                f"TLS verification failed for WAF '{instance.name}'. Upload a trusted certificate on the WAF, "
                "or add its CA certificate here.",
            )
        logger.warning(f"{where}: connection failed on {method} {url}: {type(e).__name__}")
        raise WafRequestError("unreachable", f"Could not connect to WAF '{instance.name}' at {normalize_api_url(instance.api_url)}")
    except httpx.HTTPError as e:
        logger.warning(f"{where}: {method} {url} failed: {type(e).__name__}")
        raise WafRequestError("unreachable", f"Request to WAF '{instance.name}' failed: {type(e).__name__}")

    if response.status_code == 401:
        raise WafRequestError(
            "token_rejected",
            f"WAF '{instance.name}' rejected the service token — it was revoked, disabled or expired, "
            "or its WAF user was disabled. Issue a new token in the WAF and update it here.",
        )
    if response.status_code == 403:
        upstream = _upstream_detail(response)
        raise WafRequestError(
            "insufficient_role",
            f"The token's WAF user lacks permission for this action ({upstream or 'forbidden'}). Give that user a broader role in the WAF.",
        )
    if response.status_code == 404:
        raise WafRequestError("not_found", _upstream_detail(response) or f"Not found on WAF '{instance.name}'", status_code=404)
    if response.status_code >= 400:
        logger.warning(f"{where}: {method} {url} returned HTTP {response.status_code}")
        raise WafRequestError("upstream_error", f"WAF '{instance.name}' returned HTTP {response.status_code}")

    if response.status_code == 204:
        return None
    try:
        return response.json()
    except ValueError:
        # Typically an api_url that reaches the admin UI's SPA instead of the API.
        raise WafRequestError(
            "bad_response",
            f"WAF '{instance.name}' returned a non-JSON response for {url} — check the API URL points at the WAF admin UI/API.",
        )


async def waf_get(instance, path: str, *, params: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    return await waf_request(instance, "GET", path, params=params, **kwargs)
