from enum import Enum

from pydantic import BaseModel, HttpUrl


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    DOWN = "DOWN"


class ServiceConfig(BaseModel):
    name: str
    health_url: HttpUrl
    timeout_seconds: float = 5.0
    latency_threshold_ms: float = 1000.0


class HealthCheckResult(BaseModel):
    service_name: str
    status: HealthStatus

    status_code: int | None = None

    latency_ms: float | None = None

    message: str
