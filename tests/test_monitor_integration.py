import os

import pytest

from monitoring.http_checker import check_service
from monitoring.models import (
    HealthStatus,
    ServiceConfig,
)


SIMULATOR_URL = os.getenv(
    "NOVAOPS_SIMULATOR_URL"
)


@pytest.mark.integration
def test_real_render_health_endpoint():
    """
    Integration test against the real
    NovaOps DEV simulator deployed on Render.
    """

    if not SIMULATOR_URL:
        pytest.skip(
            "NOVAOPS_SIMULATOR_URL is not configured."
        )

    service = ServiceConfig(
        name="NovaOps DEV Simulator",

        health_url=(
            SIMULATOR_URL.rstrip("/")
            + "/health"
        ),

        # Render free instances can take time
        # to wake after inactivity.
        timeout_seconds=60.0,

        # This test verifies connectivity,
        # not production latency performance.
        latency_threshold_ms=60000.0,
    )

    result = check_service(service)

    assert result.status in {
        HealthStatus.HEALTHY,
        HealthStatus.DEGRADED,
    }

    assert result.status_code == 200
