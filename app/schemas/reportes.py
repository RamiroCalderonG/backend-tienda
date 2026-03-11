from pydantic import BaseModel
from datetime import date
from typing import Optional, List


class ResumenPeriodo(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    num_ventas: int
    total: float
    efectivo: float
    transferencia: float
    inversion: float
    merma: float
    ganancia: float   # total - inversion


class VentaDia(BaseModel):
    fecha: date
    num_ventas: int
    total: float
    efectivo: float
    transferencia: float


class ProductoTop(BaseModel):
    nombre: str
    total_cantidad: int
    total_ingreso: float


class ProductoStockBajo(BaseModel):
    id: str
    nombre: str
    stock: int
    stock_minimo: int
    categoria: Optional[str] = None


class SlotVenta(BaseModel):
    label: str
    totales: List[float]


class MapaVentas(BaseModel):
    fechas: List[str]
    slots: List[SlotVenta]
