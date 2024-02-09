from fastapi import APIRouter
from fastapi import HTTPException
from loguru import logger

from app.auth.models.users import SMTP
from app.auth.models.users import SMTPInput
from app.auth.services.universal import select_all_users
from app.auth.utils import AuthHandler
from app.db.db_session import session
from app.smtp.schema.configure import SMTPResponse

smtp_configure_router = APIRouter()
auth_handler = AuthHandler()


@smtp_configure_router.post(
    "/{user_id}/register",
    response_model=SMTPResponse,
    status_code=200,
    description="Register new SMTP for user",
)
async def register(user_id: int, smtp: SMTPInput):
    """
    Register a new SMTP configuration for a user.

    Args:
        user_id (int): The ID of the user.
        smtp (SMTPInput): The SMTP configuration input.

    Returns:
        dict: A dictionary containing the message and success status of the operation.
    """
    users = select_all_users()
    logger.info(users)
    if not any(x.id == user_id for x in users):
        raise HTTPException(status_code=400, detail="User not found")
    # Check if SMTP already exists for user
    smtp_found = session.query(SMTP).filter(SMTP.user_id == user_id).first()
    if smtp_found:
        raise HTTPException(status_code=400, detail="SMTP already exists for user")
    hashed_pwd = auth_handler.get_password_hash(smtp.smtp_password)
    u = SMTP(
        email=smtp.email,
        smtp_password=hashed_pwd,
        smtp_server=smtp.smtp_server,
        smtp_port=smtp.smtp_port,
        user_id=user_id,
    )
    session.add(u)
    session.commit()
    return {"message": "SMTP created successfully", "success": True}


@smtp_configure_router.get(
    "/{user_id}",
    response_model=SMTP,
    status_code=200,
    description="Get SMTP for user",
)
async def get_smtp(user_id: int):
    """
    Get SMTP configuration for a specific user.

    Args:
        user_id (int): The ID of the user.

    Returns:
        SMTP: The SMTP configuration for the user.

    Raises:
        HTTPException: If the user is not found or if SMTP configuration is not found for the user.
    """
    users = select_all_users()
    if not any(x.id == user_id for x in users):
        raise HTTPException(status_code=400, detail="User not found")
    smtp_found = session.query(SMTP).filter(SMTP.user_id == user_id).first()
    if not smtp_found:
        raise HTTPException(status_code=400, detail="SMTP not found for user")
    return smtp_found


@smtp_configure_router.put(
    "/{user_id}",
    response_model=SMTPResponse,
    status_code=200,
    description="Update SMTP for user",
)
async def update_smtp(user_id: int, smtp: SMTPInput):
    """
    Update SMTP settings for a user.

    Args:
        user_id (int): The ID of the user.
        smtp (SMTPInput): The SMTP settings to update.

    Raises:
        HTTPException: If the user is not found or SMTP settings are not found for the user.

    Returns:
        dict: A dictionary containing the message and success status of the update.
    """
    users = select_all_users()
    if not any(x.id == user_id for x in users):
        raise HTTPException(status_code=400, detail="User not found")
    smtp_found = session.query(SMTP).filter(SMTP.user_id == user_id).first()
    if not smtp_found:
        raise HTTPException(status_code=400, detail="SMTP not found for user")
    smtp_found.email = smtp.email
    smtp_found.smtp_server = smtp.smtp_server
    smtp_found.smtp_port = smtp.smtp_port
    smtp_found.smtp_password = auth_handler.get_password_hash(smtp.smtp_password)
    session.commit()
    return {"message": "SMTP updated successfully", "success": True}


@smtp_configure_router.delete(
    "/{user_id}",
    response_model=SMTPResponse,
    status_code=200,
    description="Delete SMTP for user",
)
async def delete_smtp(user_id: int):
    """
    Delete SMTP configuration for a user.

    Args:
        user_id (int): The ID of the user.

    Raises:
        HTTPException: If the user is not found or if SMTP configuration is not found for the user.

    Returns:
        dict: A dictionary containing the success message.
    """
    users = select_all_users()
    if not any(x.id == user_id for x in users):
        raise HTTPException(status_code=400, detail="User not found")
    smtp_found = session.query(SMTP).filter(SMTP.user_id == user_id).first()
    if not smtp_found:
        raise HTTPException(status_code=400, detail="SMTP not found for user")
    session.delete(smtp_found)
    session.commit()
    return {"message": "SMTP deleted successfully", "success": True}
