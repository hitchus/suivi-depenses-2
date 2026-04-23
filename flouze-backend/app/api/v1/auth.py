from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.limiter import limiter
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

_REFRESH_COOKIE = "refresh_token"
_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, token: str, expire_days: int) -> None:
    response.set_cookie(
        _REFRESH_COOKIE,
        token,
        httponly=True,
        secure=False,   # set True in production (TLS)
        samesite="lax",
        max_age=expire_days * 86_400,
        path=_COOKIE_PATH,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await auth_service.create_user(
            db, body.email, body.password, body.display_name, body.currency
        )
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Cet email est déjà utilisé")

    access_token, refresh_token = await auth_service.issue_tokens(user)
    _set_refresh_cookie(response, refresh_token, 30)
    return TokenResponse(access_token=access_token)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,  # required by slowapi
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    user = await auth_service.authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

    access_token, refresh_token = await auth_service.issue_tokens(user)
    _set_refresh_cookie(response, refresh_token, 30)
    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token manquant")

    result = await auth_service.rotate_refresh_token(refresh_token)
    if not result:
        raise HTTPException(status_code=401, detail="Refresh token invalide ou expiré")

    new_access, new_refresh = result
    _set_refresh_cookie(response, new_refresh, 30)
    return TokenResponse(access_token=new_access)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
):
    if refresh_token:
        await auth_service.revoke_refresh_token(refresh_token)
    response.delete_cookie(_REFRESH_COOKIE, path=_COOKIE_PATH)
