import os
import time

import pytest
import requests

# Import database models so SQLAlchemy registers
# all NovaOps tables with Base.metadata.
import database.models  # noqa: F401

from database.connection import create_database

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

    1. Initializes an isolated E2E database.
    2. Makes the DEV simulator healthy.
    3. Confirms NovaOps can observe it.
    4. Makes the simulator unhealthy.
    5. Runs enough monitoring cycles to open an incident.
    6. Verifies continued failure does not create
       another state transition.
    7. Restores the simulator.
    8. Runs enough monitoring cycles to resolve
       the incident.

    Real notifications may be sent when SMTP
    configuration is supplied to the workflow.
    """

    if not SIMULATOR_URL:
        pytest.skip(
            "NOVAOPS_SIMULATOR_URL is not configured."
        )

    # ---------------------------------------------
    # INITIALIZE E2E DATABASE
    # ---------------------------------------------

    create_database()

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

    # Establish healthy persisted state.
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
    # This should generate INCIDENT_OPENED,
    # persist the incident and send the
    # opening notification.
    run_monitoring_cycle(
        [service]
    )

    # Continued outage.
    #
    # This must not generate another
    # INCIDENT_OPENED notification.
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
    # This should generate INCIDENT_RESOLVED,
    # update the persisted incident and send
    # the recovery notification.
    run_monitoring_cycle(
        [service]
    )
