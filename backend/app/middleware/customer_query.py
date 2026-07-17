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
) -> Optional[List[str]]:
    """Parse customer code filters from repeated or bracketed query params.

    FastAPI expects ``?customer_codes=a&customer_codes=b``. Some clients send
    ``customer_codes[]=a`` instead — accept both so portal filters work.
    """
    bracket_codes = request.query_params.getlist("customer_codes[]")
    codes = customer_codes or bracket_codes or None
    return codes if codes else None
