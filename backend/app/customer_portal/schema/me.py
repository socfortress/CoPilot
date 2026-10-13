from typing import List

from pydantic import BaseModel


class PortalCustomer(BaseModel):
    """A customer as the portal shows it: its name, with the code as the key."""

    customer_code: str
    customer_name: str


class PortalMeResponse(BaseModel):
    """Who the portal user is and which customers they may see.

    The customers are read at request time, so a change to the user's assignments is
    visible at the next call — the JWT's ``customer_codes`` claim is a login-time copy.
    The 2FA state is deliberately not here: the Security tab reads it from
    ``/auth/2fa/status``, the endpoint that changes it.
    """

    success: bool
    message: str
    username: str
    role: str
    customers: List[PortalCustomer]
