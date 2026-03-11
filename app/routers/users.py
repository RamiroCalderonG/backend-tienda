from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
import uuid

from app.database import get_db
from app.dependencies.auth import require_admin
from app.models.user import User, UserRole
from app.schemas.users import UserCreate, UserUpdate, UserResponse
from app.routers.auth import pwd_context

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=List[UserResponse])
async def listar_usuarios(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(User)
        .where(User.store_id == current_user.store_id)
        .order_by(User.created_at)
    )
    return result.scalars().all()


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def crear_usuario(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if body.role not in ("admin", "cashier"):
        raise HTTPException(status_code=400, detail="Rol inválido. Usa 'admin' o 'cashier'")

    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    user = User(
        id=str(uuid.uuid4()),
        store_id=current_user.store_id,
        name=body.name,
        email=body.email,
        hashed_password=pwd_context.hash(body.password),
        role=UserRole(body.role),
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def actualizar_usuario(
    user_id: str,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(User).where(User.id == user_id, User.store_id == current_user.store_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # No puedes cambiar tu propio rol ni desactivarte a ti mismo
    if user_id == current_user.id:
        if body.role is not None and body.role != current_user.role:
            raise HTTPException(status_code=400, detail="No puedes cambiar tu propio rol")
        if body.is_active is False:
            raise HTTPException(status_code=400, detail="No puedes desactivarte a ti mismo")

    # Validar que no quede la tienda sin admin
    if body.role == "cashier" and user.role == UserRole.admin:
        admins = await db.execute(
            select(func.count(User.id)).where(
                User.store_id == current_user.store_id,
                User.role == UserRole.admin,
                User.is_active == True,
            )
        )
        if admins.scalar() <= 1:
            raise HTTPException(status_code=400, detail="No puede quedar la tienda sin administradores")

    if body.name is not None:
        user.name = body.name
    if body.email is not None:
        existing = await db.execute(
            select(User).where(User.email == body.email, User.id != user_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="El email ya está en uso")
        user.email = body.email
    if body.password is not None:
        user.hashed_password = pwd_context.hash(body.password)
    if body.role is not None:
        user.role = UserRole(body.role)
    if body.is_active is not None:
        user.is_active = body.is_active

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_usuario(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo")

    result = await db.execute(
        select(User).where(User.id == user_id, User.store_id == current_user.store_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # No puede quedar la tienda sin admin
    if user.role == UserRole.admin:
        admins = await db.execute(
            select(func.count(User.id)).where(
                User.store_id == current_user.store_id,
                User.role == UserRole.admin,
                User.is_active == True,
            )
        )
        if admins.scalar() <= 1:
            raise HTTPException(status_code=400, detail="No puede quedar la tienda sin administradores")

    await db.delete(user)
    await db.commit()
