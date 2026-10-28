"""The Threat Intel sources behind the portal's IOC enrichment (#1318): VirusTotal and OpenCTI.

Everything here is about one value and one source: what kind of value it is, whether a source
may be asked about it, the request, and the projection of the answer the portal may show. The
rules about who may ask, the cache and the daily limit are in ``ioc_enrichment.py``.

- **Nothing private leaves CoPilot.** A private, loopback or reserved address, and a name under
  a TLD that only exists inside a network (``.local``, ``.corp``, …), is ``internal`` and never
  sent anywhere; a value VirusTotal cannot look up (an e-mail, a file name) goes to OpenCTI only,
  which the SOC runs itself.
- **VirusTotal is read, never written.** Only ``GET``: an IP, a domain, a file hash, or a URL by
  its identifier. A URL is never submitted for scanning, which would publish it.
- **OpenCTI is filtered by marking.** An object whose marking is beyond what the SOC may pass to
  a client (TLP:RED, TLP:AMBER+STRICT, any other statement) is left out; an observable left out
  is as good as not found, so its existence never shows either.
- **Answers are projections**: bounded strings without control or formatting characters, a few
  numbers and dates. A source's error text never leaves this module; the portal gets a code.
"""

import asyncio
import base64
import ipaddress
import json
import re
import unicodedata
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union
from urllib.parse import quote
from urllib.parse import urlsplit

import httpx
from loguru import logger

from app.connectors.opencti.services.queries import OBSERVABLE_LOOKUP_KEYS
from app.connectors.opencti.services.queries import PORTAL_OBSERVABLE_QUERY
from app.connectors.opencti.utils.universal import OPENCTI_CONNECTOR_NAME
from app.connectors.opencti.utils.universal import filter_group
from app.connectors.opencti.utils.universal import filter_item
from app.connectors.opencti.utils.universal import send_graphql_request
from app.connectors.utils import get_connector_info_from_db
from app.customer_portal.schema.ioc_enrichment import OpenCtiDetails
from app.customer_portal.schema.ioc_enrichment import OpenCtiIndicator
from app.customer_portal.schema.ioc_enrichment import OpenCtiReport
from app.customer_portal.schema.ioc_enrichment import VirusTotalDetails
from app.db.db_session import get_db_session

VIRUSTOTAL = "virustotal"
OPENCTI = "opencti"
SOURCES = (VIRUSTOTAL, OPENCTI)
VIRUSTOTAL_CONNECTOR_NAME = "VirusTotal"
VIRUSTOTAL_DEFAULT_URL = "https://www.virustotal.com/api/v3"

#: Longer values are not looked up anywhere.
MAX_VALUE_LENGTH = 2048
#: A VirusTotal answer larger than this is no answer (a domain's carries its DNS and certificates).
MAX_VIRUSTOTAL_BYTES = 4 * 1024 * 1024
#: One source's request, all in.
SOURCE_TIMEOUT_SECONDS = 15.0
VIRUSTOTAL_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

#: At least this many engines calling it malicious makes VirusTotal's verdict malicious; fewer, or
#: any suspicious, is suspicious. One or two engines alone are too often a false positive.
VIRUSTOTAL_MALICIOUS_ENGINES = 3
#: OpenCTI's 0–100 score.
OPENCTI_MALICIOUS_SCORE = 70
OPENCTI_SUSPICIOUS_SCORE = 40

#: Observables, and indicators and reports per observable, read from OpenCTI and shown at most.
OPENCTI_OBSERVABLES = 5
OPENCTI_INDICATORS = 5
OPENCTI_REPORTS = 5
MAX_TAGS = 10
MAX_LABELS = 10

#: The markings an object may carry and still be shown to a customer. TLP:AMBER may go to a
#: recipient's clients; AMBER+STRICT and RED may not. PAP markings say what may be done with the
#: data, not who may read it. An object without a marking is shown.
SHAREABLE_TLP = frozenset({"TLP:CLEAR", "TLP:WHITE", "TLP:GREEN", "TLP:AMBER"})

