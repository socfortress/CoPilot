"""
IP blocking on a customer's WAF (#1167).

The WAF has no IP-blocklist API: a block is a custom Coraza rule denying
``REMOTE_ADDR`` in phase 1, and every create/update reloads Caddy (sub-second,
no downtime). CoPilot creates exactly one rule shape::

    SecRule REMOTE_ADDR "@ipMatch <target>" "id:AUTO,phase:1,deny,status:403,log,msg:'CoPilot block: <target>',tag:'copilot-block'"

Rules that keep this safe:

- **The rule text is built here, from a parsed network — never from client input.**
  ``normalize_target`` runs ``ipaddress.ip_network`` and only its canonical string
  reaches SecLang. The analyst's reason goes to the rule's *description* (a DB
  column on the WAF), never into the rule text. This is the injection boundary:
  an interpolated raw value could add arbitrary actions (``pass``, ``ctl:ruleEngine=Off``).
- **CoPilot only ever changes rules it created** (``tag:'copilot-block'``). The WAF's
  own blocks — e.g. its Threat Intel blocks — are listed and respected (no duplicate
  rule for an IP already covered) but never modified.
- **Unblock disables, never deletes.** The rule and its WAF audit trail survive and a
  re-block is a re-enable. Verified against a real WAF: ``PUT {"is_enabled": …}``
  round-trips this shape intact (the WAF rebuilds the text from parsed fields, and
  since waf-platform ``cbc7b9b`` that keeps phase, deny and the tag).
- **Over-broad ranges are refused**: IPv4 shorter than /16, IPv6 shorter than /48.
"""

import ipaddress
import re
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from app.customer_waf.schema.customer_waf import WafBlock
from app.customer_waf.utils.universal import waf_request

Network = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]

COPILOT_BLOCK_TAG = "copilot-block"
COPILOT_BLOCK_NAME_PREFIX = "CoPilot block: "
MIN_PREFIX = {4: 16, 6: 48}
# Creating a rule reloads Caddy on the WAF; give it more room than a read.
WRITE_TIMEOUT = 30.0

_SPLIT = re.compile(r"[,\s]+")


class BlockTargetError(ValueError):
    """The requested target is not an acceptable IP or range."""


def normalize_target(value: str) -> Network:
    """Parse and validate a block target. Returns the canonical network."""
    raw = (value or "").strip()
    try:
        network = ipaddress.ip_network(raw, strict=False)
    except ValueError:
        raise BlockTargetError(f"'{raw}' is not an IPv4/IPv6 address or CIDR range")
    minimum = MIN_PREFIX[network.version]
    if network.prefixlen < minimum:
        raise BlockTargetError(
            f"{network} is too broad to block from CoPilot (IPv{network.version} ranges must be /{minimum} or narrower)",
        )
    return network


def display(network: Network) -> str:
    """A single host shows as a plain address, a range as CIDR."""
    return str(network.network_address) if network.prefixlen == network.max_prefixlen else str(network)


def target_warnings(network: Network) -> List[str]:
    address = network.network_address
    if address.is_loopback or address.is_unspecified:
        return [f"{display(network)} is a loopback/unspecified address — blocking it has no useful effect."]
    if address.is_private or address.is_link_local or address.is_reserved or address.is_multicast:
        return [
            f"{display(network)} is not a public address. That is expected only if the WAF sits behind a load balancer "
            "or proxy that it sees traffic from — blocking the proxy's address would block everyone behind it.",
        ]
    return []


def build_rule_text(network: Network) -> str:
    """The only place SecLang for a CoPilot block is produced."""
    target = display(network)
    return (
        f'SecRule REMOTE_ADDR "@ipMatch {target}" '
        f"\"id:AUTO,phase:1,deny,status:403,log,msg:'{COPILOT_BLOCK_NAME_PREFIX}{target}',tag:'{COPILOT_BLOCK_TAG}'\""
    )


def build_description(reason: str, username: str, alert_id: Optional[int], case_id: Optional[int]) -> str:
    parts = [" ".join(reason.split()), f"by {username} via CoPilot"]
    if alert_id is not None:
        parts.append(f"alert #{alert_id}")
    if case_id is not None:
        parts.append(f"case #{case_id}")
    return " | ".join(parts)


# ── reading the WAF's rules ────────────────────────────────────────────────


def is_copilot_rule(rule: dict) -> bool:
    return f"tag:'{COPILOT_BLOCK_TAG}'" in (rule.get("conf_text") or "") or (rule.get("name") or "").startswith(COPILOT_BLOCK_NAME_PREFIX)


