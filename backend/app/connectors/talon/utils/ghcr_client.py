"""The HTTP client behind the talon-analyst release check (``services/talon_release.py``).

talon-analyst ships as public images on GHCR (``ghcr.io/socfortress/talon-analyst-api``). Its source
repository is private, so GitHub's releases API is no use from a client site: the registry's tag
list is the source of truth. GHCR lists a public image's tags anonymously: an anonymous pull token
from ``/token``, then ``/v2/<repository>/tags/list`` with that token.

What leaves CoPilot, and where to:

- Only ``https://ghcr.io``, TLS verified, no redirect followed. A ``Link`` to the next page is
  followed only when it stays on that host and on the same tags path.
- Plain GETs: the token request names only the repository and the pull scope, and the tags request
  carries only that anonymous token. No CoPilot or customer data, and no CoPilot version in a header.
- The host's proxy settings apply (httpx's default ``trust_env``), so a CoPilot that reaches the
  internet through a proxy reaches GHCR the same way. Nothing secret is sent for a proxy to see.

Bounded: one deadline for the whole lookup (``TIMEOUT_SECONDS``: the token and every page), at most
``MAX_PAGES`` pages, each read raw and capped (``capped_body``: an encoded answer is refused, never
inflated). Every failure is a ``GhcrError`` whose text is fixed, plus at most an exception's class
name: an exception's own text names hosts and ports, so it is never kept.
"""
import json
import re
from typing import Any
from typing import List
from typing import Optional
from typing import Tuple

import anyio
import httpx

from app.connectors.talon.utils import capped_body

GHCR_HOST = "ghcr.io"
GHCR = f"https://{GHCR_HOST}"
REPOSITORY = "socfortress/talon-analyst-api"
TOKEN_URL = f"{GHCR}/token?scope=repository:{REPOSITORY}:pull&service={GHCR_HOST}"
TAGS_PATH = f"/v2/{REPOSITORY}/tags/list"

#: Seconds for the whole lookup: the token and every page of tags.
TIMEOUT_SECONDS = 3.0
PAGE_SIZE = 1000
#: GHCR lists tags in push order, so the newest release is on the last page: every page is read.
MAX_PAGES = 50
MAX_BODY_BYTES = 1024 * 1024
MAX_TAGS = 100_000
MAX_TAG_CHARS = 128
#: A bearer token's characters (RFC 6750 ``b64token``), bounded.
_TOKEN = re.compile(r"[A-Za-z0-9._~+/-]{1,8192}=*")
_NEXT = re.compile(r'<([^<>]*)>\s*;\s*rel="?next"?', re.IGNORECASE)


class GhcrError(Exception):
    """GHCR gave no usable tag list. The text is fixed, plus at most an exception's class name."""


def _new_client() -> httpx.AsyncClient:
    """One client per lookup (tests replace this to mock the transport)."""
    return httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT_SECONDS), follow_redirects=False)


async def _get_json(client: httpx.AsyncClient, url: str, headers: dict) -> Tuple[Any, Optional[str]]:
    """A GET's JSON body and its ``Link`` header, or ``GhcrError``."""
    async with client.stream("GET", url, headers=headers) as response:
        if response.status_code != 200:
            raise GhcrError(f"GHCR answered {response.status_code}")
        try:
            body = await capped_body.read_capped(response, MAX_BODY_BYTES)
        except capped_body.EncodedBody:
            raise GhcrError("GHCR's answer was compressed; not read") from None
        if body is None:
            raise GhcrError("GHCR's answer was too large")
        link = response.headers.get("link")
    try:
        return json.loads(body), link
    except (ValueError, RecursionError):  # ValueError includes UnicodeDecodeError
        raise GhcrError("GHCR's answer was not valid JSON") from None


def next_page(link: Optional[str]) -> Optional[str]:
    """The next page's URL from a ``Link`` header, or None on the last page. A next page anywhere
    but GHCR's tags path for this repository is a ``GhcrError``, never followed."""
    match = _NEXT.search(link or "")
    if match is None:
        return None
    try:
        url = httpx.URL(GHCR).join(match.group(1))
    except (httpx.InvalidURL, ValueError):
        raise GhcrError("GHCR's next page is not a URL; not followed") from None
    if url.scheme != "https" or url.host != GHCR_HOST or url.port not in (None, 443) or url.userinfo or url.path != TAGS_PATH:
        raise GhcrError("GHCR's next page is not on GHCR's tags path; not followed")
    return str(url)


async def _token(client: httpx.AsyncClient) -> str:
    document, _ = await _get_json(client, TOKEN_URL, {"Accept": "application/json", "Accept-Encoding": "identity"})
    token = document.get("token") if isinstance(document, dict) else None
    if not isinstance(token, str) or not _TOKEN.fullmatch(token):
        raise GhcrError("GHCR's token answer was not in the expected shape")
    return token


async def _tags(client: httpx.AsyncClient, token: str) -> List[str]:
    headers = {"Accept": "application/json", "Accept-Encoding": "identity", "Authorization": f"Bearer {token}"}
    url: Optional[str] = f"{GHCR}{TAGS_PATH}?n={PAGE_SIZE}"
    seen = set()
    tags: List[str] = []
    for _ in range(MAX_PAGES):
        if url is None:
            return tags
        if url in seen:
            raise GhcrError("GHCR's next page repeats an earlier one; not followed")
        seen.add(url)
        document, link = await _get_json(client, url, headers)
        page = document.get("tags") if isinstance(document, dict) else None
        if page is None and isinstance(document, dict) and "tags" in document:
            page = []  # an image without tags lists them as null
        if not isinstance(page, list):
            raise GhcrError("GHCR's tag list was not in the expected shape")
        tags.extend(tag for tag in page if isinstance(tag, str) and len(tag) <= MAX_TAG_CHARS)
        if len(tags) > MAX_TAGS:
            raise GhcrError(f"GHCR listed more than {MAX_TAGS} tags")
        url = next_page(link)
    if url is not None:
        raise GhcrError(f"GHCR's tag list is longer than {MAX_PAGES} pages")
    return tags


async def fetch_tags() -> List[str]:
    """Every tag of ``ghcr.io/socfortress/talon-analyst-api``, or ``GhcrError``."""
    try:
        with anyio.fail_after(TIMEOUT_SECONDS):
            async with _new_client() as client:
                return await _tags(client, await _token(client))
    except GhcrError:
        raise
    except TimeoutError:
        raise GhcrError(f"GHCR did not answer within {TIMEOUT_SECONDS:g} s") from None
    except httpx.TimeoutException as e:
        raise GhcrError(f"GHCR did not answer within {TIMEOUT_SECONDS:g} s ({type(e).__name__})") from None
    except Exception as e:  # noqa: BLE001 - a transport error, a TLS failure, a malformed answer
        raise GhcrError(f"GHCR could not be reached ({type(e).__name__})") from None
