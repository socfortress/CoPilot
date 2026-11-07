"""Domains, tenant ids and account names as the SOC records them (talon-analyst plan K1-7).

A wrong "own" domain is the risk here: talon-analyst labels every domain under it as the customer's,
so a domain many organisations share would label half the internet. These checks refuse the common
ones; they aren't the whole Public Suffix List, and talon-analyst's matching doesn't rely on them:

- **A domain** is lower case, IDNA (punycode) encoded, with at least two labels and no wildcard,
  scheme, path, port or address. It isn't a shared suffix (``co.uk``, ``onmicrosoft.com``): the
  customer's own name sits under one. It isn't a public mail provider's (``gmail.com``).
- **A tenant id** is a GUID for Entra (stored in lower case), ``C`` and letters or digits for Google
  Workspace, and plain letters, digits and ``._:-`` for any other provider.
- **An account** is an identifier: ``jsmith``, ``CORP\\jsmith`` or ``jsmith@corp.com``. Its account part
  holds no whitespace, so a display name ("Jane Smith") is refused (Taylor's decision, plan K1-7). A
  domain before the backslash may hold spaces, as ``NT AUTHORITY\\SYSTEM`` does.

Every refusal is a fixed text that never echoes input.
"""

import ipaddress
import re
import uuid

import idna

DOMAIN_MAX = 253

BAD_DOMAIN = "enter a domain name, such as example.com, without a scheme, path, port or wildcard"
SHARED_SUFFIX = "many organisations sit under this suffix: record the customer's own domain under it"
FREE_MAIL = "this is a public mail provider's domain, not the customer's"
BAD_TENANT = "enter the tenant's id as the provider shows it"
BAD_ENTRA_TENANT = "an Entra tenant id is a GUID, such as 72f988bf-86f1-41af-91ab-2d7cd011db47"
BAD_GOOGLE_TENANT = "a Google Workspace customer id starts with C, such as C01b2c3d4"
NOT_AN_IDENTIFIER = "record the account's name, such as jsmith, CORP\\jsmith or jsmith@corp.com, not a display name"

# fmt: off
#: Suffixes many organisations register under: second-level country domains and shared platforms. The
#: common ones only, not the Public Suffix List; a single label (``com``) is refused anyway.
SHARED_SUFFIXES = frozenset(
    {
        # second-level country domains
        "co.uk", "org.uk", "me.uk", "ltd.uk", "plc.uk", "net.uk", "ac.uk", "gov.uk", "nhs.uk", "sch.uk",
        "com.au", "net.au", "org.au", "edu.au", "gov.au", "id.au", "co.nz", "org.nz", "net.nz", "govt.nz",
        "ac.nz", "co.za", "org.za", "gov.za", "com.br", "net.br", "org.br", "gov.br", "com.mx", "org.mx",
        "gob.mx", "com.ar", "com.co", "com.pe", "com.cn", "net.cn", "org.cn", "gov.cn", "com.hk", "com.tw",
        "com.sg", "edu.sg", "gov.sg", "com.my", "co.in", "net.in", "org.in", "gov.in", "ac.in", "co.jp",
        "ne.jp", "or.jp", "ac.jp", "go.jp", "co.kr", "or.kr", "ac.kr", "go.kr", "co.id", "or.id", "ac.id",
        "go.id", "com.tr", "gov.tr", "com.ua", "co.il", "org.il", "ac.il", "gov.il", "com.sa", "gov.sa",
        "com.eg", "com.ng", "co.ke", "com.pk", "com.ph", "com.vn", "co.th", "in.th", "ac.th", "com.pl",
        "com.ru", "com.es", "co.at", "or.at", "com.gr", "com.cy",
        # shared platforms: a customer's tenant or site sits under these, never the suffix itself
        "onmicrosoft.com", "sharepoint.com", "azurewebsites.net", "cloudapp.net", "cloudapp.azure.com",
        "azureedge.net", "blob.core.windows.net", "trafficmanager.net", "github.io", "gitlab.io",
        "herokuapp.com", "appspot.com", "firebaseapp.com", "web.app", "pages.dev", "workers.dev",
        "netlify.app", "vercel.app", "amazonaws.com", "s3.amazonaws.com", "cloudfront.net",
        "elasticbeanstalk.com", "blogspot.com", "wordpress.com", "wixsite.com", "squarespace.com",
        "myshopify.com", "ngrok.io", "ngrok-free.app", "duckdns.org", "no-ip.org", "dyndns.org",
        "googleusercontent.com",
    },
)

