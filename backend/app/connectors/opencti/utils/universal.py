"""
OpenCTI GraphQL transport.

Everything CoPilot asks OpenCTI goes through `send_graphql_request` (one
document) or `paginate_graphql` (a Relay connection walked page by page), so
new features only need to write a query and a service function on top.

Two things about the OpenCTI API that the helpers here exist to absorb:

- **Failures arrive as HTTP 200.** A bad token, a malformed query or a missing
  capability all come back 200 with an `errors` array (`AUTH_REQUIRED`,
  `GRAPHQL_VALIDATION_FAILED`, `FORBIDDEN_ACCESS`, …) and, often, a `data`
  object full of nulls. Treating the status code as the verdict reports a
  revoked token as a healthy connector, so any `errors` entry is a failure.
- **Lists are Relay connections** (`edges { node }` + `pageInfo`), paged with
  `first` / `after`. `paginate_graphql` walks one given a path to it.

Speaks plain GraphQL over `httpx` rather than `pycti`: the SDK is synchronous
and has to track the server's exact version, while a GraphQL document keeps
working across OpenCTI releases as long as the fields it names exist.
"""

from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Sequence

import httpx
from loguru import logger

from app.connectors.utils import get_connector_info_from_db
from app.db.db_session import get_db_session

OPENCTI_CONNECTOR_NAME = "OpenCTI"
GRAPHQL_PATH = "/graphql"
DEFAULT_TIMEOUT = 30.0
# OpenCTI caps `first` at 5000, but pages that large make one slow request out
# of what should be several quick ones.
DEFAULT_PAGE_SIZE = 100

VERIFY_QUERY = "query CoPilotVerify { about { version } me { name user_email } }"


def build_graphql_url(connector_url: str) -> str:
    """
    Resolve the GraphQL endpoint from the stored connector URL.

    Operators paste either the platform URL (`http://opencti:8080`) or the
    endpoint itself (`http://opencti:8080/graphql`); both must work.
    """
    base = (connector_url or "").strip().rstrip("/")
    if base.endswith(GRAPHQL_PATH):
        return base
    return f"{base}{GRAPHQL_PATH}"


