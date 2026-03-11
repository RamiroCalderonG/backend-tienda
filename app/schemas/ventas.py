from typing import Optional, List
from pydantic import BaseModel
from enum import Enum
from datetime import datetime


class MetodoPago(str, Enum):
    efectivo = "efectivo"
    transferencia = "transferencia"


class VentaItemCreate(BaseModel):
    producto_id: str
    cantidad: int


class VentaCreate(BaseModel):
    metodo_pago: MetodoPago
    items: List[VentaItemCreate]


class VentaItemResponse(BaseModel):
    id: str
    producto_id: Optional[str]
    nombre: str
    precio: float
    cantidad: int
    subtotal: float

    model_config = {"from_attributes": True}


class VentaResponse(BaseModel):
    id: str
    store_id: str
    user_id: str
    total: float
    metodo_pago: MetodoPago
    created_at: datetime
    items: List[VentaItemResponse] = []

    model_config = {"from_attributes": True}
