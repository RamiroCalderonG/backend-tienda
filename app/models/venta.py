import uuid
import enum
from typing import Optional, List
from sqlalchemy import String, ForeignKey, DateTime, func, Enum, Numeric, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MetodoPago(str, enum.Enum):
    efectivo = "efectivo"
    transferencia = "transferencia"


class Venta(Base):
    __tablename__ = "ventas"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id: Mapped[str] = mapped_column(String, ForeignKey("stores.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    metodo_pago: Mapped[MetodoPago] = mapped_column(Enum(MetodoPago), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    items: Mapped[List["VentaItem"]] = relationship("VentaItem", back_populates="venta")


class VentaItem(Base):
    __tablename__ = "venta_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    venta_id: Mapped[str] = mapped_column(String, ForeignKey("ventas.id"), nullable=False)
    producto_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("productos.id"), nullable=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)   # snapshot
    precio: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)       # snapshot
    costo_unitario: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)  # snapshot
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    venta: Mapped["Venta"] = relationship("Venta", back_populates="items")
