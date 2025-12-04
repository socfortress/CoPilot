"""URL-related utility helpers."""

from __future__ import annotations

from urllib.parse import quote
from urllib.parse import urlparse
from urllib.parse import urlunparse


def _format_netloc(username: str | None, password: str | None, host: str, port: int | None) -> str:
    if not host:
        return ""
    # Bracket raw IPv6 literals without brackets
    if ":" in host and not host.startswith("[") and not host.endswith("]"):
        host = f"[{host}]"

    userinfo = ""
    if username:
        # Re-encode to avoid invalid characters in userinfo
        u = quote(username, safe="")  # RFC 3986
        if password is not None:
            p = quote(password, safe="")
            userinfo = f"{u}:{p}@"
        else:
            userinfo = f"{u}@"

    return f"{userinfo}{host}" if port is None else f"{userinfo}{host}:{port}"


def ensure_host_port(endpoint: str, port: int) -> str:
    if not endpoint:
        return endpoint
    if not (1 <= port <= 65535):
        raise ValueError("port must be in 1..65535")

    # Normalize scheme handling:
    has_scheme = "://" in endpoint
    scheme_prefix = "" if has_scheme else "//"
    parsed = urlparse(f"{scheme_prefix}{endpoint}")

    # Already has an explicit port
    if parsed.port is not None:
        return endpoint

    # Raw netloc as it appeared (for precise replacement)
    raw_netloc = parsed.netloc or ""
    # urlparse can return 'host:' when no digits after ':'
    if raw_netloc.endswith(":") and parsed.port is None:
        raw_netloc = raw_netloc[:-1]

    # Host fallback when netloc is empty in no-scheme cases like 'host/path'
    host = parsed.hostname or (parsed.path.split("/", 1)[0] if not parsed.netloc else "")

    new_netloc = _format_netloc(parsed.username, parsed.password, host or "", port)
    if not new_netloc:
        return endpoint  # cannot determine host

    if has_scheme:
        # Rebuild with urlunparse to preserve path, query, fragment
        return urlunparse(
            (
                parsed.scheme,
                new_netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            ),
        )

    # No scheme: replace only the authority portion at the start
    if parsed.netloc:
        return endpoint.replace(parsed.netloc, new_netloc, 1)
    # Fallback for 'host[/...]'
    remainder = endpoint[len(host) :] if host and endpoint.startswith(host) else endpoint
    return f"{new_netloc}{remainder}"