#: Names that only exist inside a network: never sent to VirusTotal (RFC 2606, 6761, 6762 and
#: common private choices).
INTERNAL_TLDS = frozenset(
    {"local", "localdomain", "localhost", "internal", "intranet", "lan", "corp", "home", "private", "arpa", "test", "invalid", "example"},
)

#: The last part of a file name that reads like a domain ("invoice.pdf.exe") and is no TLD: a file
#: name is not sent to VirusTotal as a domain. Extensions that are also TLDs (.zip, .py, .sh) can't
#: be told apart and stay domains.
FILE_EXTENSIONS = frozenset(
    {
        "exe",
        "dll",
        "sys",
        "scr",
        "msi",
        "bat",
        "cmd",
        "vbs",
        "vbe",
        "jse",
        "wsf",
        "hta",
        "lnk",
        "js",
        "jar",
        "pdf",
        "doc",
        "docx",
        "docm",
        "xls",
        "xlsx",
        "xlsm",
        "ppt",
        "pptx",
        "rtf",
        "txt",
        "csv",
        "log",
        "json",
        "xml",
        "tmp",
        "dat",
        "bin",
        "iso",
        "img",
        "rar",
        "gz",
        "tar",
        "tgz",
    },
)

_HASH = re.compile(r"[0-9a-f]{32}|[0-9a-f]{40}|[0-9a-f]{64}")
_DOMAIN = re.compile(r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:[a-z]{2,63}|xn--[a-z0-9-]{1,59})")
_URL = re.compile(r"(?:https?|ftp)://[^\s]+", re.IGNORECASE)
_VT_ID = re.compile(r"[A-Za-z0-9._:-]{1,256}")
_COUNTRY = re.compile(r"[A-Z]{2}")
_HIDDEN = {"Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp"}


# ── what a value is ───────────────────────────────────────────────────────────


def _internal_name(host: str) -> bool:
    return "." not in host or host.rsplit(".", 1)[-1] in INTERNAL_TLDS


def _internal_address(address: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]) -> bool:
    return not address.is_global or address.is_multicast


def classify(value: str) -> Tuple[str, str]:
    """``(kind, normalized value)`` for an IOC value. Pure.

    Kinds: ``ip``, ``domain``, ``url``, ``hash`` (MD5, SHA-1, SHA-256), ``internal`` (a private
    address or name, looked up nowhere), ``invalid`` (empty, too long or carrying hidden
    characters: looked up nowhere) and ``other`` (anything else: OpenCTI only).
    """
    text = (value or "").strip()
    if not text or len(text) > MAX_VALUE_LENGTH or any(unicodedata.category(ch) in _HIDDEN for ch in text):
        return "invalid", text
    try:
        address = ipaddress.ip_address(text)
    except ValueError:
        address = None
    if address is not None:
        return ("internal" if _internal_address(address) else "ip"), str(address)
    lowered = text.lower()
    if _HASH.fullmatch(lowered):
        return "hash", lowered
    if _URL.fullmatch(text):
        try:
            host = (urlsplit(text).hostname or "").rstrip(".").lower()
        except ValueError:
            return "other", text
        if not host:
            return "other", text
        try:
            return ("internal" if _internal_address(ipaddress.ip_address(host)) else "url"), text
        except ValueError:
            return ("internal" if _internal_name(host) else "url"), text
    name = lowered.rstrip(".")
    if _DOMAIN.fullmatch(name) and name.rsplit(".", 1)[-1] not in FILE_EXTENSIONS:
        return ("internal" if _internal_name(name) else "domain"), name
    return "other", text


def applicable(source: str, kind: str) -> bool:
    """Whether ``source`` may be asked about a value of ``kind``. Pure."""
    if kind in ("internal", "invalid"):
        return False
    if source == VIRUSTOTAL:
        return kind in ("ip", "domain", "url", "hash")
    return True


def text(value: Any, limit: int) -> Optional[str]:
    """A string an end customer may be shown: no control or formatting character, trimmed, bounded."""
    if not isinstance(value, str):
        return None
    cleaned = "".join(ch for ch in value if unicodedata.category(ch) not in _HIDDEN).strip()
    if not cleaned:
        return None
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 1].rstrip() + "…"


