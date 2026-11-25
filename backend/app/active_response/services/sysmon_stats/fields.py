"""Where Sysmon's fields live in the Wazuh indexer, and what each event's patterns are made of.

Two shapes exist side by side: Wazuh's own nested mapping (``data.win.eventdata.image``, ``agent.labels.customer``) and
the flat one Graylog pipelines write (``data_win_eventdata_image``, ``agent_labels_customer``). One ``_field_caps`` call
says which fields are mapped; a shape is usable only if all its base fields are. Eventdata names are matched
case-insensitively (``TargetFilename`` is ``targetFilename`` in the index), an exact keyword field preferred over its
``.keyword`` sub-field. The Windows event's ``Computer`` (a domain-joined endpoint's fully qualified name) is optional:
when mapped, the customer's host names and own domains are learned from it.
"""
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

SYSMON_CHANNEL = "Microsoft-Windows-Sysmon/Operational"

# role -> (flat, nested)
BASE_FIELDS: Dict[str, Tuple[str, str]] = {
    "time": ("timestamp", "timestamp"),
    "label": ("agent_labels_customer", "agent.labels.customer"),
    "agent": ("agent_id", "agent.id"),
    "level": ("rule_level", "rule.level"),
    "event_id": ("data_win_system_eventID", "data.win.system.eventID"),
    "channel": ("data_win_system_channel", "data.win.system.channel"),
}
# role -> (flat, nested); a shape is usable without them
OPTIONAL_FIELDS: Dict[str, Tuple[str, str]] = {
    "computer": ("data_win_system_computer", "data.win.system.computer"),
}
EVENTDATA_PREFIX = {"flat": "data_win_eventdata_", "nested": "data.win.eventdata."}
FIELD_CAPS_FIELDS = ",".join(
    [f for pair in (*BASE_FIELDS.values(), *OPTIONAL_FIELDS.values()) for f in dict.fromkeys(pair)]
    + [f"{EVENTDATA_PREFIX['flat']}*", f"{EVENTDATA_PREFIX['nested']}*"],
)


@dataclass(frozen=True)
class Nest:
    """A stage-2 terms level below the actor: the Sysmon field, its terms size, and whether events without it form a
    ``-`` bucket (Sysmon's own "empty" for an optional field)."""

    name: str
    size: int
    missing: bool = False


@dataclass(frozen=True)
class EventPlan:
    actor: str
    nests: Tuple[Nest, ...]
    # Detail fields and their sameness terms size
    details: Tuple[Tuple[str, int], ...]
    # The order fields are sent in (at most 5)
    order: Tuple[str, ...]

    @property
    def key_fields(self) -> Tuple[str, ...]:
        return (self.actor,) + tuple(n.name for n in self.nests)


_USER = ("User", 10)
EVENT_PLAN: Dict[int, EventPlan] = {
    1: EventPlan(
        "Image",
        (Nest("ParentImage", 15),),
        (("OriginalFileName", 2), _USER, ("IntegrityLevel", 2)),
        ("Image", "ParentImage", "OriginalFileName", "User", "IntegrityLevel"),
    ),
    3: EventPlan(
        "Image",
        (Nest("DestinationHostname", 15, missing=True), Nest("DestinationPort", 5)),
        (("Protocol", 2), ("Initiated", 2), _USER),
        ("Image", "DestinationPort", "DestinationHostname", "Protocol", "Initiated"),
    ),
    6: EventPlan(
        "ImageLoaded",
        (Nest("Signature", 3, missing=True), Nest("SignatureStatus", 3, missing=True)),
        (("Signed", 2),),
        ("ImageLoaded", "Signature", "SignatureStatus", "Signed"),
    ),
    # OriginalFileName before SignatureStatus: SOCFortress's own ImageLoad includes match on it (clr.dll, amsi.dll, ...),
    # and a pattern without it would be judged as not logged by them. Signed adds nothing once SignatureStatus is sent.
    7: EventPlan(
        "Image",
        (Nest("ImageLoaded", 15), Nest("Signature", 3, missing=True)),
        (("OriginalFileName", 2), ("SignatureStatus", 2), _USER),
        ("Image", "ImageLoaded", "Signature", "OriginalFileName", "SignatureStatus"),
    ),
    8: EventPlan(
        "SourceImage",
        (Nest("TargetImage", 15), Nest("StartModule", 3, missing=True)),
        (("StartFunction", 2), ("SourceUser", 10), ("TargetUser", 10)),
        ("SourceImage", "TargetImage", "StartModule", "StartFunction", "SourceUser"),
    ),
    10: EventPlan(
        "SourceImage",
        (Nest("TargetImage", 15), Nest("GrantedAccess", 5)),
        (("SourceUser", 10), ("TargetUser", 10)),
        ("SourceImage", "TargetImage", "GrantedAccess", "SourceUser", "TargetUser"),
    ),
    12: EventPlan(
        "Image",
        (Nest("TargetObject", 15), Nest("EventType", 3)),
        (_USER,),
        ("Image", "TargetObject", "EventType", "User"),
    ),
    13: EventPlan("Image", (Nest("TargetObject", 15),), (_USER,), ("Image", "TargetObject", "User")),
    14: EventPlan("Image", (Nest("TargetObject", 15),), (("NewName", 2), _USER), ("Image", "TargetObject", "NewName", "User")),
    22: EventPlan("Image", (Nest("QueryName", 15),), (("QueryStatus", 2), _USER), ("Image", "QueryName", "QueryStatus", "User")),
    25: EventPlan("Image", (Nest("Type", 3, missing=True),), (_USER,), ("Image", "Type", "User")),
}
for _eid in (2, 11, 15):
    EVENT_PLAN[_eid] = EventPlan("Image", (Nest("TargetFilename", 15),), (_USER,), ("Image", "TargetFilename", "User"))
