"""L1 validation for Graylog-only detection rules — the editor + CI linter.

Pure functions, no I/O. The SAME code is meant to run in the in-app editor (via
``POST /copilot_searches/validate``) and in the rule repo's CI, so the editor and
the repo gate can never disagree (see DETECTION_RULE_EDITOR.md §5, Milestone 1).

Scope is **Graylog-only** rules: a top-level ``graylog.query`` string, an optional
top-level ``aggregation`` block placed AFTER ``graylog``, and no ``search`` (OpenSearch
DSL) or ``parameters`` block. Covers structure + lint (L1), reference integrity as
warnings (L2), and Graylog query parse (L3); per-tenant field existence (L4) runs
inside the backtest, where a customer/stream is in scope.
"""
from __future__ import annotations

import dataclasses
import re
import uuid
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import yaml

try:  # jsonschema is present in the backend venv; degrade gracefully if not
    from jsonschema import Draft7Validator

    _HAVE_JSONSCHEMA = True
except Exception:  # noqa: BLE001
    _HAVE_JSONSCHEMA = False

# Canonical top-level key order (DETECTION_RULE_EDITOR.md §4).
CANONICAL_ORDER = [
    "name", "id", "version", "schema_version", "date", "author",
    "description", "data_source", "how_to_implement", "known_false_positives",
    "response", "tags", "graylog", "aggregation",
]
_ORDER_INDEX = {k: i for i, k in enumerate(CANONICAL_ORDER)}

SEVERITIES = {"low", "medium", "high", "critical"}
AGG_FUNCTIONS = {"count", "distinct_count"}
AGG_CONDITIONS = {">", ">=", "<", "<=", "=="}
FOLDED_SCALAR_KEYS = ("description", "how_to_implement", "known_false_positives")
FORBIDDEN_BLOCKS = ("search", "parameters")
_WINDOW_RE = re.compile(r"^\d+[smhd]$")

# --- L2 reference-integrity helpers (all L2 findings are WARNINGS: they flag
# --- likely mistakes, but enrichment pipelines can add fields we can't see) ---
_PLACEHOLDER_RE = re.compile(r"\$([A-Za-z_][\w.]*)\$")
_QUERY_FIELD_RE = re.compile(r"(?<![\w.])([A-Za-z_][\w.]*)\s*:")
_EXISTS_RE = re.compile(r"_exists_\s*:\s*([A-Za-z_][\w.]*)")
_RESERVED_QUERY_TOKENS = {"AND", "OR", "NOT", "TO", "_exists_"}
_MITRE_RE = re.compile(r"^T\d{4}(\.\d{3})?$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Rough risk_score bands per severity — deliberately wide; only flags clear mismatches.
_SEVERITY_SCORE_BANDS = {"low": (1, 40), "medium": (25, 75), "high": (55, 95), "critical": (75, 100)}


def _rule_used_fields(data: Dict[str, Any]) -> set:
    """Fields the rule actually uses: query fields + aggregation group_by/field."""
    graylog = data.get("graylog") if isinstance(data.get("graylog"), dict) else {}
    query = str(graylog.get("query") or "")
    fields = {m for m in _QUERY_FIELD_RE.findall(query) if m not in _RESERVED_QUERY_TOKENS}
    fields |= set(_EXISTS_RE.findall(query))
    agg = data.get("aggregation")
    if isinstance(agg, dict):
        fields |= {g for g in (agg.get("group_by") or []) if isinstance(g, str)}
        if agg.get("field"):
            fields.add(str(agg["field"]))
    return fields


@dataclasses.dataclass
class Finding:
    level: str  # "error" | "warning"
    code: str
    message: str
    path: str = ""
    line: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


# Structural JSON Schema (required fields + types). Deeper semantic rules that
# JSON Schema can't express (key order, quoted schema_version, count/distinct_count
# field coupling, folded scalars) are checked by hand below.
_JSON_SCHEMA = {
    "type": "object",
    "required": ["name", "id", "version", "schema_version", "description", "graylog"],
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "id": {"type": "string", "minLength": 1},
        "version": {"type": "integer", "minimum": 1},
        "schema_version": {"type": "string"},
        "date": {"type": "string"},
        "author": {"type": "string"},
        "description": {"type": "string", "minLength": 1},
        "data_source": {"type": "array", "items": {"type": "string"}},
        "how_to_implement": {"type": "string"},
        "known_false_positives": {"type": "string"},
        "response": {
            "type": "object",
            "properties": {
                "risk_score": {"type": "integer", "minimum": 0, "maximum": 100},
                "severity": {"type": "string", "enum": sorted(SEVERITIES)},
            },
        },
        "tags": {"type": "object"},
        "graylog": {
            "type": "object",
            "required": ["query"],
            "properties": {"query": {"type": "string", "minLength": 1}},
            "additionalProperties": False,
        },
        "aggregation": {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean"},
                "function": {"type": "string", "enum": sorted(AGG_FUNCTIONS)},
                "field": {"type": ["string", "null"]},
                "group_by": {"type": "array", "items": {"type": "string"}},
                "window": {"type": "string"},
                "execute_every": {"type": "string"},
                "threshold": {"type": "integer", "minimum": 1},
                "condition": {"type": "string", "enum": sorted(AGG_CONDITIONS)},
            },
        },
    },
}


