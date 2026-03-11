import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.producto import Producto
from app.models.user import User
from app.schemas.productos import ProductoCreate, ProductoUpdate, ProductoResponse
from app.dependencies.auth import get_current_user, require_admin

router = APIRouter(prefix="/productos", tags=["productos"])


@router.get("", response_model=list[ProductoResponse])
async def listar_productos(
    categoria_id: Optional[str] = Query(None),
    solo_activos: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Producto)
        .options(selectinload(Producto.categoria))
        .where(Producto.store_id == current_user.store_id)
    )
    if solo_activos:
        query = query.where(Producto.activo == True)
    if categoria_id:
        query = query.where(Producto.categoria_id == categoria_id)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=ProductoResponse, status_code=201)
async def crear_producto(
    body: ProductoCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    producto = Producto(
        id=str(uuid.uuid4()),
        store_id=current_user.store_id,
        **body.model_dump(),
    )
    db.add(producto)
    await db.commit()

    result = await db.execute(
        select(Producto)
        .options(selectinload(Producto.categoria))
        .where(Producto.id == producto.id)
    )
    return result.scalar_one()


@router.get("/{producto_id}", response_model=ProductoResponse)
async def obtener_producto(
    producto_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Producto)
        .options(selectinload(Producto.categoria))
        .where(Producto.id == producto_id, Producto.store_id == current_user.store_id)
    )
    producto = result.scalar_one_or_none()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@router.put("/{producto_id}", response_model=ProductoResponse)
async def actualizar_producto(
    producto_id: str,
    body: ProductoUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Producto).where(
            Producto.id == producto_id,
            Producto.store_id == current_user.store_id,
        )
    )
    producto = result.scalar_one_or_none()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(producto, field, value)

    await db.commit()

    result = await db.execute(
        select(Producto)
        .options(selectinload(Producto.categoria))
        .where(Producto.id == producto_id)
    )
    return result.scalar_one()


@router.delete("/{producto_id}", status_code=204)
async def eliminar_producto(
    producto_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Producto).where(
            Producto.id == producto_id,
            Producto.store_id == current_user.store_id,
        )
    )
    producto = result.scalar_one_or_none()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    await db.delete(producto)
    await db.commit()
