from fastapi import HTTPException
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.universal_models import Customers


async def ensure_customer_exists(session: AsyncSession, customer_code: str) -> None:
    """404 unless ``customer_code`` names an existing customer."""
    result = await session.execute(select(Customers.customer_code).where(Customers.customer_code == customer_code))
    if result.scalars().first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Customer {customer_code} not found")
