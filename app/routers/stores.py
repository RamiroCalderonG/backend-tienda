import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List

from pydantic import BaseModel, EmailStr

from app.database import get_db
from app.dependencies.auth import get_current_user, require_superadmin
from app.models.user import User, UserRole
from app.models.store import Store
from app.schemas.auth import StoreResponse
from app.routers.auth import pwd_context

router = APIRouter(prefix="/stores", tags=["stores"])


# ── Schemas ────────────────────────────────────────────────────

class StoreListItem(BaseModel):
    id: str
    name: str
    address: Optional[str]
    user_count: int
    created_at: str

    model_config = {"from_attributes": True}


class CreateStoreRequest(BaseModel):
    store_name: str
    store_address: Optional[str] = None
    admin_name: str
    admin_email: EmailStr
    admin_password: str


# ── Superadmin endpoints ───────────────────────────────────────

@router.get("", response_model=List[StoreListItem])
async def listar_tiendas(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    result = await db.execute(select(Store).order_by(Store.created_at.desc()))
    stores = result.scalars().all()

    items = []
    for store in stores:
        count_result = await db.execute(
            select(func.count(User.id)).where(User.store_id == store.id)
        )
        user_count = count_result.scalar() or 0
        items.append(StoreListItem(
            id=store.id,
            name=store.name,
            address=store.address,
            user_count=user_count,
            created_at=store.created_at.isoformat() if store.created_at else "",
        ))
    return items


@router.post("", response_model=StoreListItem, status_code=201)
async def crear_tienda(
    body: CreateStoreRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    existing = await db.execute(select(User).where(User.email == body.admin_email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    store = Store(
        id=str(uuid.uuid4()),
        name=body.store_name,
        address=body.store_address,
        config={},
    )
    db.add(store)

    admin = User(
        id=str(uuid.uuid4()),
        store_id=store.id,
        name=body.admin_name,
        email=body.admin_email,
        hashed_password=pwd_context.hash(body.admin_password),
        role=UserRole.admin,
        is_active=True,
    )
    db.add(admin)
    await db.commit()
    await db.refresh(store)

    return StoreListItem(
        id=store.id,
        name=store.name,
        address=store.address,
        user_count=1,
        created_at=store.created_at.isoformat() if store.created_at else "",
    )


@router.delete("/{store_id}", status_code=204)
async def eliminar_tienda(
    store_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superadmin),
):
    # No puede eliminar la tienda del propio superadmin
    if store_id == current_user.store_id:
        raise HTTPException(status_code=400, detail="No puedes eliminar la tienda del sistema")

    result = await db.execute(select(Store).where(Store.id == store_id))
    store = result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=404, detail="Tienda no encontrada")

    await db.delete(store)
    await db.commit()


class ConfigRequest(BaseModel):
    color_primario: Optional[str] = None   # hex sin '#', ej: "3F51B5"
    color_fondo: Optional[str] = None      # hex sin '#'
    fuente: Optional[str] = None           # Poppins | Inter | Montserrat | ...
    moneda: Optional[str] = None           # $, €, Q, etc.
    nombre_ticket: Optional[str] = None    # nombre en el ticket de venta


@router.put("/config", response_model=StoreResponse)
async def update_config(
    body: ConfigRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden cambiar la configuración")

    result = await db.execute(select(Store).where(Store.id == current_user.store_id))
    store = result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=404, detail="Tienda no encontrada")

    # Merge: conserva claves existentes y solo sobreescribe las enviadas
    existing = dict(store.config or {})
    for key, value in body.model_dump(exclude_none=True).items():
        existing[key] = value
    store.config = existing

    await db.commit()
    await db.refresh(store)
    return StoreResponse.model_validate(store)
