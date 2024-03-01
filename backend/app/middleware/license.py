from datetime import datetime
from datetime import timedelta
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from loguru import logger
from typing import Optional
from typing import Union
from licensing.models import *
from licensing.methods import Key, Helpers
import os

import requests
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException


license_router = APIRouter()

@license_router.post(
    "/verify",
    description="Verify the license",
)
async def verify_license():
    """
    Verify the license key.

    Args:
        license_key (str): The license key to verify.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        LicenseVerificationResponse: A Pydantic model containing the verification status and message.
    """
    RSAPublicKey = "<RSAKeyValue><Modulus>vJusFdHoph6IyVrUnL7E3kH5YKsBdnIN5k+rW6J0g7gFPy7wBJfSDCtUMxB7XcOKiC1aZu/Wt7ShdzYsmYcd/duu4+qIMfP4CbW6RPIBFyj1Tk6xj72zKqU42sUymzzVVIeCtNdV0fkTdEZtI1zJeSXPcWtyY4PWOV1mFG9PST6uCuNDC+mXVESDyYHwd7JU8ZHDCEYD2eDJ4/58kT+jNpobS2BeRc4GMNPwISK/BNQG62X2sFJUWv7gB+qGXd/zqmucKEnB7Y1RyIVgnQPXKI/nrdoFHxRcUtEjhBMeqAQB0R8QvrMmlx1B7HzR+KBARTJdiPBrwxbopvhJus6c6Q==</Modulus><Exponent>AQAB</Exponent></RSAKeyValue>"
    auth = os.getenv("CRYPTOLENS_AUTH")
    if not auth:
        raise HTTPException(status_code=500, detail="Auth token not found")

    result = Key.activate(
        token=auth,
        rsa_pub_key=RSAPublicKey,
        product_id=24355,
        key="MVWEY-IAQME-IKIVL-SAFPH",
        machine_code=Helpers.GetMachineCode(v=2),
    )

    logger.info(result)
    return result

@license_router.post(
    "/create_new_key",
    description="Create a new license key",
)
async def create_new_license_key():
    """
    Create a new license key.

    Args:
        license_key (str): The license key to verify.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        LicenseVerificationResponse: A Pydantic model containing the verification status and message.
    """
    RSAPublicKey = "<RSAKeyValue><Modulus>vJusFdHoph6IyVrUnL7E3kH5YKsBdnIN5k+rW6J0g7gFPy7wBJfSDCtUMxB7XcOKiC1aZu/Wt7ShdzYsmYcd/duu4+qIMfP4CbW6RPIBFyj1Tk6xj72zKqU42sUymzzVVIeCtNdV0fkTdEZtI1zJeSXPcWtyY4PWOV1mFG9PST6uCuNDC+mXVESDyYHwd7JU8ZHDCEYD2eDJ4/58kT+jNpobS2BeRc4GMNPwISK/BNQG62X2sFJUWv7gB+qGXd/zqmucKEnB7Y1RyIVgnQPXKI/nrdoFHxRcUtEjhBMeqAQB0R8QvrMmlx1B7HzR+KBARTJdiPBrwxbopvhJus6c6Q==</Modulus><Exponent>AQAB</Exponent></RSAKeyValue>"
    auth = os.getenv("CRYPTOLENS_AUTH")
    if not auth:
        raise HTTPException(status_code=500, detail="Auth token not found")

    result = Key.create_key(
        token=auth,
        product_id=24355,
        notes="Test Key",
        new_customer=True,
        name="Test Customer",
        email="test@email.com",
        company_name="Test Company",
    )

    logger.info(result)
    return result
