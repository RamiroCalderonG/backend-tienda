from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, cast
from sqlalchemy.types import Date
from sqlalchemy.orm import selectinload
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.venta import Venta, VentaItem, MetodoPago
from app.models.producto import Producto
from app.models.inventario import MovimientoInventario
from app.schemas.reportes import ResumenPeriodo, VentaDia, ProductoTop, ProductoStockBajo, MapaVentas, SlotVenta

router = APIRouter(prefix="/reportes", tags=["reportes"])

# La tienda opera en Monterrey (UTC-6, sin DST).
# La DB guarda created_at como TIMESTAMP naive en UTC (`func.now()`).
# Para reportes, todo cálculo de fechas/horas se hace en hora local.
LOCAL_TZ = timezone(timedelta(hours=-6))
LOCAL_TZ_NAME = "America/Monterrey"


def _hoy_local() -> date:
    return datetime.now(LOCAL_TZ).date()


def _rango(fecha_inicio: date, fecha_fin: date):
    """Recibe fechas en horario local y devuelve datetimes naive en UTC
    para filtrar la columna `created_at` (que está en UTC)."""
    start_local = datetime(fecha_inicio.year, fecha_inicio.month, fecha_inicio.day, 0, 0, 0, tzinfo=LOCAL_TZ)
    end_local = datetime(fecha_fin.year, fecha_fin.month, fecha_fin.day, 23, 59, 59, tzinfo=LOCAL_TZ)
    return (
        start_local.astimezone(timezone.utc).replace(tzinfo=None),
        end_local.astimezone(timezone.utc).replace(tzinfo=None),
    )


def _local_ts(col):
    """Convierte una columna naive-UTC a naive-local para que `cast(.., Date)`
    y `extract('hour', ..)` agrupen por hora de Monterrey."""
    return func.timezone(LOCAL_TZ_NAME, func.timezone("UTC", col))


