from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.limiter import limiter

from app.database import engine, Base
from app.models import Store, User, Categoria, Producto, Venta, VentaItem, MovimientoInventario, Promocion  # noqa: F401 — needed for Base.metadata
from app.routers import auth, categorias, productos, ventas, reportes, users, inventario, stores, promociones


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Tiendita API", version="1.0.0", lifespan=lifespan, root_path="/api")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tienda.calderonluna.org",
        "http://localhost:61998",  # dev local
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(categorias.router)
app.include_router(productos.router)
app.include_router(ventas.router)
app.include_router(reportes.router)
app.include_router(users.router)
app.include_router(inventario.router)
app.include_router(stores.router)
app.include_router(promociones.router)