def _line_of_key(raw: str, key: str) -> Optional[int]:
    """Best-effort 1-based line of a top-level ``key:`` in the raw YAML."""
    rx = re.compile(rf"^{re.escape(key)}\s*:", re.MULTILINE)
    m = rx.search(raw)
    if not m:
        return None
    return raw.count("\n", 0, m.start()) + 1


def lint_graylog_query(query: str, line: Optional[int] = None) -> List[Finding]:
    """L3: lightweight parse of a Graylog (Lucene-ish) query string.

    Not a full grammar — it catches the mistakes that would make Graylog reject
    the query at runtime (unbalanced quotes / parens / regex delimiters, dangling
    boolean operators) plus one perf advisory (leading ``.*`` in a regex). Balance
    checks ignore characters inside double-quoted strings and honour ``\\`` escapes.
    """
    out: List[Finding] = []
    q = query or ""
    if not q.strip():
        out.append(Finding("error", "GRAYLOG_QUERY_EMPTY", "graylog.query is empty.", path="graylog.query", line=line))
        return out

    in_quote = False
    escaped = False
    parens = 0
    went_negative = False
    slashes = 0
    for ch in q:
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == '"':
            in_quote = not in_quote
            continue
        if in_quote:
            continue
        if ch == "(":
            parens += 1
        elif ch == ")":
            parens -= 1
            if parens < 0:
                went_negative = True
        elif ch == "/":
            slashes += 1

    if in_quote:
        out.append(Finding("error", "GRAYLOG_QUERY_QUOTES", "Unbalanced double-quote in graylog.query.", path="graylog.query", line=line))
    if parens != 0 or went_negative:
        out.append(Finding("error", "GRAYLOG_QUERY_PARENS", "Unbalanced parentheses in graylog.query.", path="graylog.query", line=line))
    if slashes % 2 != 0:
        out.append(Finding("error", "GRAYLOG_QUERY_REGEX", "Unbalanced '/' — a regex literal (/.../) is not closed.", path="graylog.query", line=line))

    tokens = q.split()
    if tokens and tokens[0] in ("AND", "OR"):
        out.append(Finding("error", "GRAYLOG_QUERY_DANGLING_OP", f"Query starts with '{tokens[0]}'.", path="graylog.query", line=line))
    if tokens and tokens[-1] in ("AND", "OR", "NOT"):
        out.append(Finding("error", "GRAYLOG_QUERY_DANGLING_OP", f"Query ends with '{tokens[-1]}'.", path="graylog.query", line=line))

    if re.search(r"/\.\*", q):
        out.append(Finding("warning", "GRAYLOG_QUERY_LEADING_WILDCARD", "Leading '.*' in a regex scans everything — anchor it or use a literal where possible.", path="graylog.query", line=line))

    return out