def _int(value: Any) -> Optional[int]:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _epoch(value: Any) -> Optional[str]:
    seconds = _int(value)
    if seconds is None or seconds <= 0:
        return None
    try:
        return datetime.fromtimestamp(seconds, tz=timezone.utc).replace(tzinfo=None).isoformat() + "Z"
    except (OverflowError, OSError, ValueError):
        return None


def _iso(value: Any) -> Optional[str]:
    """An ISO date OpenCTI gave, kept only when it reads as one."""
    candidate = text(value, 40)
    if not candidate:
        return None
    try:
        datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError:
        return None
    return candidate


# ── the sources' outcome ──────────────────────────────────────────────────────


@dataclass
class Outcome:
    """What one source answered: ``found`` (with a verdict and details), ``not_found`` or ``error``."""

    status: str
    verdict: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None  # rate_limited | unavailable
    log: Optional[str] = field(default=None, repr=False)  # for CoPilot's log only


def _failure(code: str, log: str) -> Outcome:
    return Outcome(status="error", error=code, log=log)


# ── VirusTotal ────────────────────────────────────────────────────────────────

_VT_PATHS = {"ip": "ip_addresses", "domain": "domains", "hash": "files", "url": "urls"}
_VT_GUI = {"ip_address": "ip-address", "domain": "domain", "file": "file", "url": "url"}


def virustotal_path(kind: str, value: str) -> str:
    """The lookup path for a value: a URL by its identifier (unpadded URL-safe base64), never submitted."""
    if kind == "url":
        identifier = base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")
    else:
        identifier = value
    return f"/{_VT_PATHS[kind]}/{quote(identifier, safe='')}"


def virustotal_verdict(details: VirusTotalDetails) -> str:
    if details.engines == 0:
        return "unknown"
    if details.malicious >= VIRUSTOTAL_MALICIOUS_ENGINES:
        return "malicious"
    if details.malicious or details.suspicious:
        return "suspicious"
    return "clean"


def project_virustotal(body: Any) -> Optional[VirusTotalDetails]:
    """The part of a VirusTotal object the portal shows, or None when it is not one. Pure."""
    data = body.get("data") if isinstance(body, dict) else None
    attributes = data.get("attributes") if isinstance(data, dict) else None
    if not isinstance(attributes, dict):
        return None
    stats = attributes.get("last_analysis_stats") if isinstance(attributes.get("last_analysis_stats"), dict) else {}
    counts = {key: max(0, _int(stats.get(key)) or 0) for key in ("malicious", "suspicious", "harmless", "undetected")}
    engines = sum(max(0, _int(count) or 0) for count in stats.values())
    tags = [tag for tag in (text(t, 64) for t in (attributes.get("tags") or [])[: MAX_TAGS * 2]) if tag][:MAX_TAGS]
    country = text(attributes.get("country"), 2)
    link = None
    vt_id, vt_type = data.get("id"), data.get("type")
    if isinstance(vt_id, str) and _VT_ID.fullmatch(vt_id) and vt_type in _VT_GUI:
        link = f"https://www.virustotal.com/gui/{_VT_GUI[vt_type]}/{quote(vt_id, safe='')}"
    return VirusTotalDetails(
        **counts,
        engines=engines,
        reputation=_int(attributes.get("reputation")),
        last_analysis_at=_epoch(attributes.get("last_analysis_date")),
        tags=tags,
        country=country if country and _COUNTRY.fullmatch(country) else None,
        as_owner=text(attributes.get("as_owner"), 128),
        type_description=text(attributes.get("type_description"), 128),
        link=link,
    )


async def virustotal_credentials() -> Optional[Tuple[str, str]]:
    """``(base URL, key)`` when the VirusTotal connector holds a key and is verified, else None."""
    async with get_db_session() as session:
        attributes = await get_connector_info_from_db(VIRUSTOTAL_CONNECTOR_NAME, session)
    if not attributes or not attributes.get("connector_verified"):
        return None
    key = (attributes.get("connector_api_key") or "").strip()
    if not key:
        return None
    url = (attributes.get("connector_url") or "").strip().rstrip("/") or VIRUSTOTAL_DEFAULT_URL
    return url, key


