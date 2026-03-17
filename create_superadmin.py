"""
Script para crear el usuario superadmin del sistema.
Uso: python create_superadmin.py

Crea una tienda "Sistema" y un usuario superadmin asociado a ella.
Solo necesita ejecutarse una vez.
"""
import asyncio
import uuid
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.config import settings
from app.models.store import Store
from app.models.user import User, UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_superadmin():
    # Pedir datos
    print("=== Crear Superadmin ===\n")
    name = input("Nombre: ").strip() or "Super Admin"
    email = input("Email: ").strip()
    if not email:
        print("El email es obligatorio.")
        return
    password = input("Contraseña: ").strip()
    if not password:
        print("La contraseña es obligatoria.")
        return

    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Verificar que no exista el email
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            print(f"\n❌ Ya existe un usuario con el email {email}")
            return

        # Crear tienda del sistema (si no existe)
        system_store_id = "00000000-0000-0000-0000-000000000000"
        result = await db.execute(select(Store).where(Store.id == system_store_id))
        store = result.scalar_one_or_none()
        if not store:
            store = Store(
                id=system_store_id,
                name="Sistema",
                address=None,
                config={},
            )
            db.add(store)
            print("✅ Tienda 'Sistema' creada")

        # Crear superadmin
        user = User(
            id=str(uuid.uuid4()),
            store_id=system_store_id,
            name=name,
            email=email,
            hashed_password=pwd_context.hash(password),
            role=UserRole.superadmin,
            is_active=True,
        )
        db.add(user)
        await db.commit()

        print(f"\n✅ Superadmin creado exitosamente")
        print(f"   Nombre: {name}")
        print(f"   Email:  {email}")
        print(f"   Rol:    superadmin")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_superadmin())
