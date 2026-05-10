from fastapi import FastAPI

from app.routers import appointments, auth, health, patients


def create_app() -> FastAPI:
    app = FastAPI(
        title="HealLink API",
        version="0.1.0",
        description="Digital healthcare appointment and diagnostic platform API.",
    )
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(patients.router, prefix="/api/v1")
    app.include_router(appointments.router, prefix="/api/v1")

    return app


app = create_app()
