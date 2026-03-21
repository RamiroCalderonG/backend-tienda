from pydantic import BaseModel


class PromocionCreate(BaseModel):
    producto_id: str
    cantidad_requerida: int
    precio_promocion: float


class PromocionResponse(BaseModel):
    id: int
    producto_id: str
    cantidad_requerida: int
    precio_promocion: float

    model_config = {"from_attributes": True}
