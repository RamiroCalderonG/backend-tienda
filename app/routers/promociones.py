from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.promocion import Promocion
from app.models.producto import Producto
from app.models.user import User
from app.schemas.promociones import PromocionCreate, PromocionResponse
from app.dependencies.auth import get_current_user, require_admin

router = APIRouter(prefix="/promociones", tags=["promociones"])


@router.get("", response_model=list[PromocionResponse])
async def listar_promociones(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Promocion)
        .join(Producto, Promocion.producto_id == Producto.id)
        .where(Producto.store_id == current_user.store_id)
    )
    return result.scalars().all()


@router.post("", response_model=PromocionResponse, status_code=201)
async def crear_promocion(
    body: PromocionCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # Verificar que el producto pertenece a la tienda
    result = await db.execute(
        select(Producto).where(
            Producto.id == body.producto_id,
            Producto.store_id == current_user.store_id,
        )
    )
    producto = result.scalar_one_or_none()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    # Verificar que no exista ya una promoción para ese producto
    result = await db.execute(
        select(Promocion).where(Promocion.producto_id == body.producto_id)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="El producto ya tiene una promoción activa")

    promocion = Promocion(**body.model_dump())
    db.add(promocion)
    await db.commit()
    await db.refresh(promocion)
    return promocion


@router.delete("/{promocion_id}", status_code=204)
async def eliminar_promocion(
    promocion_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Promocion)
        .join(Producto, Promocion.producto_id == Producto.id)
        .where(Promocion.id == promocion_id, Producto.store_id == current_user.store_id)
    )
    promocion = result.scalar_one_or_none()
    if not promocion:
        raise HTTPException(status_code=404, detail="Promoción no encontrada")
    await db.delete(promocion)
    await db.commit()
