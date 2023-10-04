from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from fastapi import security
from fastapi.security import HTTPAuthorizationCredentials

from app.auth.models.users import User
from app.auth.models.users import UserInput
from app.auth.models.users import UserLogin
from app.auth.schema.auth import UserLoginResponse
from app.auth.schema.auth import UserResponse
from app.auth.services.universal import find_user
from app.auth.services.universal import select_all_users
from app.auth.utils import AuthHandler
from app.db.db_session import session

user_router = APIRouter()
auth_handler = AuthHandler()


@user_router.post("/register", response_model=UserResponse, status_code=201, description="Register new user")
def register(user: UserInput):
    users = select_all_users()
    if any(x.username == user.username for x in users):
        raise HTTPException(status_code=400, detail="Username is taken")
    hashed_pwd = auth_handler.get_password_hash(user.password)
    u = User(username=user.username, password=hashed_pwd, email=user.email, is_admin=user.is_admin)
    session.add(u)
    session.commit()
    return {"message": "User created successfully", "success": True}


@user_router.post("/login", response_model=UserLoginResponse, description="Login user")
def login(user: UserLogin):
    user_found = find_user(user.username)
    if not user_found:
        raise HTTPException(status_code=401, detail="Invalid username and/or password")
    verified = auth_handler.verify_password(user.password, user_found.password)
    if not verified:
        raise HTTPException(status_code=401, detail="Invalid username and/or password")
    token = auth_handler.encode_token(user_found.username)
    return {"token": token, "success": True, "message": "Login successful"}


@user_router.get("/users/me", description="Get current user")
def get_current_user(user: User = Depends(auth_handler.get_current_user)):
    return user
