import uuid
from typing import Optional
from sqlalchemy import String, ForeignKey, DateTime, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventario"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id: Mapped[str] = mapped_column(String, ForeignKey("stores.id"), nullable=False)
    producto_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("productos.id", ondelete="SET NULL"), nullable=True)
    nombre_producto: Mapped[str] = mapped_column(String, nullable=False)   # snapshot
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_antes: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_despues: Mapped[int] = mapped_column(Integer, nullable=False)
    costo_unitario: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)  # costo real pagado (snapshot)
    tipo: Mapped[Optional[str]] = mapped_column(String, nullable=True)   # restock | merma | muestra | otro
    notas: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    user_name: Mapped[str] = mapped_column(String, nullable=False)         # snapshot
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
