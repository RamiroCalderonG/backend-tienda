from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sqlfunc
from typing import List, Optional
from datetime import date, timedelta
import uuid

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.producto import Producto
from app.models.inventario import MovimientoInventario
from app.schemas.inventario import RestockRequest, AjusteRequest, MovimientoResponse, LoteVencimiento, ValorStockResponse

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

    costo = body.costo_unitario if body.costo_unitario is not None else float(producto.costo)

    stock_antes = producto.stock
    producto.stock = stock_antes + body.cantidad

    if body.actualizar_costo and body.costo_unitario is not None:
        producto.costo = body.costo_unitario

    movimiento = MovimientoInventario(
        id=str(uuid.uuid4()),
        store_id=current_user.store_id,
        producto_id=producto.id,
        nombre_producto=producto.nombre,
        cantidad=body.cantidad,
        stock_antes=stock_antes,
        stock_despues=producto.stock,
        costo_unitario=costo,
        tipo="restock",
        fecha_caducidad=body.fecha_caducidad,
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


@router.get("/vencimientos", response_model=List[LoteVencimiento])
async def listar_vencimientos(
    dias: int = Query(default=3, ge=1, le=30, description="Alertar lotes que vencen en los próximos N días"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    hoy = date.today()
    limite = hoy + timedelta(days=dias)

    result = await db.execute(
        select(MovimientoInventario)
        .where(
            MovimientoInventario.store_id == current_user.store_id,
            MovimientoInventario.tipo == "restock",
            MovimientoInventario.fecha_caducidad.isnot(None),
            MovimientoInventario.fecha_caducidad <= str(limite),
            MovimientoInventario.fecha_caducidad >= str(hoy),
        )
        .order_by(MovimientoInventario.fecha_caducidad)
    )
    movimientos = result.scalars().all()

    return [
        LoteVencimiento(
            movimiento_id=m.id,
            producto_id=m.producto_id,
            nombre_producto=m.nombre_producto,
            cantidad=m.cantidad,
            fecha_caducidad=m.fecha_caducidad,
            dias_restantes=(date.fromisoformat(m.fecha_caducidad) - hoy).days,
        )
        for m in movimientos
    ]


@router.get("/valor-stock", response_model=ValorStockResponse)
async def valor_stock(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Calcula el valor real invertido en el stock actual usando costo ponderado histórico
    en lugar del costo actual del producto (que puede haberse actualizado).
    """
    productos_result = await db.execute(
        select(Producto).where(
            Producto.store_id == current_user.store_id,
            Producto.activo == True,
            Producto.stock > 0,
        )
    )
    productos = productos_result.scalars().all()

    total_invertido = 0.0
    total_valor_venta = 0.0

    for p in productos:
        # Costo ponderado: suma(cantidad × costo_unitario) / suma(cantidad) de todos los restocks
        mov_result = await db.execute(
            select(
                sqlfunc.sum(MovimientoInventario.cantidad * MovimientoInventario.costo_unitario),
                sqlfunc.sum(MovimientoInventario.cantidad),
            ).where(
                MovimientoInventario.producto_id == p.id,
                MovimientoInventario.tipo == "restock",
                MovimientoInventario.costo_unitario.isnot(None),
            )
        )
        row = mov_result.one()
        total_gastado, total_unidades = row

        if total_gastado and total_unidades:
            costo_ponderado = float(total_gastado) / float(total_unidades)
        else:
            costo_ponderado = float(p.costo)

        total_invertido += costo_ponderado * p.stock
        total_valor_venta += float(p.precio) * p.stock

    return ValorStockResponse(
        total_invertido=round(total_invertido, 2),
        total_valor_venta=round(total_valor_venta, 2),
    )


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