@router.get("/resumen", response_model=ResumenPeriodo)
async def resumen(
    fecha_inicio: date = Query(default=None),
    fecha_fin: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if fecha_inicio is None:
        fecha_inicio = _hoy_local().replace(day=1)
    if fecha_fin is None:
        fecha_fin = _hoy_local()

    start, end = _rango(fecha_inicio, fecha_fin)

    result = await db.execute(
        select(
            func.count(Venta.id).label("num_ventas"),
            func.coalesce(func.sum(Venta.total), 0).label("total"),
            func.coalesce(
                func.sum(case((Venta.metodo_pago == MetodoPago.efectivo, Venta.total), else_=0)), 0
            ).label("efectivo"),
            func.coalesce(
                func.sum(case((Venta.metodo_pago == MetodoPago.transferencia, Venta.total), else_=0)), 0
            ).label("transferencia"),
        ).where(
            Venta.store_id == current_user.store_id,
            Venta.created_at >= start,
            Venta.created_at <= end,
        )
    )
    row = result.one()
    total = float(row.total)

    # Inversión: lo gastado en restocks del período (usa costo real pagado)
    r_inv = await db.execute(
        select(
            func.coalesce(
                func.sum(
                    MovimientoInventario.cantidad *
                    func.coalesce(MovimientoInventario.costo_unitario, 0)
                ), 0
            ).label("inversion")
        )
        .where(
            MovimientoInventario.store_id == current_user.store_id,
            MovimientoInventario.tipo == "restock",
            MovimientoInventario.created_at >= start,
            MovimientoInventario.created_at <= end,
        )
    )
    inversion = float(r_inv.scalar() or 0)

    # Merma declarada en el período (informativo)
    r_merma = await db.execute(
        select(
            func.coalesce(
                func.sum(func.abs(MovimientoInventario.cantidad) * Producto.costo), 0
            ).label("merma")
        )
        .select_from(MovimientoInventario)
        .join(Producto, MovimientoInventario.producto_id == Producto.id)
        .where(
            MovimientoInventario.store_id == current_user.store_id,
            MovimientoInventario.tipo == "merma",
            MovimientoInventario.created_at >= start,
            MovimientoInventario.created_at <= end,
        )
    )
    merma = float(r_merma.scalar() or 0)

    return ResumenPeriodo(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        num_ventas=row.num_ventas,
        total=total,
        efectivo=float(row.efectivo),
        transferencia=float(row.transferencia),
        inversion=inversion,
        merma=merma,
        ganancia=total - inversion,
    )


@router.get("/ventas-por-dia", response_model=List[VentaDia])
async def ventas_por_dia(
    fecha_inicio: date = Query(default=None),
    fecha_fin: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if fecha_inicio is None:
        fecha_inicio = _hoy_local().replace(day=1)
    if fecha_fin is None:
        fecha_fin = _hoy_local()

    start, end = _rango(fecha_inicio, fecha_fin)
    fecha_col = cast(_local_ts(Venta.created_at), Date).label("fecha")

    result = await db.execute(
        select(
            fecha_col,
            func.count(Venta.id).label("num_ventas"),
            func.sum(Venta.total).label("total"),
            func.coalesce(
                func.sum(case((Venta.metodo_pago == MetodoPago.efectivo, Venta.total), else_=0)), 0
            ).label("efectivo"),
            func.coalesce(
                func.sum(case((Venta.metodo_pago == MetodoPago.transferencia, Venta.total), else_=0)), 0
            ).label("transferencia"),
        ).where(
            Venta.store_id == current_user.store_id,
            Venta.created_at >= start,
            Venta.created_at <= end,
        ).group_by(fecha_col).order_by(fecha_col)
    )
    rows = result.all()
    return [
        VentaDia(
            fecha=r.fecha,
            num_ventas=r.num_ventas,
            total=float(r.total),
            efectivo=float(r.efectivo),
            transferencia=float(r.transferencia),
        )
        for r in rows
    ]


@router.get("/productos-top", response_model=List[ProductoTop])
async def productos_top(
    fecha_inicio: date = Query(default=None),
    fecha_fin: date = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if fecha_inicio is None:
        fecha_inicio = _hoy_local().replace(day=1)
    if fecha_fin is None:
        fecha_fin = _hoy_local()

    start, end = _rango(fecha_inicio, fecha_fin)

    result = await db.execute(
        select(
            VentaItem.nombre,
            func.sum(VentaItem.cantidad).label("total_cantidad"),
            func.sum(VentaItem.subtotal).label("total_ingreso"),
        )
        .join(Venta, VentaItem.venta_id == Venta.id)
        .where(
            Venta.store_id == current_user.store_id,
            Venta.created_at >= start,
            Venta.created_at <= end,
        )
        .group_by(VentaItem.nombre)
        .order_by(func.sum(VentaItem.cantidad).desc())
        .limit(limit)
    )
    rows = result.all()
    return [
        ProductoTop(
            nombre=r.nombre,
            total_cantidad=int(r.total_cantidad),
            total_ingreso=float(r.total_ingreso),
        )
        for r in rows
    ]


@router.get("/stock-bajo", response_model=List[ProductoStockBajo])
async def stock_bajo(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Producto)
        .options(selectinload(Producto.categoria))
        .where(
            Producto.store_id == current_user.store_id,
            Producto.activo == True,
            Producto.stock <= Producto.stock_minimo,
        )
        .order_by(Producto.stock.asc())
    )
    productos = result.scalars().all()
    return [
        ProductoStockBajo(
            id=p.id,
            nombre=p.nombre,
            stock=p.stock,
            stock_minimo=p.stock_minimo,
            categoria=p.categoria.nombre if p.categoria else None,
        )
        for p in productos
    ]


_SLOTS = [
    (7,  9,  "7:00 - 9:00"),
    (9,  11, "9:00 - 11:00"),
    (11, 13, "11:00 - 13:00"),
    (13, 15, "13:00 - 15:00"),
    (15, 17, "15:00 - 17:00"),
    (17, 19, "17:00 - 19:00"),
    (19, 21, "19:00 - 21:00"),
]


@router.get("/mapa-ventas", response_model=MapaVentas)
async def mapa_ventas(
    fecha_inicio: date = Query(default=None),
    fecha_fin: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if fecha_inicio is None:
        fecha_inicio = _hoy_local().replace(day=1)
    if fecha_fin is None:
        fecha_fin = _hoy_local()

    start, end = _rango(fecha_inicio, fecha_fin)

    created_local = _local_ts(Venta.created_at)
    result = await db.execute(
        select(
            cast(created_local, Date).label("fecha"),
            func.extract("hour", created_local).label("hora"),
            func.sum(Venta.total).label("total"),
        ).where(
            Venta.store_id == current_user.store_id,
            Venta.created_at >= start,
            Venta.created_at <= end,
        ).group_by(
            cast(created_local, Date),
            func.extract("hour", created_local),
        )
    )
    rows = result.all()

    # Mapa (fecha, slot_idx) -> total
    lookup: dict = {}
    for r in rows:
        h = int(r.hora)
        for i, (h_start, h_end, _) in enumerate(_SLOTS):
            if h_start <= h < h_end:
                key = (r.fecha, i)
                lookup[key] = lookup.get(key, 0.0) + float(r.total)
                break

    delta = (fecha_fin - fecha_inicio).days + 1
    fechas = [fecha_inicio + timedelta(days=d) for d in range(delta)]

    slots = [
        SlotVenta(
            label=label,
            totales=[lookup.get((f, i), 0.0) for f in fechas],
        )
        for i, (_, _, label) in enumerate(_SLOTS)
    ]

    return MapaVentas(
        fechas=[str(f) for f in fechas],
        slots=slots,
    )
