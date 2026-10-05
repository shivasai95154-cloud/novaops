import os

from monitoring.models import ServiceConfig


def get_monitored_services():
    """
    Return services registered for monitoring.

    URLs are loaded from environment variables
    instead of being hard-coded into monitoring logic.
    """

    simulator_url = os.getenv(
        "NOVAOPS_SIMULATOR_URL"
    )

    if not simulator_url:

        return []

    health_url = (
        simulator_url.rstrip("/")
        + "/health"
    )

    return [
        ServiceConfig(
            name="NovaOps DEV Simulator",
            health_url=health_url,
            timeout_seconds=10.0,
            latency_threshold_ms=3000.0,
        )
    ]
