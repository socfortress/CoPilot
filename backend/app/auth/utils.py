from datetime import datetime
from datetime import timedelta

import jwt
from fastapi import Depends
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import SecurityScopes
from loguru import logger
from passlib.context import CryptContext

from app.auth.services.universal import find_user
from app.auth.services.universal import get_role


class AuthHandler:
    security = OAuth2PasswordBearer(
        tokenUrl="auth/token",
        scopes={"admin": "Admin users", "analyst": "SOC Analysts"},
    )
    pwd_context = CryptContext(schemes=["bcrypt"])
    secret = "bL4unrkoxtFs1MT6A7Ns2yMLkduyuqrkTxDV9CjlbNc="

    def get_password_hash(self, password):
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password, hashed_password):
        return self.pwd_context.verify(plain_password, hashed_password)

    # ! Old without Async
    # def authenticate_user(self, username: str, password: str):
    #     user = find_user(username)
    #     if not user or not self.verify_password(password, user.password):
    #         return False
    #     return user

    # ! New with Async
    async def authenticate_user(self, username: str, password: str):
        user = await find_user(username)
        if not user or not self.verify_password(password, user.password):
            logger.info(f"Password is not verified")
            return False
        return user

    # ! Old without Async
    # def encode_token(self, username: str, access_token_expires: timedelta = timedelta(minutes=60)):
    #     payload = {
    #         "exp": datetime.utcnow() + access_token_expires,
    #         "iat": datetime.utcnow(),
    #         "sub": username,
    #         "scopes": [get_role(username)],
    #     }
    #     return jwt.encode(payload, self.secret, algorithm="HS256")

    # ! New with Async
    async def encode_token(self, username: str, access_token_expires: timedelta = timedelta(minutes=60)):
        role = await get_role(username)
        payload = {
            "exp": datetime.utcnow() + access_token_expires,
            "iat": datetime.utcnow(),
            "sub": username,
            "scopes": [role],
        }
        return jwt.encode(payload, self.secret, algorithm="HS256")

    def decode_token(self, token):
        try:
            payload = jwt.decode(token, self.secret, algorithms=["HS256"])
            return payload["sub"], payload.get("scopes", [])
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Expired signature")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

    async def get_current_user(self, security_scopes: SecurityScopes, token: str = Depends(security)):
        if security_scopes.scopes:
            authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
        else:
            authenticate_value = "Bearer"

        credentials_exception = HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": authenticate_value},
        )

        try:
            username, token_scopes = self.decode_token(token)
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail=f"Could not decode token: {e}",
                headers={"WWW-Authenticate": authenticate_value},
            )

        if username is None:
            raise HTTPException(
                status_code=401,
                detail="Username not found in token",
                headers={"WWW-Authenticate": authenticate_value},
            )
        user = await find_user(username)

        if user is None:
            raise HTTPException(
                status_code=401,
                detail="User not found",
                headers={"WWW-Authenticate": authenticate_value},
            )

        for scope in security_scopes.scopes:
            if scope not in token_scopes:
                raise HTTPException(
                    status_code=401,
                    detail="Not enough permissions",
                    headers={"WWW-Authenticate": authenticate_value},
                )

        return user

    def return_username_for_logging(self, token: str = Depends(security)):
        username, token_scopes = self.decode_token(token)
        return username

    def require_any_scope(self, *required_scopes: str):
        async def _require_any_scope(token: str = Depends(self.security)):
            if not token:
                raise HTTPException(
                    status_code=401,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            username, token_scopes = self.decode_token(token)

            if not any(scope in token_scopes for scope in required_scopes):
                raise HTTPException(
                    status_code=401,
                    detail="Not enough permissions, you don't have any of the required scopes.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return username

        return _require_any_scope
