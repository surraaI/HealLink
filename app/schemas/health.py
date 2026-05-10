from datetime import datetime

from pydantic import BaseModel


class HealthResponse(BaseModel):
    message: str
    status: str
    timestamp: datetime
