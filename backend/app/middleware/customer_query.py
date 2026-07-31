from typing import List
from typing import Optional

from fastapi import Query
from fastapi import Request


def customer_codes_query(
    request: Request,
    customer_codes: Optional[List[str]] = Query(
        None,
        description="Optional subset of customer codes to scope the results to",
    ),
    customer_code: Optional[str] = Query(
        None,
        description="Deprecated single-customer alias for customer_codes — kept so callers predating multi-customer filtering keep working",
    ),
) -> Optional[List[str]]:
    """Parse customer code filters from repeated, bracketed or legacy-singular query params.

    FastAPI expects ``?customer_codes=a&customer_codes=b``. Some clients send
    ``customer_codes[]=a`` instead — accept both so portal filters work.

    ``customer_code=a`` is the pre-multi-customer spelling. Folding it in here means an
    endpoint can move from single to multi filtering without breaking existing callers,
    and without each route re-implementing the fallback.
    """
    bracket_codes = request.query_params.getlist("customer_codes[]")
    # isinstance rather than a plain truthiness check: called directly (tests, service-level
    # reuse) the default is FastAPI's ``Query(None)`` sentinel, which is truthy and would be
    # wrapped into a bogus ``[Query(None)]`` filter. FastAPI's DI resolves it to None itself.
    legacy_code = [customer_code] if isinstance(customer_code, str) and customer_code else None
    codes = customer_codes or bracket_codes or legacy_code or None
    return codes if codes else None
