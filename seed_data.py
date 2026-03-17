"""Seed: 10 productos + ventas en los últimos 10 días con horarios variados."""
import asyncio
import random
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.store import Store
from app.models.categoria import Categoria
from app.models.producto import Producto
from app.models.venta import Venta, VentaItem, MetodoPago

# Franjas horarias y sus probabilidades (simula un negocio real)
FRANJAS = [
    (7, 8),   # 7-9
    (8, 9),
    (9, 10),  # 9-11
    (10, 11),
    (11, 12), # 11-13
    (12, 13),
    (13, 14), # 13-15
    (14, 15),
    (15, 16), # 15-17
    (16, 17),
    (17, 18), # 17-19
    (18, 19),
    (19, 20), # 19-21
]

PESOS = [2, 3, 8, 10, 12, 15, 8, 6, 7, 9, 11, 7, 2]  # más ventas al mediodía y tarde

CATEGORIAS_PRODUCTOS = {
    "Panadería": [
        ("Bolillo",        3.50,   2.00, 100),
        ("Telera",         4.00,   2.50, 80),
        ("Cuernito",       5.00,   3.00, 60),
        ("Pan dulce",      6.00,   3.50, 120),
    ],
    "Bebidas": [
        ("Café americano", 18.00, 10.00, 50),
        ("Cappuccino",     25.00, 14.00, 40),
        ("Agua natural",   12.00,  6.00, 80),
    ],
    "Snacks": [
        ("Galletas",       15.00,  8.00, 60),
        ("Empanada",       20.00, 11.00, 45),
        ("Tamal",          22.00, 12.00, 30),
    ],
}


async def main():
    async with AsyncSessionLocal() as db:
        # Tomar el primer store y admin
        result = await db.execute(select(User).where(User.role == "admin").limit(1))
        admin = result.scalar_one_or_none()
        if not admin:
            print("No hay usuario admin. Registra una tienda primero.")
            return

        store_id = admin.store_id
        user_id = admin.id
        print(f"Store: {store_id}  |  Admin: {admin.email}")

        # ── Categorías ────────────────────────────────────────
        categorias = {}
        for nombre_cat in CATEGORIAS_PRODUCTOS:
            result = await db.execute(
                select(Categoria).where(Categoria.store_id == store_id, Categoria.nombre == nombre_cat)
            )
            cat = result.scalar_one_or_none()
            if not cat:
                cat = Categoria(id=str(uuid.uuid4()), store_id=store_id, nombre=nombre_cat)
                db.add(cat)
                await db.flush()
                print(f"  + Categoría: {nombre_cat}")
            categorias[nombre_cat] = cat

        # ── Productos ─────────────────────────────────────────
        productos = []
        for nombre_cat, items in CATEGORIAS_PRODUCTOS.items():
            cat = categorias[nombre_cat]
            for nombre, precio, costo, stock in items:
                result = await db.execute(
                    select(Producto).where(Producto.store_id == store_id, Producto.nombre == nombre)
                )
                p = result.scalar_one_or_none()
                if not p:
                    p = Producto(
                        id=str(uuid.uuid4()),
                        store_id=store_id,
                        categoria_id=cat.id,
                        nombre=nombre,
                        descripcion="",
                        costo=costo,
                        precio=precio,
                        stock=stock,
                        stock_minimo=10,
                        activo=True,
                    )
                    db.add(p)
                    await db.flush()
                    print(f"  + Producto: {nombre} ${precio}")
                productos.append(p)

        await db.commit()
        print(f"\n{len(productos)} productos listos. Generando ventas...\n")

        # ── Ventas: últimos 10 días ───────────────────────────
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        total_ventas = 0

        for dias_atras in range(10, 0, -1):
            dia_base = hoy - timedelta(days=dias_atras)
            # Entre 8 y 20 ventas por día
            num_ventas = random.randint(8, 20)

            for _ in range(num_ventas):
                hora = random.choices(FRANJAS, weights=PESOS, k=1)[0]
                minuto = random.randint(0, 59)
                segundo = random.randint(0, 59)
                ts = dia_base.replace(
                    hour=hora[0] + random.randint(0, hora[1] - hora[0]),
                    minute=minuto,
                    second=segundo,
                )

                metodo = random.choices(
                    [MetodoPago.efectivo, MetodoPago.transferencia],
                    weights=[65, 35], k=1
                )[0]

                # 1-4 productos por venta
                num_items = random.randint(1, 4)
                seleccion = random.sample(productos, min(num_items, len(productos)))

                venta_id = str(uuid.uuid4())
                items_data = []
                total = 0.0

                for prod in seleccion:
                    cantidad = random.randint(1, 3)
                    subtotal = float(prod.precio) * cantidad
                    total += subtotal
                    items_data.append(VentaItem(
                        id=str(uuid.uuid4()),
                        venta_id=venta_id,
                        producto_id=prod.id,
                        nombre=prod.nombre,
                        precio=float(prod.precio),
                        cantidad=cantidad,
                        subtotal=subtotal,
                    ))

                venta = Venta(
                    id=venta_id,
                    store_id=store_id,
                    user_id=user_id,
                    total=round(total, 2),
                    metodo_pago=metodo,
                    created_at=ts,
                )
                db.add(venta)
                for item in items_data:
                    db.add(item)

                total_ventas += 1

            await db.commit()
            print(f"  Día {dia_base.strftime('%Y-%m-%d')}: {num_ventas} ventas")

        print(f"\n✓ {total_ventas} ventas generadas en 10 días.")


if __name__ == "__main__":
    asyncio.run(main())
