import os
import time

import pytest
import requests

from monitoring.http_checker import check_service
from monitoring.models import ServiceConfig
from monitoring.worker import run_monitoring_cycle


SIMULATOR_URL = os.getenv(
    "NOVAOPS_SIMULATOR_URL",
    "",
).rstrip("/")


def simulator_request(path):
    """
    Call one of the DEV simulator control endpoints.
    """

    response = requests.post(
        f"{SIMULATOR_URL}{path}",
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


@pytest.mark.e2e
def test_real_incident_lifecycle():
    """
    End-to-end DEV lifecycle test.

    This test deliberately:

    1. Makes the DEV simulator healthy.
    2. Confirms NovaOps can observe it.
    3. Makes the simulator unhealthy.
    4. Runs enough monitoring cycles to open an incident.
    5. Keeps the service unhealthy for another cycle.
    6. Restores the simulator.
    7. Runs enough monitoring cycles to resolve the incident.

    Real notifications may be sent when SMTP
    configuration is supplied to the workflow.
    """

    if not SIMULATOR_URL:
        pytest.skip(
            "NOVAOPS_SIMULATOR_URL is not configured."
        )

    service = ServiceConfig(
        name="NovaOps DEV Simulator",
        health_url=f"{SIMULATOR_URL}/health",
        timeout_seconds=30,
        latency_threshold_ms=5000,
    )

    # ---------------------------------------------
    # BASELINE — HEALTHY
    # ---------------------------------------------

    simulator_request(
        "/test/recovery"
    )

    time.sleep(1)

    baseline = check_service(
        service
    )

    assert baseline.status.value == "HEALTHY"

    # Establish healthy state.
    run_monitoring_cycle(
        [service]
    )

    # ---------------------------------------------
    # SIMULATE OUTAGE
    # ---------------------------------------------

    simulator_request(
        "/test/failure"
    )

    time.sleep(1)

    # Failure observation #1
    run_monitoring_cycle(
        [service]
    )

    # Failure observation #2
    run_monitoring_cycle(
        [service]
    )

    # Failure observation #3
    #
    # State engine should now generate
    # INCIDENT_OPENED.
    run_monitoring_cycle(
        [service]
    )

    # One additional failed check proves that
    # an existing outage does not continuously
    # generate new incident events.
    run_monitoring_cycle(
        [service]
    )

    # ---------------------------------------------
    # RESTORE SERVICE
    # ---------------------------------------------

    simulator_request(
        "/test/recovery"
    )

    time.sleep(1)

    recovered = check_service(
        service
    )

    assert recovered.status.value == "HEALTHY"

    # Recovery observation #1
    run_monitoring_cycle(
        [service]
    )

    # Recovery observation #2
    #
    # State engine should now generate
    # INCIDENT_RESOLVED.
    run_monitoring_cycle(
        [service]
    )