#: Public mail providers: nobody records these as their own, for mail or anything else.
FREE_MAIL_DOMAINS = frozenset(
    {
        "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "hotmail.co.uk", "live.com", "msn.com",
        "yahoo.com", "yahoo.co.uk", "ymail.com", "aol.com", "icloud.com", "me.com", "mac.com", "proton.me",
        "protonmail.com", "pm.me", "gmx.com", "gmx.de", "gmx.net", "web.de", "mail.com", "yandex.com",
        "yandex.ru", "mail.ru", "zoho.com", "qq.com", "163.com", "126.com", "fastmail.com", "tutanota.com",
        "tuta.io", "hey.com", "comcast.net", "verizon.net", "att.net",
    },
)
# fmt: on

_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
_NOT_IN_A_DOMAIN = set("*%/@:?#\\[]<>\"'`=&;,")
_GOOGLE_TENANT = re.compile(r"C[0-9A-Za-z]{4,20}")
_OTHER_TENANT = re.compile(r"[0-9A-Za-z][0-9A-Za-z._:-]{0,127}")


class DomainProblem(ValueError):
    """A domain, tenant id or account that can't be recorded. Its text is one of the fixed texts above."""


def checked_domain(value: str) -> str:
    """``value`` as stored: lower case, IDNA encoded, no trailing dot. Raises ``DomainProblem``."""
    text = str(value).strip().rstrip(".").lower()
    if not text or any(ch.isspace() or ch in _NOT_IN_A_DOMAIN or ord(ch) < 32 for ch in text):
        raise DomainProblem(BAD_DOMAIN)
    try:
        ipaddress.ip_address(text)
    except ValueError:
        pass
    else:
        raise DomainProblem(BAD_DOMAIN)
    try:
        encoded = idna.encode(text, uts46=True).decode("ascii")
    except (idna.IDNAError, UnicodeError, ValueError):
        raise DomainProblem(BAD_DOMAIN) from None
    labels = encoded.split(".")
    if len(encoded) > DOMAIN_MAX or len(labels) < 2 or not all(_LABEL.fullmatch(label) for label in labels):
        raise DomainProblem(BAD_DOMAIN)
    if labels[-1].isdigit():
        raise DomainProblem(BAD_DOMAIN)
    if encoded in SHARED_SUFFIXES:
        raise DomainProblem(SHARED_SUFFIX)
    if encoded in FREE_MAIL_DOMAINS:
        raise DomainProblem(FREE_MAIL)
    return encoded


def related(a: str, b: str) -> bool:
    """Two stored domains that name the same space: equal, or one under the other."""
    return a == b or a.endswith("." + b) or b.endswith("." + a)


def checked_tenant(provider: str, value: str) -> str:
    """The tenant id as stored. Raises ``DomainProblem``."""
    text = str(value).strip()
    if provider == "entra":
        try:
            return str(uuid.UUID(text))
        except ValueError:
            raise DomainProblem(BAD_ENTRA_TENANT) from None
    if provider == "google":
        if not _GOOGLE_TENANT.fullmatch(text):
            raise DomainProblem(BAD_GOOGLE_TENANT)
        return text
    if not _OTHER_TENANT.fullmatch(text):
        raise DomainProblem(BAD_TENANT)
    return text


def checked_identifier(value: str) -> str:
    """An account identifier as stored (trimmed). ``CORP\\jsmith``'s domain may hold spaces, its account
    part never; ``jsmith@corp.com`` holds none. The name checks (``_account``) are the caller's."""
    text = str(value).strip()
    if "\\" in text:
        domain, _, account = text.partition("\\")
        if not domain.strip() or not account or "\\" in account or any(ch.isspace() for ch in account):
            raise DomainProblem(NOT_AN_IDENTIFIER)
        return text
    if any(ch.isspace() for ch in text):
        raise DomainProblem(NOT_AN_IDENTIFIER)
    if "@" in text:
        local, _, domain = text.partition("@")
        if not local or not domain or "@" in domain:
            raise DomainProblem(NOT_AN_IDENTIFIER)
    return text
