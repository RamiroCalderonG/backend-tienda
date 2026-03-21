import uuid
from typing import Optional
from sqlalchemy import String, ForeignKey, DateTime, func, Boolean, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Producto(Base):
    __tablename__ = "productos"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id: Mapped[str] = mapped_column(String, ForeignKey("stores.id"), nullable=False)
    categoria_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("categorias.id"), nullable=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    costo: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    precio: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stock_minimo: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    categoria: Mapped[Optional["Categoria"]] = relationship("Categoria", back_populates="productos")
    promocion: Mapped[Optional["Promocion"]] = relationship("Promocion", back_populates="producto", uselist=False)
