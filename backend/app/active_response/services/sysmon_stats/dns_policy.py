"""Which DNS names (QueryName, DestinationHostname) a noise report may carry. Pure.

An organisation's internal names identify it and map its network, and SOCFortress's suggestion gates cannot tell them
from a vendor's, so this is CoPilot's decision (owner decision D1, a conservative default): a name is sent verbatim only
when nothing marks it as internal or as the customer's. Every uncertain case drops the pattern; the one redaction is a
multi-tenant SaaS name, whose tenant part becomes <redacted> (``contoso-my.sharepoint.com`` ->
``<redacted>.sharepoint.com``). IP addresses are never sent: an IP literal drops the pattern, and DestinationIp is never
queried.

The customer's own domains are rarely configured, so they are also learned from what its endpoints reveal about them
(``owner_domain``): the domain of an Active Directory locator record (``_ldap._tcp.dc._msdcs.<domain>``), the rest of
``<one of its host names>.<domain>``, and the domain an organisation's own service names sit in
(``autodiscover.<domain>``, ``enterpriseregistration.<domain>``, ``wpad.<domain>``, ...). Such names are dropped
themselves, learned or not.
"""
import ipaddress
import re
from dataclasses import dataclass
from typing import AbstractSet
from typing import Iterable
from typing import Optional
from typing import Union

# Suffixes that are never public: RFC 6761/6762/8375 special-use names, and the ones organisations use internally
PRIVATE_SUFFIXES = (
    "local",
    "localhost",
    "localdomain",
    "lan",
    "home",
    "corp",
    "internal",
    "intranet",
    "private",
    "priv",
    "domain",
    "workgroup",
    "test",
    "example",
    "invalid",
    "home.arpa",
    "lab",
    "office",
)
# Multi-tenant SaaS: the labels left of these name a tenant (an organisation). Extend in code.
TENANT_SUFFIXES = (
    "sharepoint.com",
    "onmicrosoft.com",
    "mail.protection.outlook.com",
    "blob.core.windows.net",
    "file.core.windows.net",
    "queue.core.windows.net",
    "table.core.windows.net",
    "dfs.core.windows.net",
    "azurewebsites.net",
    "cloudapp.azure.com",
    "cloudapp.net",
    "vault.azure.net",
    "database.windows.net",
    "servicebus.windows.net",
    "s3.amazonaws.com",
    "awsapps.com",
    "okta.com",
    "oktapreview.com",
    "atlassian.net",
    "zendesk.com",
    "my.salesforce.com",
    "service-now.com",
    "webex.com",
    "zoom.us",
    "myshopify.com",
    "freshservice.com",
)
# The first label of a name that only an organisation's own domain has: the name is the organisation's (dropped), and the
# rest of it is its domain (learned), unless that is a mail or identity provider's (autodiscover.outlook.com)
OWN_LOCATOR_LABELS = frozenset(
    {
        "autodiscover",
        "enterpriseregistration",
        "enterpriseenrollment",
        "lyncdiscover",
        "lyncdiscoverinternal",
        "sipinternal",
        "wpad",
        "isatap",
    },
)
PROVIDER_DOMAINS = (
    "outlook.com",
    "office365.com",
    "office.com",
    "office.net",
    "microsoft.com",
    "microsoftonline.com",
    "live.com",
    "hotmail.com",
    "msn.com",
    "windows.net",
    "azure.com",
    "lync.com",
    "skype.com",
    "gmail.com",
    "google.com",
    "googlemail.com",
    "yahoo.com",
    "icloud.com",
    "me.com",
    "apple.com",
    "aol.com",
    "zoho.com",
    "proton.me",
    "protonmail.com",
    "gmx.com",
    "yandex.com",
)
# Active Directory's DNS locator records (RFC 2782 SRV names a domain-joined endpoint asks for all the time)
AD_SRV_SERVICES = frozenset({"_ldap", "_kerberos", "_kpasswd", "_gc"})
_LABEL_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
_OCTET = r"(?:25[0-5]|2[0-4]\d|1?\d?\d)"
IPV4_IN_NAME_RE = re.compile(rf"(?<!\d){_OCTET}(?:[-.]{_OCTET}){{3}}(?!\d)")


