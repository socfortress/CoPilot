"""Input validation for values interpolated into Velociraptor VQL.

CoPilot builds VQL by f-string interpolation and executes it server-side over the
Velociraptor gRPC API. A single quote (or brace/backtick/newline) in an interpolated
value breaks out of the VQL string literal and lets the caller append arbitrary VQL —
including an ``execve()`` subquery that runs OS commands on the Velociraptor server
(GHSA-5542-j2fc-gqjm).

These validators constrain the *identifier* fields (client/agent id, org id, artifact
name, flow id) to their known, machine-generated formats, so an injection payload can
never reach the query. They are intentionally strict: every legitimate value matches,
and anything containing a quote, backtick, brace, backslash, whitespace, or newline is
rejected. Free-form fields (a run_command ``command``, a collect ``file`` glob, artifact
``parameters``) are NOT identifiers and must NOT be validated here — those are secured by
parameterized/bound VQL, not by format rejection.
"""
import re

from fastapi import HTTPException

# Velociraptor client IDs are "C." followed by hex (e.g. C.475df76785008b04). The literal
# "server" addresses the Velociraptor server itself and is used by built-in server
# artifacts (e.g. Server.Utils.DeleteClient).
_CLIENT_ID_PATTERN = re.compile(r"^(server|C\.[0-9A-Fa-f]+)$")

# Org IDs are "root" (the default org) or generated ids like "O1234ABCD".
_ORG_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")

# Artifact names are dotted alphanumeric segments, e.g. Windows.AttackSimulation.AtomicRedTeam
# or Custom.Linux.Remediation.Quarantine. Source notation (Artifact/Source, e.g.
# Generic.Client.Info/BasicInformation) uses a slash. None of the allowed characters can
# break out of a VQL string literal.
_ARTIFACT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._/-]+$")

# Flow / session IDs are "F." followed by alphanumerics, e.g. F.CMVK8U....
_FLOW_ID_PATTERN = re.compile(r"^F\.[A-Za-z0-9]+$")

# Characters that can break out of a (single- or double-quoted) VQL string literal. Used for
# values like a hostname that are too variable to pin to a strict format but must never carry
# a string-literal escape.
_VQL_BREAKOUT_CHARS = ("'", '"', "`", "\\", "\n", "\r")


def validate_client_id(value: str) -> str:
    """Validate a Velociraptor client/agent id ("C.<hex>" or "server")."""
    if not isinstance(value, str) or not _CLIENT_ID_PATTERN.fullmatch(value):
        raise HTTPException(status_code=400, detail="Invalid Velociraptor client id")
    return value


def validate_org_id(value: str) -> str:
    """Validate a Velociraptor org id ("root" or a generated org id)."""
    if not isinstance(value, str) or not _ORG_ID_PATTERN.fullmatch(value):
        raise HTTPException(status_code=400, detail="Invalid Velociraptor org id")
    return value


def validate_artifact_name(value: str) -> str:
    """Validate a Velociraptor artifact name (dotted alphanumeric segments)."""
    if not isinstance(value, str) or not _ARTIFACT_NAME_PATTERN.fullmatch(value):
        raise HTTPException(status_code=400, detail="Invalid Velociraptor artifact name")
    return value


def validate_flow_id(value: str) -> str:
    """Validate a Velociraptor flow/session id ("F.<alnum>")."""
    if not isinstance(value, str) or not _FLOW_ID_PATTERN.fullmatch(value):
        raise HTTPException(status_code=400, detail="Invalid Velociraptor flow id")
    return value


def validate_hostname(value: str) -> str:
    """Reject a hostname/asset name that could break out of a VQL string literal.

    Hostnames are too variable to pin to a strict format, but a legitimate one never
    contains a quote, backtick, backslash, or newline, so rejecting those is enough to
    prevent VQL injection via the client search (GHSA-5542-j2fc-gqjm).
    """
    if not isinstance(value, str) or any(ch in value for ch in _VQL_BREAKOUT_CHARS):
        raise HTTPException(status_code=400, detail="Invalid Velociraptor hostname")
    return value
