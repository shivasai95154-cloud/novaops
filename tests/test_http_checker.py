from unittest.mock import Mock, patch

import httpx

from monitoring.http_checker import check_service
from monitoring.models import (
    HealthStatus,
    ServiceConfig,
)


def create_service(
    latency_threshold_ms=1000.0,
):
    """
    Create a standard service configuration
    used by monitoring tests.
    """

    return ServiceConfig(
        name="Test Service",
        health_url="https://example.com/health",
        timeout_seconds=5.0,
        latency_threshold_ms=latency_threshold_ms,
    )


# -------------------------------------------------
# HEALTHY
# -------------------------------------------------

@patch("monitoring.http_checker.httpx.get")
def test_healthy_service(mock_get):

    mock_response = Mock()
    mock_response.status_code = 200

    mock_get.return_value = mock_response

    service = create_service(
        latency_threshold_ms=10000
    )

    result = check_service(service)

    assert result.status == HealthStatus.HEALTHY
    assert result.status_code == 200
    assert result.latency_ms is not None
    assert result.message == "Service is healthy."


# -------------------------------------------------
# DEGRADED
# -------------------------------------------------

@patch("monitoring.http_checker.time.perf_counter")
@patch("monitoring.http_checker.httpx.get")
def test_slow_service_is_degraded(
    mock_get,
    mock_perf_counter,
):

    mock_response = Mock()
    mock_response.status_code = 200

    mock_get.return_value = mock_response

    # First call = request start
    # Second call = request finish
    # Difference = 2 seconds = 2000 ms
    mock_perf_counter.side_effect = [
        100.0,
        102.0,
    ]

    service = create_service(
        latency_threshold_ms=1000
    )

    result = check_service(service)

    assert result.status == HealthStatus.DEGRADED
    assert result.status_code == 200
    assert result.latency_ms == 2000.0


# -------------------------------------------------
# HTTP 503
# -------------------------------------------------

@patch("monitoring.http_checker.httpx.get")
def test_503_service_is_unhealthy(
    mock_get,
):

    mock_response = Mock()
    mock_response.status_code = 503

    mock_get.return_value = mock_response

    service = create_service()

    result = check_service(service)

    assert result.status == HealthStatus.UNHEALTHY
    assert result.status_code == 503


# -------------------------------------------------
# TIMEOUT
# -------------------------------------------------

@patch("monitoring.http_checker.httpx.get")
def test_timeout_service_is_down(
    mock_get,
):

    mock_get.side_effect = (
        httpx.TimeoutException(
            "Request timed out"
        )
    )

    service = create_service()

    result = check_service(service)

    assert result.status == HealthStatus.DOWN
    assert result.status_code is None

    assert (
        result.message
        == "Health check timed out."
    )


# -------------------------------------------------
# CONNECTION FAILURE
# -------------------------------------------------

@patch("monitoring.http_checker.httpx.get")
def test_connection_failure_is_down(
    mock_get,
):

    request = httpx.Request(
        "GET",
        "https://example.com/health",
    )

    mock_get.side_effect = (
        httpx.ConnectError(
            "Connection refused",
            request=request,
        )
    )

    service = create_service()

    result = check_service(service)

    assert result.status == HealthStatus.DOWN
    assert result.status_code is None

    assert "ConnectError" in result.message
