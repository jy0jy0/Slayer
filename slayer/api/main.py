"""FastAPI application factory."""

# from fastapi import FastAPI
# from slayer.api.routes import resumes, applications, health
#
# def create_app() -> FastAPI:
#     app = FastAPI(title="Slayer API", version="0.1.0")
#     app.include_router(health.router)
#     app.include_router(resumes.router, prefix="/api/v1")
#     app.include_router(applications.router, prefix="/api/v1")
#     return app
