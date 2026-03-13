from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from pydantic import BaseModel

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User, UserRole
from app.models.store import Store
from app.schemas.auth import StoreResponse

router = APIRouter(prefix="/stores", tags=["stores"])


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
