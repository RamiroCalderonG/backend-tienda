"""Borra todos los usuarios excepto el admin indicado por --keep-email.

Reasigna ventas y movimientos de inventario al admin conservado para no
violar las FK NOT NULL.

Uso:
    python delete_users.py --keep-email admin@ejemplo.com
    python delete_users.py --keep-email admin@ejemplo.com --yes
"""
import argparse
import asyncio
import sys

from sqlalchemy import select, update, delete, func

from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.venta import Venta
from app.models.inventario import MovimientoInventario


async def run(keep_email: str, skip_confirm: bool) -> int:
    async with AsyncSessionLocal() as session:
        admin = (
            await session.execute(select(User).where(User.email == keep_email))
        ).scalar_one_or_none()

        if admin is None:
            print(f"ERROR: no existe ningún usuario con email '{keep_email}'.")
            return 1

        to_delete = (
            await session.execute(select(User).where(User.id != admin.id))
        ).scalars().all()

        if not to_delete:
            print(f"No hay usuarios para borrar. Solo existe '{admin.email}'.")
            return 0

        ids_a_borrar = [u.id for u in to_delete]

        ventas_count = (
            await session.execute(
                select(func.count(Venta.id)).where(Venta.user_id.in_(ids_a_borrar))
            )
        ).scalar() or 0
        movs_count = (
            await session.execute(
                select(func.count(MovimientoInventario.id)).where(
                    MovimientoInventario.user_id.in_(ids_a_borrar)
                )
            )
        ).scalar() or 0

        print()
        print(f"Admin a conservar: {admin.email}  (id={admin.id}, role={admin.role.value})")
        print(f"Usuarios a borrar: {len(to_delete)}")
        for u in to_delete:
            print(f"  - {u.email}  (role={u.role.value}, store_id={u.store_id})")
        print()
        print(f"Ventas a reasignar al admin conservado:       {ventas_count}")
        print(f"Movimientos a reasignar al admin conservado:  {movs_count}")
        print()

        if not skip_confirm:
            answer = input("Escribe 'BORRAR' para continuar: ").strip()
            if answer != "BORRAR":
                print("Cancelado. No se realizaron cambios.")
                return 1

        try:
            if ventas_count:
                await session.execute(
                    update(Venta)
                    .where(Venta.user_id.in_(ids_a_borrar))
                    .values(user_id=admin.id)
                )
            if movs_count:
                await session.execute(
                    update(MovimientoInventario)
                    .where(MovimientoInventario.user_id.in_(ids_a_borrar))
                    .values(user_id=admin.id)
                )
            await session.execute(delete(User).where(User.id.in_(ids_a_borrar)))
            await session.commit()
        except Exception as exc:
            await session.rollback()
            print(f"ERROR durante el borrado, transacción revertida: {exc}")
            return 1

        remaining = (
            await session.execute(select(func.count(User.id)))
        ).scalar()
        print()
        print(f"Listo. Usuarios borrados: {len(to_delete)}. Usuarios restantes: {remaining}.")
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep-email", required=True, help="Email del admin que se conserva")
    parser.add_argument("--yes", action="store_true", help="Saltar confirmación interactiva")
    args = parser.parse_args()

    sys.exit(asyncio.run(run(args.keep_email, args.yes)))


if __name__ == "__main__":
    main()
