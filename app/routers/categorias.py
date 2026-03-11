import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.categoria import Categoria
from app.models.user import User
from app.schemas.productos import CategoriaCreate, CategoriaResponse
from app.dependencies.auth import get_current_user, require_admin

router = APIRouter(prefix="/categorias", tags=["categorias"])


@router.get("", response_model=list[CategoriaResponse])
async def listar_categorias(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Categoria).where(Categoria.store_id == current_user.store_id)
    )
    return result.scalars().all()


@router.post("", response_model=CategoriaResponse, status_code=201)
async def crear_categoria(
    body: CategoriaCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    categoria = Categoria(
        id=str(uuid.uuid4()),
        store_id=current_user.store_id,
        nombre=body.nombre,
    )
    db.add(categoria)
    await db.commit()
    await db.refresh(categoria)
    return categoria


@router.delete("/{categoria_id}", status_code=204)
async def eliminar_categoria(
    categoria_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Categoria).where(
            Categoria.id == categoria_id,
            Categoria.store_id == current_user.store_id,
        )
    )
    categoria = result.scalar_one_or_none()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    await db.delete(categoria)
    await db.commit()
