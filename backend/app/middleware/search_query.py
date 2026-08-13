from dataclasses import dataclass
from typing import Callable
from typing import Optional

from fastapi import Query
from sqlalchemy import or_


@dataclass
class SearchParams:
    """A text-search + row-cap pair, shared by every endpoint the search palette hits."""

    search: Optional[str] = None
    limit: Optional[int] = None


def search_query(
    search: Optional[str] = Query(None, description="Case-insensitive substring match"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Cap the number of returned results (used by the search palette)"),
) -> SearchParams:
    """FastAPI dependency exposing the palette's ``?search=&limit=`` pair once, instead of

    re-declaring the same two ``Query(...)`` params on every list endpoint. Mirrors
    ``customer_codes_query`` in ``customer_query.py``.
    """
    return SearchParams(search=search, limit=limit)


def apply_search_limit(statement, params: SearchParams, *columns):
    """Add a case-insensitive substring filter over ``columns`` + a row cap to a SELECT.

    Case-insensitive (``ilike``) so it matches the in-memory ``filter_and_limit`` path
    and the "case-insensitive" contract the endpoints document.
    """
    if params.search and columns:
        term = f"%{params.search}%"
        statement = statement.where(or_(*(column.ilike(term) for column in columns)))
    if params.limit is not None:
        statement = statement.limit(params.limit)
    return statement


def filter_and_limit(rows: list, params: SearchParams, key: Callable[[object], object]) -> list:
    """Case-insensitive substring filter + cap over an already-loaded list.

    ``key`` returns the searchable text for a row (join several fields with a space to
    match against more than one). Used by the cache/in-memory endpoints (scheduler,
    catalog stories/rules, indices) that have no SQL query to push the filter into.
    """
    if params.search:
        needle = params.search.lower()
        rows = [row for row in rows if needle in str(key(row)).lower()]
    if params.limit is not None:
        rows = rows[: params.limit]
    return rows
