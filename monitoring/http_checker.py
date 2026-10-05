import time

import httpx

from monitoring.models import (
    HealthCheckResult,
    HealthStatus,
    ServiceConfig,
)


def check_service(
    service: ServiceConfig,
) -> HealthCheckResult:
    """
    Perform one real HTTP health check.

    This function only observes and classifies
    service health.

    It does NOT:
    - create incidents
    - call an LLM
    - send notifications
    - restart services
    """

    start_time = time.perf_counter()

    try:
        response = httpx.get(
            str(service.health_url),
            timeout=service.timeout_seconds,
            follow_redirects=True,
        )

        latency_ms = (
            time.perf_counter() - start_time
        ) * 1000


        # -----------------------------------------
        # HTTP 5XX
        # -----------------------------------------

        if 500 <= response.status_code <= 599:

            return HealthCheckResult(
                service_name=service.name,
                status=HealthStatus.UNHEALTHY,
                status_code=response.status_code,
                latency_ms=round(latency_ms, 2),
                message=(
                    "Service returned a server error."
                ),
            )


        # -----------------------------------------
        # OTHER NON-2XX RESPONSES
        # -----------------------------------------

        if not 200 <= response.status_code <= 299:

            return HealthCheckResult(
                service_name=service.name,
                status=HealthStatus.UNHEALTHY,
                status_code=response.status_code,
                latency_ms=round(latency_ms, 2),
                message=(
                    "Service returned an unexpected "
                    "HTTP status."
                ),
            )


        # -----------------------------------------
        # HIGH LATENCY
        # -----------------------------------------

        if (
            latency_ms
            > service.latency_threshold_ms
        ):

            return HealthCheckResult(
                service_name=service.name,
                status=HealthStatus.DEGRADED,
                status_code=response.status_code,
                latency_ms=round(latency_ms, 2),
                message=(
                    "Service responded successfully "
                    "but exceeded the configured "
                    "latency threshold."
                ),
            )


        # -----------------------------------------
        # HEALTHY
        # -----------------------------------------

        return HealthCheckResult(
            service_name=service.name,
            status=HealthStatus.HEALTHY,
            status_code=response.status_code,
            latency_ms=round(latency_ms, 2),
            message="Service is healthy.",
        )


    # ---------------------------------------------
    # TIMEOUT
    # ---------------------------------------------

    except httpx.TimeoutException:

        latency_ms = (
            time.perf_counter() - start_time
        ) * 1000

        return HealthCheckResult(
            service_name=service.name,
            status=HealthStatus.DOWN,
            status_code=None,
            latency_ms=round(latency_ms, 2),
            message=(
                "Health check timed out."
            ),
        )


    # ---------------------------------------------
    # NETWORK / DNS / CONNECTION FAILURE
    # ---------------------------------------------

    except httpx.RequestError as error:

        latency_ms = (
            time.perf_counter() - start_time
        ) * 1000

        return HealthCheckResult(
            service_name=service.name,
            status=HealthStatus.DOWN,
            status_code=None,
            latency_ms=round(latency_ms, 2),
            message=(
                f"Health check request failed: "
                f"{type(error).__name__}"
            ),
        )