async def _read_capped(response: httpx.Response, limit: int) -> Optional[bytes]:
    """The body, or None past ``limit``. Bytes as sent: an encoded body is refused before this."""
    body = bytearray()
    async for chunk in response.aiter_bytes():
        body.extend(chunk)
        if len(body) > limit:
            return None
    return bytes(body)


def _virustotal_client() -> httpx.AsyncClient:
    """The client every VirusTotal lookup uses (the tests hand it a transport)."""
    return httpx.AsyncClient(timeout=VIRUSTOTAL_TIMEOUT, follow_redirects=False)


async def lookup_virustotal(kind: str, value: str, credentials: Tuple[str, str]) -> Outcome:
    """Ask VirusTotal about one value, by ``GET`` only."""
    base_url, key = credentials
    url = f"{base_url}{virustotal_path(kind, value)}"
    headers = {"x-apikey": key, "accept": "application/json", "accept-encoding": "identity"}
    try:
        async with _virustotal_client() as client:
            async with client.stream("GET", url, headers=headers) as response:
                if response.status_code == 404:
                    return Outcome(status="not_found")
                if response.status_code == 429:
                    return _failure("rate_limited", "VirusTotal answered 429")
                if response.status_code != 200:
                    return _failure("unavailable", f"VirusTotal answered {response.status_code}")
                if response.headers.get("content-encoding", "identity").lower() not in ("", "identity"):
                    return _failure("unavailable", "VirusTotal answered with an encoded body")
                raw = await _read_capped(response, MAX_VIRUSTOTAL_BYTES)
    except httpx.HTTPError as error:
        return _failure("unavailable", f"VirusTotal request failed: {type(error).__name__}")
    if raw is None:
        return _failure("unavailable", "VirusTotal's answer was too large")
    try:
        details = project_virustotal(json.loads(raw))
    except ValueError:
        details = None
    if details is None:
        return _failure("unavailable", "VirusTotal's answer was not an object")
    return Outcome(status="found", verdict=virustotal_verdict(details), details=details.model_dump())


# ── OpenCTI ───────────────────────────────────────────────────────────────────


def _markings(node: Dict[str, Any]) -> List[str]:
    return [m.get("definition") for m in node.get("objectMarking") or [] if isinstance(m, dict) and isinstance(m.get("definition"), str)]


def shareable(markings: Iterable[str]) -> bool:
    """Whether an object with these markings may be shown to a customer. Pure."""
    for marking in markings:
        upper = marking.strip().upper()
        if upper in SHAREABLE_TLP or upper.startswith("PAP:"):
            continue
        return False
    return True


def _edges(connection: Any) -> List[Dict[str, Any]]:
    if not isinstance(connection, dict):
        return []
    return [edge["node"] for edge in connection.get("edges") or [] if isinstance(edge, dict) and isinstance(edge.get("node"), dict)]


def opencti_verdict(score: Optional[int]) -> str:
    if score is not None and score >= OPENCTI_MALICIOUS_SCORE:
        return "malicious"
    if score is not None and score >= OPENCTI_SUSPICIOUS_SCORE:
        return "suspicious"
    return "known"


def _score(value: Any) -> Optional[int]:
    score = _int(value)
    return score if score is not None and 0 <= score <= 100 else None


