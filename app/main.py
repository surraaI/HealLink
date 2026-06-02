import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import appointments, auth, health, notifications, patients, payments, providers, admin, qr_checkin, diagnostic_results, reviews, schedules


settings = get_settings()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _cors_origins() -> list[str]:
    origins = ["http://localhost:3000"]
    frontend_url = settings.frontend_url.strip().rstrip("/")
    if frontend_url:
        origins.append(frontend_url)
    return origins


def create_app() -> FastAPI:
    app = FastAPI(
        title="HealLink API",
        version="0.1.0",
        description="Digital healthcare appointment and diagnostic platform API.",
    )

    @app.middleware("http")
    async def log_requests(request, call_next):
        logger.info(f"Incoming request: {request.method} {request.url.path}")
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code} for {request.method} {request.url.path}")
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
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
    app.include_router(schedules.router, prefix="/api/v1")
    app.include_router(payments.router, prefix="/api/v1")
    app.include_router(qr_checkin.router, prefix="/api/v1")
    app.include_router(diagnostic_results.router, prefix="/api/v1")
    app.include_router(reviews.router, prefix="/api/v1")
    app.include_router(admin.router)

    return app


app = create_app()
