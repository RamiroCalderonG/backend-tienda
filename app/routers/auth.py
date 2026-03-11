import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.config import settings
from app.models.store import Store
from app.models.user import User, UserRole
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
    StoreResponse,
    TokenResponse,
    UserResponse,
)
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    store = Store(
        id=str(uuid.uuid4()),
        name=body.store_name,
        address=body.store_address,
        config={},
    )
    db.add(store)

    user = User(
        id=str(uuid.uuid4()),
        store_id=store.id,
        name=body.name,
        email=body.email,
        hashed_password=pwd_context.hash(body.password),
        role=UserRole.admin,
    )
    db.add(user)
    await db.commit()

    access_token = create_token(
        {"sub": user.id, "store_id": store.id, "role": user.role},
        timedelta(minutes=settings.access_token_expire_minutes),
    )
    refresh_token = create_token(
        {"sub": user.id, "type": "refresh"},
        timedelta(days=settings.refresh_token_expire_days),
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not pwd_context.verify(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Cuenta desactivada")

    access_token = create_token(
        {"sub": user.id, "store_id": user.store_id, "role": user.role},
        timedelta(minutes=settings.access_token_expire_minutes),
    )
    refresh_token = create_token(
        {"sub": user.id, "type": "refresh"},
        timedelta(days=settings.refresh_token_expire_days),
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(body.refresh_token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Token inválido")
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    access_token = create_token(
        {"sub": user.id, "store_id": user.store_id, "role": user.role},
        timedelta(minutes=settings.access_token_expire_minutes),
    )
    refresh_token = create_token(
        {"sub": user.id, "type": "refresh"},
        timedelta(days=settings.refresh_token_expire_days),
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=MeResponse)
async def me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Store).where(Store.id == current_user.store_id))
    store = result.scalar_one()
    return MeResponse(
        user=UserResponse.model_validate(current_user),
        store=StoreResponse.model_validate(store),
    )
