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
        tokenUrl="api/auth/token",
        scopes={
            "admin": "Admin users",
            "analyst": "SOC Analysts",
            "scheduler": "Scheduler for automated tasks",
        },
    )
    pwd_context = CryptContext(schemes=["bcrypt"])
    secret = "bL4unrkoxtFs1MT6A7Ns2yMLkduyuqrkTxDV9CjlbNc="

    def get_password_hash(self, password):
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password, hashed_password):
        return self.pwd_context.verify(plain_password, hashed_password)

    # ! TODO: HAVE LOGIC TO HANDLE PASSWORD RESET VIA A TOKEN BUT NOT IMPLEMENTED YET ! #
    def generate_reset_token(
        self,
        username: str,
        expires_delta: timedelta = timedelta(minutes=30),
    ):
        """
        Generates a password reset token.

        Args:
            username (str): The username for which the token is being generated.
            expires_delta (timedelta, optional): The expiration time for the token.
                Defaults to 30 minutes.

        Returns:
            str: The generated reset token.
        """
        to_encode = {"exp": datetime.utcnow() + expires_delta, "sub": username}
        encoded_jwt = jwt.encode(to_encode, self.secret, algorithm="HS256")
        return encoded_jwt

    # ! TODO: HAVE LOGIC TO HANDLE PASSWORD RESET VIA A TOKEN BUT NOT IMPLEMENTED YET ! #
    # def verify_reset_token(self, token: str, username: str):
    #     """
    #     Verifies a password reset token.

    #     Args:
    #         token (str): The reset token to verify.
    #         username (str): The username for which the token was generated.

    #     Returns:
    #         bool: True if the token is valid and not expired, False otherwise.
    #     """
    #     try:
    #         payload = jwt.decode(token, self.secret, algorithms=["HS256"])
    #         return payload["sub"] == username
    #     except jwt.ExpiredSignatureError:
    #         return False

    async def verify_reset_token_me(self, token: str, user):
        """
        Verifies a password reset token and checks that the username in the token matches the provided user's username.

        Args:
            token (str): The reset token to verify.
            user: The user for which the token should be verified.

        Returns:
            The username from the token if the token is valid, None otherwise.
        """
        try:
            payload = jwt.decode(token, self.secret, algorithms=["HS256"])
            if payload["sub"] == user.username:
                return payload["sub"]
            else:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token. Username does not match.",
                )
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

    # ! New with Async
    async def authenticate_user(self, username: str, password: str):
        """
        Authenticates a user by checking if the provided username and password match.

        Args:
            username (str): The username of the user.
            password (str): The password of the user.

        Returns:
            Union[User, bool]: The authenticated user object if the username and password match,
                              otherwise False.
        """
        user = await find_user(username)
        try:
            if not user or not self.verify_password(password, user.password):
                logger.info("Password is not verified")
                return False
            return user
        except Exception as e:
            logger.error(f"Error: {e}")
            return False

    # ! New with Async
    async def encode_token(
        self,
        username: str,
        access_token_expires: timedelta = timedelta(hours=24),
    ):
        """
        Encodes a JWT token with the given username and expiration time.

        Args:
            username (str): The username for which the token is being encoded.
            access_token_expires (timedelta, optional): The expiration time for the token.
                Defaults to 24 hours.

        Returns:
            str: The encoded JWT token.
        """
        role = await get_role(username)
        payload = {
            "exp": datetime.utcnow() + access_token_expires,
            "iat": datetime.utcnow(),
            "sub": username,
            "scopes": [role],
        }
        return jwt.encode(payload, self.secret, algorithm="HS256")

    def decode_token(self, token):
        """
        Decode a JWT token and extract the subject and scopes.

        Args:
            token (str): The JWT token to decode.

        Returns:
            tuple: A tuple containing the subject and scopes extracted from the token.

        Raises:
            jwt.ExpiredSignatureError: If the token has expired.
            jwt.InvalidTokenError: If the token is invalid.
        """
        try:
            payload = jwt.decode(token, self.secret, algorithms=["HS256"])
            return payload["sub"], payload.get("scopes", [])
        except jwt.ExpiredSignatureError:
            return "Expired signature", []
        except jwt.InvalidTokenError:
            return "Invalid token", []

    async def get_current_user(
        self,
        security_scopes: SecurityScopes,
        token: str = Depends(security),
    ):
        """
        Retrieves the current user based on the provided security scopes and token.

        Args:
            security_scopes (SecurityScopes): The security scopes required for authentication.
            token (str): The authentication token.

        Raises:
            HTTPException: If the credentials cannot be validated or if the token is expired, invalid, or cannot be decoded.
            HTTPException: If the username is not found in the token.
            HTTPException: If the user is not found.
            HTTPException: If the user does not have enough permissions.

        Returns:
            User: The current user.

        """
        if security_scopes.scopes:
            authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
        else:
            authenticate_value = "Bearer"

        try:
            username, token_scopes = self.decode_token(token)
            if username == "Expired signature":
                raise HTTPException(
                    status_code=401,
                    detail="Expired signature",
                    headers={"WWW-Authenticate": authenticate_value},
                )
            if username == "Invalid token":
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token",
                    headers={"WWW-Authenticate": authenticate_value},
                )
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
        """
        Returns the username extracted from the provided token.

        Parameters:
        - token (str): The token to decode and extract the username from.

        Returns:
        - str: The username extracted from the token.
        """
        username, token_scopes = self.decode_token(token)
        return username

    def require_any_scope(self, *required_scopes: str):
        """
        Decorator that requires any of the specified scopes in the token.

        Args:
            *required_scopes (str): The required scopes.

        Returns:
            Callable: The decorated function that checks if the token has any of the required scopes.
        """

        async def _require_any_scope(token: str = Depends(self.security)):
            if not token:
                raise HTTPException(
                    status_code=401,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            username, token_scopes = self.decode_token(token)

            if username == "Expired signature":
                raise HTTPException(
                    status_code=401,
                    detail="Expired signature",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            if username == "Invalid token":
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if not any(scope in token_scopes for scope in required_scopes):
                raise HTTPException(
                    status_code=401,
                    detail="Not enough permissions, you don't have any of the required scopes.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return username

        return _require_any_scope
