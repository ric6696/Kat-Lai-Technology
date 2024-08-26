# Fast API
from fastapi import Depends, FastAPI, Form, HTTPException, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm

# Utilities
from typing import Annotated
from .internal.Debug.utils import print_warn

# Authentication
from .database import UserDataManager, get_user_db
from .models.Authentication import Token, User
from .internal.Authentication import (
    get_access_token,
    get_current_active_user,
    register_user_with_unhashed_password,
)

# Routers
from .routers import device_setup
from .routers import device, health, manager, mobile
from .sleepAPI.real_time import iSuke_creds_valid


app = FastAPI(
    title="Elysium Aroma API",
    summary="API for to manage AromaPod's and Aid in Sleep Studies",
    version="0.1.5",
    redoc_url=None,
)


app.include_router(mobile.router)
app.include_router(device.router)
app.include_router(manager.router)
if iSuke_creds_valid:
    app.include_router(health.router)
else:
    print_warn("iSuke Credentials are invalid! Health API Disabled!")
app.include_router(device_setup.router)


# Enable Cross Origin Resource Sharing (CORS)
origin = [
    # TODO: Modify to public AWS url here! (Edit to make private later!)
    "http://localhost:3000",
    "http://89.116.231.26",
    "*",
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origin,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/token", tags=["Authentication"], response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_db: Annotated[UserDataManager, Depends(get_user_db)],
) -> Token:
    return get_access_token(form_data, user_db)


# All Endpoints
@app.get("/users/me/", tags=["Authentication"], response_model=User)
async def read_users_me(
    current_user: Annotated[User, Security(get_current_active_user)],
):
    return current_user


# TODO: Enable email indexing and validation
@app.put(
    "/users/register",
    tags=["Authentication"],
    response_model=User,
    # dependencies=[Security(get_current_active_user, scopes=["User-Manager"])],
)
async def register_user(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_db: Annotated[UserDataManager, Depends(get_user_db)],
    email: Annotated[str | None, Form()] = None,
    full_name: Annotated[str | None, Form()] = None,
) -> User:
    user = user_db.get_user(form_data.username, True)
    if user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken!"
        )

    register_user_with_unhashed_password(
        {
            "username": form_data.username,
            "email": email,
            "full_name": full_name,
            "unhashed_password": form_data.password,
            "scopes": form_data.scopes,
            "disabled": False,
        },
        user_db,
    )

    return User(
        username=form_data.username,
        email=email,
        full_name=full_name,
        disabled=False,
    )


@app.delete("/users/delete", tags=["Authentication"], response_model=User)
def delete_user(
    user_db: Annotated[UserDataManager, Depends(get_user_db)],
    current_user: Annotated[
        User, Security(get_current_active_user, scopes=["User-Manager"])
    ],
    username: str | None = None,
) -> User | None:
    # [TODO@Ziya]: Verify Password

    if username is None:
        username = current_user.username

    if user_db.delete_user(username):
        raise HTTPException(
            status_code=status.HTTP_200_OK, detail="User deleted successfully!"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user!",
        )
