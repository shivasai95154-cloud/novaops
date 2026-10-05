from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


app = FastAPI(
    title="NovaOps Service Simulator",
    description=(
        "Development service used to simulate "
        "real infrastructure health conditions."
    ),
    version="1.0.0",
)


class ServiceState(BaseModel):
    status: str = "healthy"
    response_time_ms: int = 50


service_state = ServiceState()


@app.get("/")
def root():
    return {
        "service": "NovaOps Service Simulator",
        "environment": "DEV",
        "status": "running",
    }


@app.get("/health")
def health():
    """
    Health endpoint used by the future NovaOps monitor.
    """

    if service_state.status == "unhealthy":
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "response_time_ms": service_state.response_time_ms,
            },
        )

    return {
        "status": service_state.status,
        "response_time_ms": service_state.response_time_ms,
    }


@app.get("/metrics")
def metrics():
    return {
        "status": service_state.status,
        "response_time_ms": service_state.response_time_ms,
    }


@app.post("/test/failure")
def simulate_failure():
    """
    DEV-only endpoint used to simulate a service outage.
    """

    service_state.status = "unhealthy"
    service_state.response_time_ms = 0

    return {
        "message": "Failure simulation enabled.",
        "status": service_state.status,
    }


@app.post("/test/recovery")
def simulate_recovery():
    """
    Restore the simulated service.
    """

    service_state.status = "healthy"
    service_state.response_time_ms = 50

    return {
        "message": "Service recovered.",
        "status": service_state.status,
    }
