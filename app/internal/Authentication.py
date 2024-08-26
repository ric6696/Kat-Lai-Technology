# Authentication & Security
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import (
    OAuth2PasswordBearer,
    SecurityScopes,
    OAuth2PasswordRequestForm,
)
import jwt
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext

# Database & Data Validation
from ..database import UserDataManager, get_user_db
from ..models.Authentication import Token, TokenData, User, UserInDB
from pydantic import ValidationError

# Credentials
from .credentials import User_Auth_Credentials

# Utilities
from datetime import datetime, timedelta, timezone
from typing import Annotated


class __Auth_Config:
    SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES = User_Auth_Credentials()


# "Admin" is a special scope that grants all permissions
__Scopes: dict[str, str] = {
    "Device": "Read device control information",
    "Device-Setup": "Setup and register device serial numbers",
    "Mobile": "Send requests to control device from mobile",
    "Manager": "Gain access to enable/disable user touch etc.",
    "User-Manager": "Access to register/delete users with different scopes",
}

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    scopes=__Scopes,
)

__pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", truncate_error=True)


def _verify_password_hash(plain_password: str, hashed_password: str) -> bool:
    """Verify a hash using bcrypt."""
    return __pwd_context.verify(plain_password, hashed_password)


def _verify_scopes(input_scopes: list[str], user_scopes: str) -> bool:
    return all(scope in user_scopes for scope in input_scopes)


def authenticate_user(
    name: str, input_password: str, input_scopes: list[str], db: UserDataManager
) -> UserInDB:
    """
    Check if user credentials are valid. Gets a username, password and optinal scopes
    str, looks up if user is in the database, and verifies the password and scopes.
    Returns the user if the credentials are valid, raise an HTTP 401 Exception
    if not found.
    """

    user = db.get_user(name, True)

    # TODO@[ZIYA]: Determine if this is the correct way to handle scopes
    # https://github.com/Kat-Lai-Technologies/Kat-Lai-Backend/issues/21

    authenticate_value = f"Bearer scope={input_scopes}" if input_scopes else "Bearer"

    insufficent_permissions_err = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username, password or scopes."
        + "Please use the same scopes as when you registered (if any).",
        headers={"WWW-Authenticate": authenticate_value},
    )

    if (
        user is None
        or not _verify_password_hash(input_password, user.hashed_password)
        or not _verify_scopes(input_scopes, user.scopes)
    ):
        raise insufficent_permissions_err

    return user


def register_user_with_unhashed_password(
    user_data: dict, user_db: Annotated[UserDataManager, Depends(get_user_db)]
) -> None:
    """
    Register a user in the database.

    :param user_data: A dictionary containing the user's data.
    The dictionary must contain the following keys:
    - username: The user's username.
    - email: The user's email address.
    - full_name: The user's full name.
    - disabled: A boolean indicating whether the user is disabled.
    - unhashed_password: The user's unhashed password.
    - scopes: A list of strings that contans the desired user scopes, may be empty list.
    -- If the user has the "Admin" scope, creates a user with all scopes.
    """
    password_hash = _get_password_hash(user_data["unhashed_password"])
    del user_data["unhashed_password"]

    try:
        validated_scopes = validate_scopes(user_data["scopes"])
        del user_data["scopes"]
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bad Request: Invalid Scopes",
        ) from err

    if not (user_db.register_user(user_data, password_hash, validated_scopes)):
        raise RuntimeError("Failed to register user in database!")


def _get_password_hash(plain_password: str) -> str:
    """Hash a string using bcrypt."""
    return __pwd_context.hash(plain_password)


def validate_scopes(input_scopes: list[str]) -> str:
    """Verify is provided scopes are valid. Raise a ValueError if not."""
    if "Admin" in input_scopes:
        return " ".join(__Scopes.keys())

    for scope in input_scopes:
        if scope not in __Scopes:
            raise ValueError(f"Invalid Scope: {scope}")
    return " ".join(input_scopes)


def _create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Takes data to encode into a JWT token and an optional expiration time.
    Returns the encoded JWT token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, __Auth_Config.SECRET_KEY, algorithm=__Auth_Config.ALGORITHM
    )
    return encoded_jwt


def get_access_token(
    form_data: OAuth2PasswordRequestForm, user_db: UserDataManager
) -> Token:
    user = authenticate_user(
        form_data.username, form_data.password, form_data.scopes, user_db
    )

    access_token_expires = timedelta(
        minutes=int(__Auth_Config.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    access_token = _create_access_token(
        data={"sub": user.username, "scopes": form_data.scopes},
        expires_delta=access_token_expires,
    )

    return Token(access_token=access_token, token_type="bearer")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    security_scopes: SecurityScopes,
    db: Annotated[UserDataManager, Depends(get_user_db)],
) -> User:
    """
    Validate a user's token and return the user if the token is valid.
    """
    # Determine Authentication Type (Scoped or Not)
    if security_scopes.scopes:
        authenticate_value = f"Bearer scope={security_scopes.scope_str}"
    else:
        authenticate_value = "Bearer"

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )

    try:
        assert __Auth_Config.SECRET_KEY is not None, "Secret Key not set!"
        payload = jwt.decode(
            token, __Auth_Config.SECRET_KEY, algorithms=[__Auth_Config.ALGORITHM]
        )

        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        token_scopes = payload.get("scopes", [])
        token_data = TokenData(username=username, scopes=token_scopes)
    except (InvalidTokenError, ValidationError, AssertionError) as err:
        raise credentials_exception from err

    user = db.get_user(token_data.username, False)
    if user is None:
        raise credentials_exception

    # Authenticate Scoped Permissions
    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value},
            )

    # Return Authenticated User
    try:
        return User(**user.model_dump())
    except ValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid user data received from db in get_current_user(...)",
            headers={"WWW-Authenticate": authenticate_value},
        ) from err


async def get_current_active_user(
    current_user: Annotated[User, Security(get_current_user)],
) -> User:
    """
    Validate that a user is active.
    """
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
