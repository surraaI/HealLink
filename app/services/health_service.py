from datetime import datetime, timezone


class HealthService:
    def get_system_health(self) -> dict:
        return {
            "message": "HealLink backend is running",
            "status": "ok",
            "timestamp": datetime.now(timezone.utc),
        }
