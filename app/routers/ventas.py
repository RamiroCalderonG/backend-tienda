import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.venta import Venta, VentaItem
from app.models.producto import Producto
from app.models.promocion import Promocion
from app.models.user import User
from app.schemas.ventas import VentaCreate, VentaResponse
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/ventas", tags=["ventas"])


@router.post("", response_model=VentaResponse, status_code=201)
async def crear_venta(
    body: VentaCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not body.items:
        raise HTTPException(status_code=400, detail="La venta debe tener al menos un producto")

    total = 0.0
    items_data = []

    # Validar productos y calcular total
    for item in body.items:
        result = await db.execute(
            select(Producto).where(
                Producto.id == item.producto_id,
                Producto.store_id == current_user.store_id,
                Producto.activo == True,
            )
        )
        producto = result.scalar_one_or_none()
        if not producto:
            raise HTTPException(status_code=404, detail=f"Producto {item.producto_id} no encontrado")
        if producto.stock < item.cantidad:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente para '{producto.nombre}' (disponible: {producto.stock})",
            )

        # Aplicar promoción si corresponde
        # precio_promocion = precio TOTAL del bundle (ej. "3 por $50")
        promo_result = await db.execute(
            select(Promocion).where(Promocion.producto_id == producto.id)
        )
        promocion = promo_result.scalar_one_or_none()
        if promocion and item.cantidad >= promocion.cantidad_requerida:
            grupos = item.cantidad // promocion.cantidad_requerida
            resto  = item.cantidad %  promocion.cantidad_requerida
            subtotal = grupos * float(promocion.precio_promocion) + resto * float(producto.precio)
        else:
            subtotal = float(producto.precio) * item.cantidad

        precio_efectivo = subtotal / item.cantidad
        total += subtotal
        items_data.append((producto, item.cantidad, subtotal, precio_efectivo))

    # Crear venta
    venta = Venta(
        id=str(uuid.uuid4()),
        store_id=current_user.store_id,
        user_id=current_user.id,
        total=total,
        metodo_pago=body.metodo_pago,
    )
    db.add(venta)

    # Crear items y descontar stock
    for producto, cantidad, subtotal, precio_efectivo in items_data:
        db.add(VentaItem(
            id=str(uuid.uuid4()),
            venta_id=venta.id,
            producto_id=producto.id,
            nombre=producto.nombre,
            precio=precio_efectivo,
            costo_unitario=float(producto.costo),
            cantidad=cantidad,
            subtotal=subtotal,
        ))
        producto.stock -= cantidad

    await db.commit()

    result = await db.execute(
        select(Venta)
        .options(selectinload(Venta.items))
        .where(Venta.id == venta.id)
    )
    return result.scalar_one()


@router.get("", response_model=list[VentaResponse])
async def listar_ventas(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Venta)
        .options(selectinload(Venta.items))
        .where(Venta.store_id == current_user.store_id)
        .order_by(Venta.created_at.desc())
    )
    return result.scalars().all()
