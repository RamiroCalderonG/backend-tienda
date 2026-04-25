"""Borra todas las tiendas excepto las indicadas (por defecto: solo 'Sistema').

Limpia en cascada todos los datos asociados (promociones, venta_items,
ventas, movimientos de inventario, productos, categorias) y reasigna los
usuarios restantes a la tienda 'Sistema' para no perder al admin principal.

Uso:
    python delete_stores.py
    python delete_stores.py --yes
    python delete_stores.py --keep-id 00000000-0000-0000-0000-000000000000 --keep-id <otro-id>
"""
import argparse
import asyncio
import sys

from sqlalchemy import select, update, delete, func

from app.database import AsyncSessionLocal
from app.models.store import Store
from app.models.user import User
from app.models.categoria import Categoria
from app.models.producto import Producto
from app.models.inventario import MovimientoInventario
from app.models.venta import Venta, VentaItem
from app.models.promocion import Promocion

SYSTEM_STORE_ID = "00000000-0000-0000-0000-000000000000"


async def run(keep_ids: list[str], skip_confirm: bool) -> int:
    async with AsyncSessionLocal() as session:
        if SYSTEM_STORE_ID not in keep_ids:
            keep_ids.append(SYSTEM_STORE_ID)

        all_stores = (await session.execute(select(Store))).scalars().all()
        to_delete = [s for s in all_stores if s.id not in keep_ids]

        if not to_delete:
            print("No hay tiendas para borrar.")
            return 0

        delete_ids = [s.id for s in to_delete]

        prods_count = (await session.execute(
            select(func.count(Producto.id)).where(Producto.store_id.in_(delete_ids))
        )).scalar() or 0
        ventas_count = (await session.execute(
            select(func.count(Venta.id)).where(Venta.store_id.in_(delete_ids))
        )).scalar() or 0
        movs_count = (await session.execute(
            select(func.count(MovimientoInventario.id)).where(MovimientoInventario.store_id.in_(delete_ids))
        )).scalar() or 0
        cats_count = (await session.execute(
            select(func.count(Categoria.id)).where(Categoria.store_id.in_(delete_ids))
        )).scalar() or 0
        users_to_move = (await session.execute(
            select(User).where(User.store_id.in_(delete_ids))
        )).scalars().all()

        print()
        print(f"Tiendas a CONSERVAR: {len(all_stores) - len(to_delete)}")
        for s in all_stores:
            if s.id in keep_ids:
                print(f"  ✓ {s.name}  (id={s.id})")
        print()
        print(f"Tiendas a BORRAR: {len(to_delete)}")
        for s in to_delete:
            print(f"  ✗ {s.name}  (id={s.id})")
        print()
        print(f"Datos que se borran en cascada:")
        print(f"  - Productos:    {prods_count}")
        print(f"  - Ventas:       {ventas_count}  (+ sus venta_items y promociones)")
        print(f"  - Movimientos:  {movs_count}")
        print(f"  - Categorias:   {cats_count}")
        print()
        print(f"Usuarios a reasignar a la tienda 'Sistema': {len(users_to_move)}")
        for u in users_to_move:
            print(f"  → {u.email}  (role={u.role.value})")
        print()

        if not skip_confirm:
            answer = input("Escribe 'BORRAR' para continuar: ").strip()
            if answer != "BORRAR":
                print("Cancelado. No se realizaron cambios.")
                return 1

        try:
            # 1. promociones → productos de tiendas borradas
            await session.execute(
                delete(Promocion).where(
                    Promocion.producto_id.in_(
                        select(Producto.id).where(Producto.store_id.in_(delete_ids))
                    )
                )
            )
            # 2. venta_items → ventas de tiendas borradas (y productos de tiendas borradas)
            await session.execute(
                delete(VentaItem).where(
                    VentaItem.venta_id.in_(
                        select(Venta.id).where(Venta.store_id.in_(delete_ids))
                    )
                )
            )
            await session.execute(
                delete(VentaItem).where(
                    VentaItem.producto_id.in_(
                        select(Producto.id).where(Producto.store_id.in_(delete_ids))
                    )
                )
            )
            # 3. ventas
            await session.execute(
                delete(Venta).where(Venta.store_id.in_(delete_ids))
            )
            # 4. movimientos de inventario
            await session.execute(
                delete(MovimientoInventario).where(MovimientoInventario.store_id.in_(delete_ids))
            )
            # 5. productos
            await session.execute(
                delete(Producto).where(Producto.store_id.in_(delete_ids))
            )
            # 6. categorias
            await session.execute(
                delete(Categoria).where(Categoria.store_id.in_(delete_ids))
            )
            # 7. mover usuarios a la tienda Sistema
            await session.execute(
                update(User)
                .where(User.store_id.in_(delete_ids))
                .values(store_id=SYSTEM_STORE_ID)
            )
            # 8. borrar tiendas
            await session.execute(
                delete(Store).where(Store.id.in_(delete_ids))
            )
            await session.commit()
        except Exception as exc:
            await session.rollback()
            print(f"ERROR durante el borrado, transacción revertida: {exc}")
            return 1

        remaining = (await session.execute(select(func.count(Store.id)))).scalar()
        print()
        print(f"Listo. Tiendas borradas: {len(to_delete)}. Tiendas restantes: {remaining}.")
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keep-id",
        action="append",
        default=[],
        help="ID de tienda a conservar (puede repetirse). 'Sistema' siempre se conserva.",
    )
    parser.add_argument("--yes", action="store_true", help="Saltar confirmación interactiva")
    args = parser.parse_args()

    sys.exit(asyncio.run(run(args.keep_id, args.yes)))


if __name__ == "__main__":
    main()
