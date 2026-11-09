"""GHCR faked for the talon-analyst release check (``utils/ghcr_client.py``): the anonymous token,
then the tag list in pages linked by ``Link: <…>; rel="next"`` as GHCR sends them, served by an
``httpx.MockTransport`` under the real client. No network."""
import asyncio

import httpx

TOKEN = "djE6c29jZm9ydHJlc3MvdGFsb24tYW5hbHlzdC1hcGk6MTIzNDU2Nzg5MA=="
TAGS_PATH = "/v2/socfortress/talon-analyst-api/tags/list"
#: As GHCR lists them: in push order, ``latest`` and ``sha-…`` among the releases.
TAGS = ["0.1.0", "latest", "sha-2d71450fe7c360cdcc3016e30a76703e0bab1fbb", "0.1.2", "0.1.3", "sha-704778514fcded753cfbf24d07e04c0840511a69"]


def ghcr(tags=None, overrides=None, page_size=None):
    """GHCR serving talon-analyst-api's ``tags`` (default ``TAGS``), at most ``page_size`` a page;
    ``overrides`` maps a path to a response, a callable(request) -> response, or an exception."""
    tags = list(TAGS if tags is None else tags)
    overrides = overrides or {}

    def tag_page(request):
        if request.headers.get("authorization") != f"Bearer {TOKEN}":
            return httpx.Response(401, json={"errors": [{"code": "UNAUTHORIZED"}]})
        n = int(request.url.params.get("n", "100"))
        if page_size:
            n = min(n, page_size)
        last = request.url.params.get("last")
        start = tags.index(last) + 1 if last else 0
        page = tags[start : start + n]
        headers = {}
        if start + n < len(tags):
            headers["Link"] = f'<{TAGS_PATH}?last={page[-1]}&n={n}>; rel="next"'
        return httpx.Response(200, json={"name": "socfortress/talon-analyst-api", "tags": page}, headers=headers)

    defaults = {
        "/token": lambda r: httpx.Response(200, json={"token": TOKEN}),
        TAGS_PATH: tag_page,
    }

    def respond(request):
        answer = overrides.get(request.url.path, defaults.get(request.url.path))
        if answer is None:
            return httpx.Response(404, json={"errors": [{"code": "NAME_UNKNOWN"}]})
        if isinstance(answer, Exception):
            raise answer
        return answer(request) if callable(answer) else answer

    return respond


class Registry:
    """The fake GHCR's transport, recording every request."""

    def __init__(self, respond):
        self.respond = respond
        self.requests = []

    async def handler(self, request):
        self.requests.append(request)
        answer = self.respond(request)
        if asyncio.iscoroutine(answer):
            answer = await answer
        return answer

    def new_client(self):
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handler), follow_redirects=False)

    def paths(self):
        return [r.url.path for r in self.requests]