def project_opencti(data: Any) -> Optional[OpenCtiDetails]:
    """What the portal shows of OpenCTI's observables for one value, or None when none may be shown. Pure."""
    observables = [node for node in _edges((data or {}).get("stixCyberObservables")) if shareable(_markings(node))]
    if not observables:
        return None
    scores: List[int] = []
    entity_types: List[str] = []
    labels: List[str] = []
    indicators: List[OpenCtiIndicator] = []
    reports: List[OpenCtiReport] = []
    seen_reports = set()
    withheld = 0
    for node in observables[:OPENCTI_OBSERVABLES]:
        if (score := _score(node.get("x_opencti_score"))) is not None:
            scores.append(score)
        entity_type = text(node.get("entity_type"), 64)
        if entity_type and entity_type not in entity_types:
            entity_types.append(entity_type)
        for label in node.get("objectLabel") or []:
            value = text(label.get("value"), 64) if isinstance(label, dict) else None
            if value and value not in labels and len(labels) < MAX_LABELS:
                labels.append(value)
        for indicator in _edges(node.get("indicators")):
            if not shareable(_markings(indicator)):
                withheld += 1
                continue
            revoked = indicator.get("revoked") is True
            score = _score(indicator.get("x_opencti_score"))
            if score is not None and not revoked:
                scores.append(score)
            if len(indicators) < OPENCTI_INDICATORS:
                indicators.append(
                    OpenCtiIndicator(
                        name=text(indicator.get("name"), 200),
                        score=score,
                        valid_until=_iso(indicator.get("valid_until")),
                        revoked=revoked,
                    ),
                )
        for report in _edges(node.get("reports")):
            if not shareable(_markings(report)):
                withheld += 1
                continue
            name = text(report.get("name"), 200)
            if name and name not in seen_reports and len(reports) < OPENCTI_REPORTS:
                seen_reports.add(name)
                reports.append(OpenCtiReport(name=name, published=_iso(report.get("published"))))
    return OpenCtiDetails(
        score=max(scores) if scores else None,
        entity_types=entity_types,
        labels=labels,
        indicators=indicators,
        reports=reports,
        withheld=withheld,
    )


async def opencti_configured() -> bool:
    """Whether the OpenCTI connector holds a URL and a key and is verified."""
    async with get_db_session() as session:
        attributes = await get_connector_info_from_db(OPENCTI_CONNECTOR_NAME, session)
    if not attributes:
        return False
    configured = bool((attributes.get("connector_url") or "").strip() and (attributes.get("connector_api_key") or "").strip())
    return configured and bool(attributes.get("connector_verified"))


async def lookup_opencti(value: str) -> Outcome:
    """Ask OpenCTI about one value: its ``value`` or any of its hashes, as the analysts' lookup does."""
    variables = {
        "filters": filter_group([filter_item(OBSERVABLE_LOOKUP_KEYS, [value])]),
        "first": OPENCTI_OBSERVABLES,
        "indicators": OPENCTI_INDICATORS * 2,
        "reports": OPENCTI_REPORTS * 2,
    }
    response = await send_graphql_request(PORTAL_OBSERVABLE_QUERY, variables, timeout=SOURCE_TIMEOUT_SECONDS - 2)
    if not response.get("success"):
        return _failure("unavailable", "OpenCTI did not answer the lookup")
    details = project_opencti(response.get("data"))
    if details is None:
        return Outcome(status="not_found")
    return Outcome(status="found", verdict=opencti_verdict(details.score), details=details.model_dump())


# ── asking ────────────────────────────────────────────────────────────────────


async def available_sources() -> List[str]:
    """The sources this deployment can ask now, in display order."""
    sources = []
    if await virustotal_credentials() is not None:
        sources.append(VIRUSTOTAL)
    if await opencti_configured():
        sources.append(OPENCTI)
    return sources


async def ask(source: str, kind: str, value: str) -> Outcome:
    """Ask one source about one value, within ``SOURCE_TIMEOUT_SECONDS``. Never raises."""
    try:
        if source == VIRUSTOTAL:
            credentials = await virustotal_credentials()
            if credentials is None:
                return _failure("unavailable", "the VirusTotal connector is not verified")
            outcome = await asyncio.wait_for(lookup_virustotal(kind, value, credentials), SOURCE_TIMEOUT_SECONDS)
        else:
            outcome = await asyncio.wait_for(lookup_opencti(value), SOURCE_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        outcome = _failure("unavailable", f"{source} did not answer within {SOURCE_TIMEOUT_SECONDS:.0f} s")
    except Exception as error:  # a source must never fail the lookup of the other
        outcome = _failure("unavailable", f"{source} lookup failed: {type(error).__name__}")
    if outcome.status == "error":
        logger.warning(f"IOC enrichment: {outcome.log}")
    return outcome