def rule_networks(rule: dict) -> List[Network]:
    """Networks an IP-blocking rule denies; [] for any other rule.

    Only simple ``REMOTE_ADDR @ipMatch`` deny rules count. A chained or bypass rule that
    happens to mention an address is not a block, so it is never reported as one.
    """
    if (rule.get("field") or "").upper() != "REMOTE_ADDR" or (rule.get("operator") or "") != "@ipMatch":
        return []
    # Judge by the rule text, not the stored ``action``: rules created before waf-platform
    # cbc7b9b carry a stale "deny,status:403" action on what is really a pass/bypass rule.
    conf = rule.get("conf_text") or ""
    if "deny" not in conf or "chain" in conf or "ctl:ruleEngine" in conf:
        return []
    networks = []
    for token in _SPLIT.split(rule.get("value") or ""):
        try:
            networks.append(ipaddress.ip_network(token, strict=False))
        except ValueError:
            continue
    return networks


def to_block(rule: dict, network: Optional[Network] = None) -> WafBlock:
    nets = rule_networks(rule)
    target = display(network) if network else ", ".join(display(n) for n in nets) or (rule.get("value") or "")
    return WafBlock(
        target=target,
        rule_uuid=str(rule["id"]),
        rule_id=int(rule["rule_id"]),
        name=rule.get("name") or "",
        description=rule.get("description") or "",
        enabled=bool(rule.get("is_enabled")),
        created_by_copilot=is_copilot_rule(rule),
        created_at=rule.get("created_at"),
    )


async def fetch_rules(instance) -> List[dict]:
    return list(await waf_request(instance, "GET", "/rules/custom") or [])


def ip_block_rules(rules: Iterable[dict]) -> Tuple[List[dict], List[dict]]:
    """Split into (CoPilot-created IP blocks, the WAF's own IP blocks)."""
    copilot, other = [], []
    for rule in rules:
        if not rule_networks(rule):
            continue
        (copilot if is_copilot_rule(rule) else other).append(rule)
    return copilot, other


def _covers(rule: dict, network: Network) -> bool:
    return any(n.version == network.version and network.subnet_of(n) for n in rule_networks(rule))


def _exact(rule: dict, network: Network) -> bool:
    return network in rule_networks(rule)


# ── actions ────────────────────────────────────────────────────────────────


async def block(instance, network: Network, description: str) -> Tuple[str, dict]:
    """Make sure ``network`` is blocked. Returns ``(action, rule)``.

    Nothing is written when the target is already blocked: by CoPilot's own rule for
    exactly this target, or by any enabled rule covering it (a broader CoPilot range, or
    the WAF's own block — e.g. a Threat Intel rule, reported as ``blocked_by_waf_rule``).
    Otherwise CoPilot's disabled rule for the target is re-enabled (keeping one rule per
    target and its history), and only failing that is a new rule created.
    """
    rules = await fetch_rules(instance)
    copilot, other = ip_block_rules(rules)

    mine = [r for r in copilot if _exact(r, network)]
    enabled = next((r for r in mine if r.get("is_enabled")), None)
    if enabled:
        return "already_blocked", enabled
    covering = next((r for r in copilot + other if r.get("is_enabled") and _covers(r, network)), None)
    if covering:
        return ("already_blocked" if is_copilot_rule(covering) else "blocked_by_waf_rule"), covering
    if mine:
        rule = await waf_request(
            instance,
            "PUT",
            f"/rules/custom/{mine[0]['id']}",
            json={"is_enabled": True, "description": description},
            timeout=WRITE_TIMEOUT,
        )
        return "reenabled", rule

    rule = await waf_request(
        instance,
        "POST",
        "/rules/custom",
        json={
            "name": f"{COPILOT_BLOCK_NAME_PREFIX}{display(network)}",
            "description": description,
            "raw_conf_text": build_rule_text(network),
        },
        timeout=WRITE_TIMEOUT,
    )
    return "created", rule


async def unblock(instance, network: Network) -> Tuple[str, List[dict], Optional[dict]]:
    """Disable CoPilot's rule(s) for exactly ``network``.

    Returns ``(action, rules, waf_rule)`` where ``waf_rule`` is a still-enabled WAF-owned
    rule covering the network, if any — CoPilot can't lift that one, and the caller
    should say so rather than report the IP as unblocked.
    """
    rules = await fetch_rules(instance)
    copilot, other = ip_block_rules(rules)
    mine = [r for r in copilot if _exact(r, network)]
    waf_rule = next((r for r in other if r.get("is_enabled") and _covers(r, network)), None)

    active = [r for r in mine if r.get("is_enabled")]
    if not active:
        return "already_unblocked", mine, waf_rule
    updated = [
        await waf_request(instance, "PUT", f"/rules/custom/{r['id']}", json={"is_enabled": False}, timeout=WRITE_TIMEOUT) for r in active
    ]
    return "unblocked", updated, waf_rule
