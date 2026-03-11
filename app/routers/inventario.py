from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import uuid

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.producto import Producto
from app.models.inventario import MovimientoInventario
from app.schemas.inventario import RestockRequest, AjusteRequest, MovimientoResponse

router = APIRouter(prefix="/inventario", tags=["inventario"])


@router.post("/restock", response_model=MovimientoResponse, status_code=201)
async def restock(
    body: RestockRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Producto).where(
            Producto.id == body.producto_id,
            Producto.store_id == current_user.store_id,
        )
    )
    producto = result.scalar_one_or_none()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    stock_antes = producto.stock
    producto.stock = stock_antes + body.cantidad

    movimiento = MovimientoInventario(
        id=str(uuid.uuid4()),
        store_id=current_user.store_id,
        producto_id=producto.id,
        nombre_producto=producto.nombre,
        cantidad=body.cantidad,
        stock_antes=stock_antes,
        stock_despues=producto.stock,
        tipo="restock",
        notas=body.notas,
        user_id=current_user.id,
        user_name=current_user.name,
    )
    db.add(movimiento)
    await db.commit()
    await db.refresh(movimiento)
    return movimiento


@router.post("/ajuste", response_model=MovimientoResponse, status_code=201)
async def ajuste(
    body: AjusteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Producto).where(
            Producto.id == body.producto_id,
            Producto.store_id == current_user.store_id,
        )
    )
    producto = result.scalar_one_or_none()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if producto.stock < body.cantidad:
        raise HTTPException(status_code=400, detail="Stock insuficiente para el ajuste")

    stock_antes = producto.stock
    producto.stock = stock_antes - body.cantidad

    movimiento = MovimientoInventario(
        id=str(uuid.uuid4()),
        store_id=current_user.store_id,
        producto_id=producto.id,
        nombre_producto=producto.nombre,
        cantidad=-body.cantidad,
        stock_antes=stock_antes,
        stock_despues=producto.stock,
        tipo=body.tipo,
        notas=body.notas,
        user_id=current_user.id,
        user_name=current_user.name,
    )
    db.add(movimiento)
    await db.commit()
    await db.refresh(movimiento)
    return movimiento


@router.get("/movimientos", response_model=List[MovimientoResponse])
async def listar_movimientos(
    producto_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(MovimientoInventario)
        .where(MovimientoInventario.store_id == current_user.store_id)
        .order_by(MovimientoInventario.created_at.desc())
        .limit(limit)
    )
    if producto_id:
        query = query.where(MovimientoInventario.producto_id == producto_id)

    result = await db.execute(query)
    return result.scalars().all()
