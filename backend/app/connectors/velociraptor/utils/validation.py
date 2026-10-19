"""Input validation for values that reach Velociraptor VQL.

A single quote (or brace/backtick/newline) in a value interpolated into VQL text breaks
out of the VQL string literal and lets the caller append arbitrary VQL -- including an
``execve()`` subquery that runs OS commands on the Velociraptor server
(GHSA-5542-j2fc-gqjm).

Every caller now passes its values to Velociraptor as *query variables*
(``VQLCollectorArgs.env``, see ``UniversalService.execute_query``) and references them by
name, so no value is part of the query text. The validators below stay as a second line of
defence and keep error messages meaningful: they constrain the *identifier* fields
(client/agent id, org id, artifact name, flow id) to their known, machine-generated
formats. Free-form fields (a run_command ``command``, a collect ``file`` glob, artifact
parameter values) are NOT validated here; they only ever travel as query variables.

Artifact parameter *names* are the one exception: VQL's ``dict()`` takes literal keyword
names, so they are placed in the query text as backtick-quoted identifiers. They are only
accepted when they match a parameter the artifact itself declares, and must also pass
``validate_artifact_parameter_name``.
"""
import re

from fastapi import HTTPException

# Velociraptor client IDs are "C." followed by hex (e.g. C.475df76785008b04). The literal
# "server" addresses the Velociraptor server itself and is used by built-in server
# artifacts (e.g. Server.Utils.DeleteClient).
#
# In a multi-org deployment Velociraptor reports a client's id *within an org* with the org
# appended -- "C.<hex>-<ORGID>" -- and that suffixed form is the one the server matches on:
# flows(client_id='C.aaaaaaaaaaaaaaaa') returns nothing where
# flows(client_id='C.aaaaaaaaaaaaaaaa-OXXXXXXX') returns the flow. `sync_agents_velociraptor`
# stores exactly what clients() reports, so agents outside the root org carry the suffixed id
# and the un-suffixed pattern rejected CoPilot's own stored value (GitHub issue #1015).
# The optional suffix uses the same character class as _ORG_ID_PATTERN below, so this widens
# an accepted *format* without admitting any of the quote/backtick/brace/backslash/whitespace
# characters the validator exists to reject (GHSA-5542-j2fc-gqjm).
_CLIENT_ID_PATTERN = re.compile(r"^(server|C\.[0-9A-Fa-f]+(-[A-Za-z0-9._-]+)?)$")

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

# Artifact parameter names, e.g. "Glob", "Upload_File", "T1552.001 - 3" (AtomicRedTeam) or
# "Sidebar gadgets (Vista and higher)" (Sysinternals Autoruns); "$" and a little punctuation
# are allowed for generated triage artifacts. They are written into the query as a
# backtick-quoted identifier, which only a backtick can end, so the class excludes
# backticks, quotes, backslashes and every control character.
_ARTIFACT_PARAMETER_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_$][A-Za-z0-9 _.$()+,:/#@-]{0,255}$")

# Names CoPilot gives the query variables it passes in VQLCollectorArgs.env. A plain VQL
# identifier that is not a keyword, so it can be referenced bare (``client_id=ClientId``).
_VQL_VARIABLE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_VQL_KEYWORDS = frozenset(
    {
        "and",
        "as",
        "by",
        "desc",
        "explain",
        "false",
        "from",
        "group",
        "in",
        "let",
        "limit",
        "not",
        "null",
        "or",
        "order",
        "select",
        "true",
        "where",
    },
)


def validate_client_id(value: str) -> str:
    """Validate a Velociraptor client/agent id ("C.<hex>", "C.<hex>-<ORGID>", or "server")."""
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


def validate_artifact_parameter_name(value: str) -> str:
    """Validate an artifact parameter name before it is written into VQL as `name`.

    Callers must first check the name against the artifact's own parameter list; this is
    the format check behind that.
    """
    if not isinstance(value, str) or not _ARTIFACT_PARAMETER_NAME_PATTERN.fullmatch(value):
        raise HTTPException(status_code=400, detail="Invalid Velociraptor artifact parameter name")
    return value


def validate_vql_variable_name(value: str) -> str:
    """Validate the name of a query variable CoPilot passes in ``VQLCollectorArgs.env``.

    These names are chosen in code, never by a user, so a failure is a programming error.
    """
    if not isinstance(value, str) or not _VQL_VARIABLE_NAME_PATTERN.fullmatch(value) or value.lower() in _VQL_KEYWORDS:
        raise ValueError(f"Invalid VQL variable name: {value!r}")
    return value


_HEX_DIGITS = frozenset(b"0123456789abcdefABCDEF")


def encode_vql_value(value: str) -> bytes:
    """`value` as UTF-8; a 400 for a string that cannot be (a lone surrogate), never a 500."""
    try:
        return value.encode("utf-8")
    except UnicodeEncodeError:
        raise HTTPException(status_code=400, detail="Value is not valid UTF-8 text") from None


def vql_string_literal_value(body: str) -> str:
    """The value Velociraptor read from the VQL string literal ``'<body>'``.

    Several request fields (a run_command ``command``, ``/collect`` parameter values, the
    ``/collect/file`` glob and root) were written into the query between single quotes, so
    Velociraptor applied VQL's backslash escapes to them, and clients learned to rely on
    that: the frontend doubles the backslashes of Windows paths in ``/collect`` parameters
    and ``format_file_path_for_os`` does the same for file collection. Those values now
    travel as query variables, which Velociraptor takes verbatim, so this applies the same
    unescaping first: every value that worked before reaches the artifact unchanged.

    A port of vfilter's ``utils.Unquote`` (unchanged since 2021), including its handling of
    an invalid ``\\x`` escape and its strict ``decode_hex`` (``[0-9A-Fa-f]`` only). Only the
    value is produced here; it is never put back into query text. A string that cannot be
    encoded as UTF-8 (a lone surrogate) is refused with a 400.
    """
    if not isinstance(body, str):
        raise TypeError("VQL string literal body must be a str")
    data = encode_vql_value(body)
    out = bytearray()
    end = len(data) - 1
    i = 0
    while i <= end:
        ch = data[i]
        if ch != 0x5C:  # not a backslash
            out.append(ch)
            i += 1
            continue
        if i >= end:  # a trailing backslash is dropped
            break
        nxt = data[i + 1]
        if nxt in (0x78, 0x58):  # \x / \X: a hex-encoded byte
            if i > end - 3:
                break
            high, low = data[i + 2], data[i + 3]
            if high in _HEX_DIGITS and low in _HEX_DIGITS:
                out.append(int(bytes((high, low)), 16))
                i += 4
            else:
                # vfilter copies in[j] (the output index) here and steps one byte.
                out.append(data[len(out)])
                i += 1
            continue
        out.append({0x72: 0x0D, 0x6E: 0x0A, 0x74: 0x09}.get(nxt, nxt))  # \r \n \t, else the char itself
        i += 2
    return out.decode("utf-8", errors="replace")
