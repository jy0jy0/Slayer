"""FastAPI application factory."""

from __future__ import annotations

import logging

from fastapi import FastAPI

from slayer.api.routes import applications, health, resumes


def create_app() -> FastAPI:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    app = FastAPI(title="Slayer API", version="0.1.0")
    app.include_router(health.router)
    app.include_router(resumes.router, prefix="/api/v1")
    app.include_router(applications.router, prefix="/api/v1")
    return app


app = create_app()