for _eid in (17, 18):
    EVENT_PLAN[_eid] = EventPlan("Image", (Nest("PipeName", 15),), (_USER,), ("Image", "PipeName", "User"))
for _eid in (23, 26):
    EVENT_PLAN[_eid] = EventPlan(
        "Image",
        (Nest("TargetFilename", 15),),
        (("IsExecutable", 2), _USER),
        ("Image", "TargetFilename", "IsExecutable", "User"),
    )

EVENT_IDS: Tuple[int, ...] = tuple(sorted(EVENT_PLAN))
ACTORS: Tuple[str, ...] = ("Image", "SourceImage", "ImageLoaded")
# Every eventdata field the collector may read. CommandLine and ParentCommandLine are not among them: they are never
# queried, and neither is DestinationIp.
EVENTDATA_FIELDS = frozenset(
    {"RuleName"}
    | {name for plan in EVENT_PLAN.values() for name in plan.key_fields}
    | {name for plan in EVENT_PLAN.values() for name, _ in plan.details},
)


@dataclass
class FieldMap:
    """One usable shape: the index field of each base role and of each Sysmon eventdata field it maps."""

    shape: str
    time: str
    label: str
    agent: str
    level: str
    event_id: str
    channel: str
    eventdata: Dict[str, str] = field(default_factory=dict)
    computer: Optional[str] = None

    def ed(self, name: str) -> Optional[str]:
        return self.eventdata.get(name)

    def plan_mapped(self, eid: int) -> bool:
        """Whether every key field of the event is mapped (an unmapped detail is just never sent)."""
        return not self.unmapped_keys(eid)

    def unmapped_keys(self, eid: int) -> List[str]:
        """The event's key fields that are not mapped (or not aggregatable in every index): its patterns cannot be
        collected."""
        return [name for name in EVENT_PLAN[eid].key_fields if not self.ed(name)]


def _types(caps: Dict[str, Any], name: str) -> Dict[str, Any]:
    entry = caps.get(name)
    if not isinstance(entry, dict):
        return {}
    return {t: spec for t, spec in entry.items() if t != "unmapped" and isinstance(spec, dict)}


def _aggregatable(caps: Dict[str, Any], name: str) -> bool:
    """Mapped, and aggregatable in every index that maps it (a text mapping in one index fails its shards)."""
    types = _types(caps, name)
    return bool(types) and all(spec.get("aggregatable") for spec in types.values())


def _is_date(caps: Dict[str, Any], name: str) -> bool:
    types = _types(caps, name)
    return bool(types) and all(t in ("date", "date_nanos") for t in types)


def _keyword_variant(caps: Dict[str, Any], name: str) -> Optional[str]:
    if _aggregatable(caps, name):
        return name
    if _aggregatable(caps, name + ".keyword"):
        return name + ".keyword"
    return None


def discover(field_caps_response: Any) -> List[FieldMap]:
    """The usable shapes in a _field_caps answer (flat first). Empty when none is usable."""
    caps = (field_caps_response or {}).get("fields") if isinstance(field_caps_response, dict) else None
    if not isinstance(caps, dict):
        return []
    maps: List[FieldMap] = []
    for index, shape in enumerate(("flat", "nested")):
        roles: Dict[str, str] = {}
        for role, pair in BASE_FIELDS.items():
            name = pair[index]
            if role == "time":
                if _is_date(caps, name):
                    roles[role] = name
                continue
            chosen = _keyword_variant(caps, name)
            if chosen:
                roles[role] = chosen
        if len(roles) != len(BASE_FIELDS):
            continue
        prefix = EVENTDATA_PREFIX[shape]
        by_lower: Dict[str, List[str]] = {}
        for name in caps:
            if isinstance(name, str) and name.startswith(prefix):
                suffix = name[len(prefix) :]
                base = suffix[: -len(".keyword")] if suffix.endswith(".keyword") else suffix
                if "." in base:
                    continue
                by_lower.setdefault(base.lower(), []).append(prefix + base)
        eventdata: Dict[str, str] = {}
        for sysmon_name in sorted(EVENTDATA_FIELDS):
            candidates = sorted(set(by_lower.get(sysmon_name.lower(), [])))
            for candidate in candidates:
                chosen = _keyword_variant(caps, candidate)
                if chosen:
                    eventdata[sysmon_name] = chosen
                    break
        computer = _keyword_variant(caps, OPTIONAL_FIELDS["computer"][index])
        maps.append(FieldMap(shape=shape, eventdata=eventdata, computer=computer, **roles))
    return maps
