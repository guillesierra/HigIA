from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.db.init_db import create_db


def create_app() -> FastAPI:
    app = FastAPI(
        title="HigIA API",
        description="Public medicine alerts, consumption, ATC, and Asturias document explorer.",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.on_event("startup")
    def on_startup() -> None:
        create_db()

    return app


app = create_app()

