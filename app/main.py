from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import appointments, auth, health, notifications, patients, payments, providers, admin


def create_app() -> FastAPI:
    app = FastAPI(
        title="HealLink API",
        version="0.1.0",
        description="Digital healthcare appointment and diagnostic platform API.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(patients.router, prefix="/api/v1")
    app.include_router(notifications.router, prefix="/api/v1")
    app.include_router(appointments.router, prefix="/api/v1")
    app.include_router(providers.router, prefix="/api/v1")
    app.include_router(payments.router, prefix="/api/v1")
    app.include_router(admin.router)

    return app


app = create_app()
