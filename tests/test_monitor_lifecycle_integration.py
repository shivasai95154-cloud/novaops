import os

import httpx
import pytest

from monitoring.http_checker import check_service
from monitoring.models import (
    HealthStatus,
    ServiceConfig,
)


SIMULATOR_URL = os.getenv("NOVAOPS_SIMULATOR_URL")


@pytest.mark.integration
def test_real_monitoring_lifecycle():
    """
    Full DEV integration lifecycle:

    HEALTHY
       ->
    FAILURE
       ->
    NovaOps detects UNHEALTHY
       ->
    RECOVERY
       ->
    NovaOps detects HEALTHY
    """

    if not SIMULATOR_URL:
        pytest.skip(
            "NOVAOPS_SIMULATOR_URL is not configured."
        )

    base_url = SIMULATOR_URL.rstrip("/")

    service = ServiceConfig(
        name="NovaOps DEV Simulator",
        health_url=f"{base_url}/health",
        timeout_seconds=60.0,
        latency_threshold_ms=60000.0,
    )

    # Always attempt recovery at the end,
    # even if an assertion fails.
    try:

        # -----------------------------------------
        # STEP 1: FORCE KNOWN HEALTHY STATE
        # -----------------------------------------

        recovery_response = httpx.post(
            f"{base_url}/test/recovery",
            timeout=60.0,
        )

        assert recovery_response.status_code == 200

        healthy_result = check_service(service)

        print(
            "\nINITIAL CHECK:"
            f"\nStatus: {healthy_result.status.value}"
            f"\nHTTP: {healthy_result.status_code}"
        )

        assert (
            healthy_result.status
            == HealthStatus.HEALTHY
        )

        assert healthy_result.status_code == 200

        # -----------------------------------------
        # STEP 2: CREATE REAL DEV FAILURE
        # -----------------------------------------

        failure_response = httpx.post(
            f"{base_url}/test/failure",
            timeout=60.0,
        )

        assert failure_response.status_code == 200

        # -----------------------------------------
        # STEP 3: MONITOR MUST DISCOVER FAILURE
        # -----------------------------------------

        outage_result = check_service(service)

        print(
            "\nOUTAGE CHECK:"
            f"\nStatus: {outage_result.status.value}"
            f"\nHTTP: {outage_result.status_code}"
        )

        assert (
            outage_result.status
            == HealthStatus.UNHEALTHY
        )

        assert outage_result.status_code == 503

        # -----------------------------------------
        # STEP 4: RECOVER SERVICE
        # -----------------------------------------

        recovery_response = httpx.post(
            f"{base_url}/test/recovery",
            timeout=60.0,
        )

        assert recovery_response.status_code == 200

        # -----------------------------------------
        # STEP 5: MONITOR MUST DISCOVER RECOVERY
        # -----------------------------------------

        recovered_result = check_service(service)

        print(
            "\nRECOVERY CHECK:"
            f"\nStatus: {recovered_result.status.value}"
            f"\nHTTP: {recovered_result.status_code}"
        )

        assert (
            recovered_result.status
            == HealthStatus.HEALTHY
        )

        assert recovered_result.status_code == 200

    finally:

        # Safety cleanup:
        # leave DEV simulator healthy even when
        # the test fails halfway through.

        try:
            httpx.post(
                f"{base_url}/test/recovery",
                timeout=60.0,
            )

        except httpx.RequestError:
            pass