@dataclass(frozen=True)
class Drop:
    reason: str


def under(name: str, suffix: str) -> bool:
    """``name`` is ``suffix`` or a name below it (both lowercase, no trailing dot)."""
    return name == suffix or name.endswith("." + suffix)


def _ip_literal(name: str) -> bool:
    if ":" in name or name.startswith("["):
        return True
    try:
        ipaddress.ip_address(name)
    except ValueError:
        return False
    return True


def _provider(domain: str) -> bool:
    return any(under(domain, p) for p in PROVIDER_DOMAINS)


def _domain(labels) -> Optional[str]:
    """``labels`` as a domain name, when every one is a plain DNS label (no service label, nothing empty)."""
    if not labels or not all(_LABEL_RE.fullmatch(label) for label in labels):
        return None
    return ".".join(labels)


def owner_domain(value: str, hosts: AbstractSet[str]) -> Optional[str]:
    """The customer's own domain a DNS name it looked up reveals, or None: the domain of an Active Directory locator
    record, the rest of ``<one of its hosts>.<domain>``, the domain of ``autodiscover.<domain>`` and the like (not a
    provider's). ``hosts`` are its host names (lowercase, first label). A single-label result is an AD domain's own
    single-label name."""
    name = value.strip().lower().rstrip(".")
    labels = name.split(".")
    if len(labels) < 2:
        return None
    if "_msdcs" in labels:
        return _domain(labels[labels.index("_msdcs") + 1 :])
    if labels[0] in AD_SRV_SERVICES and len(labels) > 2 and labels[1] in ("_tcp", "_udp"):
        last = max(i for i, label in enumerate(labels) if label.startswith("_"))
        return _domain(labels[last + 1 :])
    if len(labels) >= 3 and (labels[0] in OWN_LOCATOR_LABELS or labels[0] in hosts):
        domain = _domain(labels[1:])
        return None if domain is None or _provider(domain) else domain
    return None


def classify_dns(
    value: str,
    names: AbstractSet[str],
    own_domains: Iterable[str],
    compounds: Iterable[str] = (),
) -> Union[str, Drop]:
    """The value to send (as logged, or tenant-redacted), or why the pattern is dropped. ``names`` are the customer's
    identity tokens (lowercase), ``own_domains`` its own domains (lowercase), ``compounds`` its multi-word name written
    as one word (``acmewidgets``), dropped wherever a label holds it."""
    if value == "-":
        return value
    name = value.strip().lower().rstrip(".")
    if not name:
        return Drop("value-empty")
    if _ip_literal(name):
        return Drop("dns-ip-literal")
    if "." not in name:
        return Drop("dns-single-label")
    labels = name.split(".")
    if any(label.startswith("_") for label in labels):
        return Drop("dns-service-record")
    if name.endswith("in-addr.arpa") or name.endswith("ip6.arpa"):
        return Drop("dns-reverse-lookup")
    if any(under(name, suffix) for suffix in PRIVATE_SUFFIXES):
        return Drop("dns-private-suffix")
    if any(d and under(name, d) for d in own_domains):
        return Drop("dns-own-domain")
    if len(labels) >= 3 and labels[0] in OWN_LOCATOR_LABELS and not _provider(".".join(labels[1:])):
        return Drop("dns-own-locator")
    compounds = tuple(compounds)
    for label in labels:
        if label in names or any(token in names for token in label.split("-") if token):
            return Drop("dns-identity-token")
        if any(c in label for c in compounds):
            return Drop("dns-identity-token")
    if IPV4_IN_NAME_RE.search(name):
        return Drop("dns-ip-label")
    tenant = tenant_suffix(name)
    if tenant is not None:
        original = value.strip().rstrip(".")
        return "<redacted>." + original[len(original) - len(tenant) :]
    return value


def tenant_suffix(name: str) -> Optional[str]:
    """The tenant suffix ``name`` is strictly below, if any."""
    for suffix in TENANT_SUFFIXES:
        if name.endswith("." + suffix):
            return suffix
    return None
