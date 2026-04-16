"""Agrega columna foto a la tabla productos."""
import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal


async def main():
    async with AsyncSessionLocal() as db:
        await db.execute(text(
            "ALTER TABLE productos ADD COLUMN IF NOT EXISTS foto TEXT"
        ))
        await db.commit()
        print("✓ Columna 'foto' agregada a productos.")


if __name__ == "__main__":
    asyncio.run(main())
