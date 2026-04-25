"""Lista usuarios y permite resetear password."""
import asyncio
from sqlalchemy import select, update
from passlib.context import CryptContext
from app.database import AsyncSessionLocal
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User.email, User.name, User.role, User.is_active))
        users = result.all()

        print("\nUsuarios registrados:")
        for i, u in enumerate(users):
            print(f"  [{i}] {u.email}  ({u.role})  {'activo' if u.is_active else 'inactivo'}")

        email = input("\nEmail a resetear (Enter para salir): ").strip()
        if not email:
            return

        nueva = input("Nueva password: ").strip()
        if not nueva:
            print("Password vacía, cancelado.")
            return

        await db.execute(
            update(User)
            .where(User.email == email)
            .values(hashed_password=pwd_context.hash(nueva))
        )
        await db.commit()
        print(f"✓ Password de {email} actualizada.")


if __name__ == "__main__":
    asyncio.run(main())
