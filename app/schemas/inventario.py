from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class RestockRequest(BaseModel):
    producto_id: str
    cantidad: int = Field(gt=0, description="Cantidad a agregar (debe ser positiva)")
    notas: Optional[str] = None


class AjusteRequest(BaseModel):
    producto_id: str
    cantidad: int = Field(gt=0, description="Cantidad a descontar (positiva, se guarda negativa)")
    tipo: str = Field(description="merma | muestra | otro")
    notas: Optional[str] = None


class MovimientoResponse(BaseModel):
    id: str
    producto_id: Optional[str]
    nombre_producto: str
    cantidad: int
    stock_antes: int
    stock_despues: int
    tipo: Optional[str]
    notas: Optional[str]
    user_name: str
    created_at: datetime

    class Config:
        from_attributes = True
