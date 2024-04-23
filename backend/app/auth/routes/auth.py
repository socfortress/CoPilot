from datetime import timedelta

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from fastapi import status
from fastapi.security import OAuth2PasswordRequestForm
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import PasswordReset
from app.auth.models.users import PasswordResetToken
from app.auth.models.users import User
from app.auth.models.users import UserInput
from app.auth.models.users import UserLogin
from app.auth.schema.auth import Token
from app.auth.schema.auth import UserLoginResponse
from app.auth.schema.auth import UserResponse
from app.auth.schema.user import UserBaseResponse
from app.auth.services.universal import find_user
from app.auth.services.universal import select_all_users
from app.auth.utils import AuthHandler
from app.db.db_session import get_db

ACCESS_TOKEN_EXPIRE_MINUTES = 1440

auth_router = APIRouter()
auth_handler = AuthHandler()


@auth_router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticates a user and generates an access token.

    Args:
        form_data (OAuth2PasswordRequestForm): The form data containing the username and password.

    Returns:
        dict: A dictionary containing the access token and token type.
    """
    # user = auth_handler.authenticate_user(form_data.username, form_data.password)

    user = await auth_handler.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = await auth_handler.encode_token(user.username, access_token_expires)
    logger.info(f"Access token: {access_token}")
    return {"access_token": access_token, "token_type": "bearer"}


@auth_router.get("/refresh", response_model=Token)
async def refresh_token(current_user: User = Depends(auth_handler.get_current_user)):
    """
    Refreshes the access token for the current user.

    Parameters:
    - current_user (User): The current authenticated user.

    Returns:
    - dict: A dictionary containing the refreshed access token and token type.
    """
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = await auth_handler.encode_token(
        current_user.username,
        access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@auth_router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    description="Register new user",
)
async def register(user: UserInput, session: AsyncSession = Depends(get_db)):
    """
    Register a new user.

    Args:
        user (UserInput): The user input data.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        dict: A dictionary containing the message and success status.
    """
    users = await select_all_users()
    if any(x.username == user.username for x in users):
        raise HTTPException(status_code=400, detail="Username is taken")
    hashed_pwd = auth_handler.get_password_hash(user.password)
    u = User(
        username=user.username,
        password=hashed_pwd,
        email=user.email,
        role_id=user.role_id.value if user.role_id else 2,
    )
    logger.info(f"User: {u}")
    session.add(u)
    await session.commit()
    return {"message": "User created successfully", "success": True}


@auth_router.post(
    "/login",
    response_model=UserLoginResponse,
    description="Login user",
    deprecated=True,
)
async def login(user: UserLogin):
    """
    Logs in a user.

    Args:
        user (UserLogin): The user login credentials.

    Returns:
        dict: A dictionary containing the authentication token, success status, and a message.
    """
    # user_found = find_user(user.username)
    user_found = await find_user(user.username)
    if not user_found:
        raise HTTPException(status_code=401, detail="Invalid username and/or password")
    verified = auth_handler.verify_password(user.password, user_found.password)
    if not verified:
        raise HTTPException(status_code=401, detail="Invalid username and/or password")
    token = auth_handler.encode_token(user_found.username)
    return {"token": token, "success": True, "message": "Login successful"}


# Get all users
@auth_router.get(
    "/users",
    response_model=UserBaseResponse,
    description="Get all users",
    dependencies=[Security(AuthHandler().require_any_scope("analyst", "admin"))],
)
async def get_users(session: AsyncSession = Depends(get_db)):
    """
    Retrieve all users from the database.

    Parameters:
    - session: AsyncSession - The database session.

    Returns:
    - UserBaseResponse: The response containing the retrieved users.

    Raises:
    - None

    """
    users = await select_all_users()
    return UserBaseResponse(
        users=users,
        message="Users retrieved successfully",
        success=True,
    )


# ! TODO: HAVE LOGIC TO HANDLE PASSWORD RESET VIA A TOKEN BUT NOT IMPLEMENTED YET ! #
@auth_router.post(
    "/reset-token",
    status_code=200,
    description="Request password reset",
    include_in_schema=False,
)
async def request_password_reset(
    password_reset_request: PasswordResetToken,
    session: AsyncSession = Depends(get_db),
):
    """
    Request a password reset.

    Args:
        password_reset_request (PasswordResetRequest): The password reset request data.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        dict: A dictionary containing the reset token.
    """
    user = await find_user(password_reset_request.username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    reset_token = auth_handler.generate_reset_token(user.username)
    return {"reset_token": reset_token}


# ! TODO: HAVE LOGIC TO HANDLE PASSWORD RESET VIA A TOKEN BUT NOT IMPLEMENTED YET ! #
# @auth_router.post("/reset-password", status_code=200, description="Reset user's password", include_in_schema=False)
# async def reset_password(password_reset: PasswordReset, session: AsyncSession = Depends(get_db)):
#     """
#     Reset a user's password.

#     Args:
#         password_reset (PasswordReset): The password reset data.
#         session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

#     Returns:
#         dict: A dictionary containing the message and success status.
#     """
#     user = await find_user(password_reset.username)
#     if not user or not auth_handler.verify_reset_token(password_reset.reset_token, user.username):
#         raise HTTPException(status_code=404, detail="Invalid username or reset token")
#     hashed_pwd = auth_handler.get_password_hash(password_reset.new_password)
#     user.password = hashed_pwd
#     session.add(user)
#     await session.commit()
#     return {"message": "Password reset successfully", "success": True}


# Reset a user's password via the username, must be an admin
@auth_router.post(
    "/reset-password",
    status_code=200,
    description="Reset user's password via username",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def reset_password_via_username(
    request: PasswordReset,
    session: AsyncSession = Depends(get_db),
):
    """
    Reset a user's password via the username. Must be an admin.

    Args:
        request (PasswordReset): The password reset data.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        dict: A dictionary containing the message and success status.
    """
    user = await find_user(request.username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    hashed_pwd = auth_handler.get_password_hash(request.new_password)
    user.password = hashed_pwd
    session.add(user)
    await session.commit()
    return {"message": "Password reset successfully", "success": True}


# Reset a users password for themselves. The user must be logged in and the token decoded to get the username
@auth_router.post(
    "/reset-password/me",
    status_code=200,
    description="Reset user's password",
    dependencies=[Security(AuthHandler().require_any_scope("analyst", "admin"))],
)
async def reset_password_me(
    request: PasswordReset,
    token: str = Depends(AuthHandler().security),
    session: AsyncSession = Depends(get_db),
):
    """
    Reset a user's password.

    Args:
        request (PasswordReset): The password reset data.
        token (str, optional): The authentication token. Defaults to Depends(AuthHandler().security).
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        dict: A dictionary containing the message and success status.
    """
    user = await find_user(request.username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await auth_handler.verify_reset_token_me(token, user)
    hashed_pwd = auth_handler.get_password_hash(request.new_password)
    user.password = hashed_pwd
    session.add(user)
    await session.commit()
    return {"message": "Password reset successfully", "success": True}