def lint_rule_yaml(raw: str) -> List[Finding]:
    """Return the L1 findings for a raw YAML rule string (empty list == clean)."""
    findings: List[Finding] = []

    # --- parse -------------------------------------------------------------
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        line = None
        mark = getattr(exc, "problem_mark", None)
        if mark is not None:
            line = mark.line + 1
        return [Finding("error", "YAML_PARSE", f"YAML is not parseable: {getattr(exc, 'problem', exc)}", line=line)]

    if data is None:
        return [Finding("error", "EMPTY", "Rule is empty.")]
    if not isinstance(data, dict):
        return [Finding("error", "NOT_A_MAPPING", "A rule must be a YAML mapping (key: value), not a list or scalar.")]

    # --- forbidden (out-of-scope) blocks ----------------------------------
    for block in FORBIDDEN_BLOCKS:
        if block in data:
            findings.append(Finding(
                "error", "FORBIDDEN_BLOCK",
                f"'{block}' is out of scope for Graylog-only rules — remove it (this editor targets graylog.query only).",
                path=block, line=_line_of_key(raw, block),
            ))

    # --- structural JSON Schema -------------------------------------------
    if _HAVE_JSONSCHEMA:
        for err in sorted(Draft7Validator(_JSON_SCHEMA).iter_errors(data), key=lambda e: list(e.absolute_path)):
            path = ".".join(str(p) for p in err.absolute_path)
            top = str(err.absolute_path[0]) if err.absolute_path else None
            findings.append(Finding("error", "SCHEMA", err.message, path=path, line=_line_of_key(raw, top) if top else None))
    else:  # minimal fallback if jsonschema is unavailable
        for req in ("name", "id", "version", "schema_version", "description", "graylog"):
            if req not in data:
                findings.append(Finding("error", "SCHEMA", f"'{req}' is a required property", path=req))

    # --- graylog block: only 'query' --------------------------------------
    gl = data.get("graylog")
    if isinstance(gl, dict):
        extra = sorted(set(gl.keys()) - {"query"})
        if extra:
            findings.append(Finding(
                "error", "GRAYLOG_EXTRA_KEYS",
                f"graylog must contain only 'query'; found extra key(s): {', '.join(extra)}.",
                path="graylog", line=_line_of_key(raw, "graylog"),
            ))
        # L3 — parse the Graylog query string itself.
        if isinstance(gl.get("query"), str):
            findings.extend(lint_graylog_query(gl["query"], _line_of_key(raw, "graylog")))

    # --- schema_version must be a quoted string ---------------------------
    if "schema_version" in data and not isinstance(data["schema_version"], str):
        findings.append(Finding(
            "error", "SCHEMA_VERSION_UNQUOTED",
            'schema_version must be a quoted string, e.g. "1.0" (unquoted 1.0 parses as a number).',
            path="schema_version", line=_line_of_key(raw, "schema_version"),
        ))

    # --- id should be a UUID ----------------------------------------------
    rid = data.get("id")
    if isinstance(rid, str):
        try:
            uuid.UUID(rid)
        except ValueError:
            findings.append(Finding("warning", "ID_NOT_UUID", "id should be a UUID (generate a fresh one per rule).", path="id", line=_line_of_key(raw, "id")))

    # --- canonical key order ----------------------------------------------
    present = [k for k in data.keys() if k in _ORDER_INDEX]
    expected = sorted(present, key=lambda k: _ORDER_INDEX[k])
    if present != expected:
        findings.append(Finding(
            "warning", "KEY_ORDER",
            f"Top-level keys are out of canonical order. Expected: {', '.join(expected)}.",
        ))
    # aggregation must come after graylog specifically
    if "aggregation" in data and "graylog" in data:
        keys = list(data.keys())
        if keys.index("aggregation") < keys.index("graylog"):
            findings.append(Finding("error", "AGG_POSITION", "aggregation must appear AFTER the graylog block.", path="aggregation", line=_line_of_key(raw, "aggregation")))

    # --- aggregation semantics --------------------------------------------
    agg = data.get("aggregation")
    if isinstance(agg, dict):
        fn = agg.get("function")
        field = agg.get("field")
        if fn == "count" and field:
            findings.append(Finding("error", "AGG_FIELD_FORBIDDEN", "field must be null (or omitted) when function is 'count'.", path="aggregation.field", line=_line_of_key(raw, "aggregation")))
        if fn == "distinct_count" and not field:
            findings.append(Finding("error", "AGG_FIELD_REQUIRED", "field is required when function is 'distinct_count'.", path="aggregation.field", line=_line_of_key(raw, "aggregation")))
        win = agg.get("window")
        if isinstance(win, str) and not _WINDOW_RE.match(win):
            findings.append(Finding("warning", "AGG_WINDOW_FORMAT", "window should look like '10m' / '1h' / '30s' / '1d'.", path="aggregation.window", line=_line_of_key(raw, "aggregation")))

    # --- folded scalars for long text fields ------------------------------
    for key in FOLDED_SCALAR_KEYS:
        if key in data and isinstance(data.get(key), str):
            if not re.search(rf"^{re.escape(key)}\s*:\s*>", raw, re.MULTILINE):
                findings.append(Finding("warning", "FOLDED_SCALAR", f"{key} should use a folded scalar (>) for readable multi-line text.", path=key, line=_line_of_key(raw, key)))

    # --- data_source entries with a colon must be quoted ------------------
    ds = data.get("data_source")
    if isinstance(ds, list):
        for v in ds:
            if isinstance(v, str) and ":" in v and f'"{v}"' not in raw and f"'{v}'" not in raw:
                findings.append(Finding("warning", "DATA_SOURCE_QUOTE", f"data_source entry '{v}' contains ':' — quote it so YAML doesn't misparse it.", path="data_source"))

    # --- recommended metadata (soft) --------------------------------------
    for key in ("author", "date", "data_source", "response", "tags"):
        if key not in data:
            findings.append(Finding("warning", "MISSING_RECOMMENDED", f"'{key}' is recommended for a complete rule.", path=key))

    # --- L2: reference integrity (warnings only) ---------------------------
    used_fields = _rule_used_fields(data)
    response = data.get("response") if isinstance(data.get("response"), dict) else {}

    # $field$ placeholders in the alert message should be fields the rule uses.
    msg = response.get("message")
    if isinstance(msg, str):
        for ph in sorted(set(_PLACEHOLDER_RE.findall(msg))):
            if ph not in used_fields:
                findings.append(Finding("warning", "REF_MESSAGE_FIELD", f"response.message references ${ph}$ but the query/aggregation never uses that field — it may render blank in alerts.", path="response.message", line=_line_of_key(raw, "response")))

    # risk_objects / threat_objects should point at fields the rule uses.
    for kind, code in (("risk_objects", "REF_RISK_OBJECT"), ("threat_objects", "REF_THREAT_OBJECT")):
        items = response.get(kind)
        if isinstance(items, list):
            for obj in items:
                if isinstance(obj, dict) and isinstance(obj.get("field"), str) and obj["field"] not in used_fields:
                    findings.append(Finding("warning", code, f"response.{kind} field '{obj['field']}' is not used by the query/aggregation — the object may be empty on alerts.", path=f"response.{kind}", line=_line_of_key(raw, "response")))

    # MITRE technique id format.
    tags = data.get("tags") if isinstance(data.get("tags"), dict) else {}
    mitre = tags.get("mitre_attack_id")
    if isinstance(mitre, list):
        for mid in mitre:
            if isinstance(mid, str) and not _MITRE_RE.match(mid):
                findings.append(Finding("warning", "MITRE_ID_FORMAT", f"'{mid}' does not look like a MITRE ATT&CK technique id (e.g. T1059 or T1059.001).", path="tags.mitre_attack_id", line=_line_of_key(raw, "tags")))

    # severity vs risk_score sanity (wide bands — only clear mismatches).
    sev = str(response.get("severity") or "").lower()
    score = response.get("risk_score")
    if sev in _SEVERITY_SCORE_BANDS and isinstance(score, int) and not isinstance(score, bool):
        lo, hi = _SEVERITY_SCORE_BANDS[sev]
        if not (lo <= score <= hi):
            findings.append(Finding("warning", "SEVERITY_SCORE_MISMATCH", f"risk_score {score} is unusual for severity '{sev}' (expected roughly {lo}–{hi}).", path="response.risk_score", line=_line_of_key(raw, "response")))

    # date should be a quoted ISO date string.
    date_v = data.get("date")
    if isinstance(date_v, str) and not _DATE_RE.match(date_v):
        findings.append(Finding("warning", "DATE_FORMAT", 'date should be a quoted ISO date, e.g. "2026-08-26".', path="date", line=_line_of_key(raw, "date")))

    return findings


def lint_result(raw: str) -> Dict[str, Any]:
    """Convenience wrapper: {valid, error_count, warning_count, findings[]}."""
    findings = lint_rule_yaml(raw)
    errors = [f for f in findings if f.level == "error"]
    return {
        "valid": not errors,
        "error_count": len(errors),
        "warning_count": len(findings) - len(errors),
        "findings": [f.to_dict() for f in findings],
    }
