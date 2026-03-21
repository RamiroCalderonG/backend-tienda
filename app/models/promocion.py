from sqlalchemy import Integer, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Promocion(Base):
    __tablename__ = "promociones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    producto_id: Mapped[str] = mapped_column(ForeignKey("productos.id"), nullable=False, unique=True)
    cantidad_requerida: Mapped[int] = mapped_column(Integer, nullable=False)
    precio_promocion: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    producto: Mapped["Producto"] = relationship("Producto", back_populates="promocion")
