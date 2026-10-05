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
@pytest.mark.outage
def test_monitor_detects_real_service_outage():
    """
    Verify that NovaOps detects the real DEV
    simulator when it is returning HTTP 503.
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
        timeout_seconds=60.0,
        latency_threshold_ms=60000.0,
    )

    result = check_service(service)

    print(
        f"\nService: {result.service_name}"
        f"\nStatus: {result.status.value}"
        f"\nHTTP: {result.status_code}"
        f"\nLatency: {result.latency_ms} ms"
        f"\nMessage: {result.message}"
    )

    assert result.status == HealthStatus.UNHEALTHY
    assert result.status_code == 503
