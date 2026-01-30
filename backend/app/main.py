from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import auth, products, partners, warehouses, docs, stock, sns
from app.core.security import hash_password
from app.core.config import BASE_DIR
from app.db.base import Base
from app.db.session import engine
from app.models import User


def create_app() -> FastAPI:
    app = FastAPI(title="jxc_manage")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(products.router)
    app.include_router(partners.router)
    app.include_router(warehouses.router)
    app.include_router(docs.router)
    app.include_router(stock.router)
    app.include_router(sns.router)

    dist_path = BASE_DIR / "frontend" / "dist"
    web_path = Path(__file__).resolve().parent / "web"

    if dist_path.exists():
        app.mount("/", StaticFiles(directory=str(dist_path), html=True), name="static")
    else:
        app.mount("/static", StaticFiles(directory=str(web_path)), name="static")

        @app.get("/")
        def index():
            return FileResponse(web_path / "index.html")

    @app.on_event("startup")
    def on_startup():
        Base.metadata.create_all(bind=engine)
        with engine.begin() as conn:
            admin = conn.execute(
                User.__table__.select().where(User.__table__.c.username == "admin")
            ).fetchone()
            if admin is None:
                conn.execute(
                    User.__table__.insert().values(
                        username="admin",
                        password_hash=hash_password("admin123"),
                        role="admin",
                        is_active=True,
                    )
                )
            else:
                # Auto-migrate legacy bcrypt hash to pbkdf2 to avoid bcrypt backend issues.
                if str(admin.password_hash).startswith(("$2a$", "$2b$", "$2y$")):
                    conn.execute(
                        User.__table__.update()
                        .where(User.__table__.c.username == "admin")
                        .values(password_hash=hash_password("admin123"))
                    )

    return app


app = create_app()