def _build_headers(api_key: Optional[str]) -> Dict[str, str]:
    """Build request headers with Bearer token authentication."""
    return {
        "Authorization": f"Bearer {api_key or ''}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def format_graphql_errors(errors: List[Dict[str, Any]]) -> str:
    """Flatten a GraphQL `errors` array into one readable line, keeping each error's code."""
    parts = []
    for error in errors:
        message = error.get("message", "Unknown error")
        code = (error.get("extensions") or {}).get("code") or error.get("name")
        parts.append(f"{message} ({code})" if code else message)
    return "; ".join(parts)


def filter_group(filters: Sequence[Dict[str, Any]], mode: str = "and") -> Dict[str, Any]:
    """
    Build an OpenCTI `FilterGroup` variable.

    Args:
        filters: Items built with `filter_item`.
        mode: How the items combine — "and" or "or".
    """
    return {"mode": mode, "filters": list(filters), "filterGroups": []}


def filter_item(key: Sequence[str] | str, values: Sequence[Any], operator: str = "eq", mode: str = "or") -> Dict[str, Any]:
    """
    Build one entry of an OpenCTI `FilterGroup`.

    Several keys in one item are OR-ed together (with `mode="or"`), which is how
    a single IOC value is matched against `value` *and* every hash field at once.
    """
    return {
        "key": [key] if isinstance(key, str) else list(key),
        "values": list(values),
        "operator": operator,
        "mode": mode,
    }


async def _post_graphql(
    client: httpx.AsyncClient,
    attributes: Dict[str, Any],
    query: str,
    variables: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    POST one GraphQL document with an already-resolved connector.

    Returns the standard envelope: `success`, `message`, `data`, `errors`.
    `data` is passed through even on failure — a partial result can still be
    worth reading — but `success` is False whenever `errors` is non-empty.
    """
    url = build_graphql_url(attributes.get("connector_url"))
    try:
        response = await client.post(
            url,
            headers=_build_headers(attributes.get("connector_api_key")),
            json={"query": query, "variables": variables or {}},
        )
    except httpx.HTTPError as e:
        logger.error(f"OpenCTI request to {url} failed: {e!r}")
        return {"success": False, "message": f"Failed to reach OpenCTI at {url}: {e!r}", "data": None, "errors": []}

    try:
        body = response.json()
    except ValueError:
        logger.error(f"OpenCTI returned a non-JSON response ({response.status_code}) from {url}")
        return {
            "success": False,
            "message": f"OpenCTI returned a non-JSON response with status {response.status_code}",
            "data": None,
            "errors": [],
        }

    if not isinstance(body, dict):
        return {"success": False, "message": "OpenCTI returned an unexpected response shape", "data": None, "errors": []}

    errors = body.get("errors") or []
    data = body.get("data")
    if errors:
        message = format_graphql_errors(errors)
        logger.error(f"OpenCTI GraphQL error: {message}")
        return {"success": False, "message": f"OpenCTI GraphQL error: {message}", "data": data, "errors": errors}

    if response.status_code >= 400:
        logger.error(f"OpenCTI returned HTTP {response.status_code} from {url}")
        return {"success": False, "message": f"OpenCTI returned HTTP {response.status_code}", "data": data, "errors": []}

    return {"success": True, "message": "Successfully retrieved data", "data": data, "errors": []}


async def _get_attributes(connector_name: str) -> Optional[Dict[str, Any]]:
    async with get_db_session() as session:
        return await get_connector_info_from_db(connector_name, session)


def _missing_connector(connector_name: str) -> Dict[str, Any]:
    logger.error(f"No {connector_name} connector found in the database")
    return {"success": False, "message": f"No {connector_name} connector found in the database", "data": None, "errors": []}


async def send_graphql_request(
    query: str,
    variables: Optional[Dict[str, Any]] = None,
    connector_name: str = OPENCTI_CONNECTOR_NAME,
    timeout: float = DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    """
    Send one GraphQL document to OpenCTI using the stored connector credentials.

    Args:
        query: The GraphQL document.
        variables: Values for the document's `$variables`. Always pass user
            input this way, never by interpolating it into `query`.
        connector_name: The connector row to use. Defaults to "OpenCTI".
        timeout: Request timeout in seconds.

    Returns:
        Dict[str, Any]: `success`, `message`, `data` (the GraphQL `data`
        object) and `errors` (the raw GraphQL errors, empty on success).
    """
    attributes = await _get_attributes(connector_name)
    if attributes is None:
        return _missing_connector(connector_name)
    async with httpx.AsyncClient(verify=False, timeout=timeout) as client:
        return await _post_graphql(client, attributes, query, variables)


def _dig(data: Any, path: Sequence[str]) -> Any:
    for key in path:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


async def paginate_graphql(
    query: str,
    connection_path: Sequence[str],
    variables: Optional[Dict[str, Any]] = None,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_items: Optional[int] = None,
    connector_name: str = OPENCTI_CONNECTOR_NAME,
    timeout: float = DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    """
    Walk a Relay connection to the end (or to `max_items`) and return every node.

    The query must declare `$first: Int` and `$after: ID` and pass them to the
    connection, and must select `pageInfo { hasNextPage endCursor }` and
    `edges { node { … } }` on it.

    Args:
        query: The GraphQL document.
        connection_path: Keys from `data` down to the connection, e.g.
            `["indicators"]` or `["stixCoreObject", "reports"]`.
        variables: Other variables for the query. `first` / `after` are managed here.
        page_size: Nodes requested per page.
        max_items: Stop once this many nodes are collected. None walks everything.
        connector_name: The connector row to use. Defaults to "OpenCTI".
        timeout: Per-request timeout in seconds.

    Returns:
        Dict[str, Any]: The standard envelope with `data` set to the list of
        nodes and `global_count` set to the server's total for the connection.
        On a mid-walk failure `data` holds the nodes gathered so far.
    """
    attributes = await _get_attributes(connector_name)
    if attributes is None:
        return _missing_connector(connector_name)

    nodes: List[Dict[str, Any]] = []
    after: Optional[str] = None
    global_count: Optional[int] = None
    seen_cursors = set()

    async with httpx.AsyncClient(verify=False, timeout=timeout) as client:
        while True:
            first = page_size if max_items is None else min(page_size, max_items - len(nodes))
            page_variables = {**(variables or {}), "first": first, "after": after}
            response = await _post_graphql(client, attributes, query, page_variables)
            if not response["success"]:
                return {**response, "data": nodes, "global_count": global_count}

            connection = _dig(response["data"], connection_path)
            if not isinstance(connection, dict):
                message = f"OpenCTI response has no connection at {'.'.join(connection_path)}"
                logger.error(message)
                return {"success": False, "message": message, "data": nodes, "errors": [], "global_count": global_count}

            page_info = connection.get("pageInfo") or {}
            if global_count is None:
                global_count = page_info.get("globalCount")
            nodes.extend(edge["node"] for edge in connection.get("edges") or [] if edge and edge.get("node") is not None)

            cursor = page_info.get("endCursor")
            if max_items is not None and len(nodes) >= max_items:
                break
            # A cursor the server has already handed out means it is not
            # advancing; stop rather than loop forever.
            if not page_info.get("hasNextPage") or not cursor or cursor in seen_cursors:
                break
            seen_cursors.add(cursor)
            after = cursor

    return {
        "success": True,
        "message": f"Retrieved {len(nodes)} items",
        "data": nodes,
        "errors": [],
        "global_count": global_count,
    }


async def verify_opencti_credentials(attributes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifies the connection to OpenCTI.

    Asks for `about` and `me`, both of which require a valid token — and a bad
    token still answers HTTP 200, so the verdict comes from the GraphQL errors.

    Returns:
        dict: A dictionary containing 'connectionSuccessful' status and a message.
    """
    if not (attributes.get("connector_url") or "").strip():
        return {"connectionSuccessful": False, "message": "No OpenCTI URL is configured"}

    url = build_graphql_url(attributes["connector_url"])
    logger.info(f"Verifying the OpenCTI connection to {url}")
    async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
        response = await _post_graphql(client, attributes, VERIFY_QUERY)

    if not response["success"]:
        return {"connectionSuccessful": False, "message": f"Connection to {url} failed: {response['message']}"}

    data = response["data"] or {}
    version = (data.get("about") or {}).get("version")
    user = (data.get("me") or {}).get("name")
    if not version:
        return {"connectionSuccessful": False, "message": f"Connection to {url} failed: OpenCTI did not report a version"}

    logger.info(f"Connection to {url} successful (OpenCTI {version}, user {user})")
    return {
        "connectionSuccessful": True,
        "message": f"OpenCTI connection successful (version {version}, authenticated as {user})",
    }


async def verify_opencti_connection(connector_name: str = OPENCTI_CONNECTOR_NAME) -> Optional[Dict[str, Any]]:
    """
    Verifies the connection to OpenCTI using stored connector credentials.

    Args:
        connector_name (str): The name of the connector. Defaults to "OpenCTI".

    Returns:
        Optional[Dict[str, Any]]: Connection verification result, or None when no connector row exists.
    """
    attributes = await _get_attributes(connector_name)
    if attributes is None:
        logger.error("No OpenCTI connector found in the database")
        return None
    return await verify_opencti_credentials(attributes)
