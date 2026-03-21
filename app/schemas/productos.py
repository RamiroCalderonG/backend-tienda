from typing import Optional
from pydantic import BaseModel
from app.schemas.promociones import PromocionResponse


# ── Categorías ──────────────────────────────────────────────

class CategoriaCreate(BaseModel):
    nombre: str


class CategoriaResponse(BaseModel):
    id: str
    store_id: str
    nombre: str

    model_config = {"from_attributes": True}


# ── Productos ────────────────────────────────────────────────

class ProductoCreate(BaseModel):
    categoria_id: Optional[str] = None
    nombre: str
    descripcion: Optional[str] = None
    costo: float = 0
    precio: float
    stock: int = 0
    stock_minimo: int = 5


class ProductoUpdate(BaseModel):
    categoria_id: Optional[str] = None
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    costo: Optional[float] = None
    precio: Optional[float] = None
    stock: Optional[int] = None
    stock_minimo: Optional[int] = None
    activo: Optional[bool] = None


class ProductoResponse(BaseModel):
    id: str
    store_id: str
    categoria_id: Optional[str]
    nombre: str
    descripcion: Optional[str]
    costo: float
    precio: float
    stock: int
    stock_minimo: int
    activo: bool
    categoria: Optional[CategoriaResponse] = None
    promocion: Optional[PromocionResponse] = None

    model_config = {"from_attributes": True}
