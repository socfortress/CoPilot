from fastapi import APIRouter
from fastapi import HTTPException
from loguru import logger

from app.auth.models.users import SMTP
from app.auth.models.users import SMTPInput
from app.auth.services.universal import select_all_users
from app.auth.utils import AuthHandler
from app.db.db_session import session
from app.smtp.schema.configure import SMTPResponse

smtp_reports_router = APIRouter()
auth_handler = AuthHandler()


# ! TODO: Add SMTP reporting all things. Example is in the services/reports.py and services/create_report.py file
@smtp_reports_router.post(
    "/{user_id}/register",
    response_model=SMTPResponse,
    status_code=200,
    description="Register new SMTP for user",
)
async def register(user_id: int, smtp: SMTPInput):
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
