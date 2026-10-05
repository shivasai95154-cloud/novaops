from monitoring.models import (
    HealthCheckResult,
    HealthStatus,
)

from monitoring.state import (
    EventType,
    MonitoringEvent,
    OperationalState,
    ServiceState,
)


FAILURE_THRESHOLD = 3
RECOVERY_THRESHOLD = 2


def process_health_result(
    state: ServiceState,
    result: HealthCheckResult,
) -> MonitoringEvent | None:

    is_failure = result.status in {
        HealthStatus.UNHEALTHY,
        HealthStatus.DOWN,
    }

    is_success = result.status in {
        HealthStatus.HEALTHY,
        HealthStatus.DEGRADED,
    }

    # ---------------------------------------------
    # FAILURE OBSERVATION
    # ---------------------------------------------

    if is_failure:

        state.consecutive_failures += 1
        state.consecutive_successes = 0

        # Already confirmed down.
        if (
            state.operational_state
            == OperationalState.DOWN
        ):
            return None

        # Failure observed but threshold not reached.
        if (
            state.consecutive_failures
            < FAILURE_THRESHOLD
        ):
            state.operational_state = (
                OperationalState.SUSPECTED_FAILURE
            )

            return None

        # Failure threshold reached.
        previous_state = state.operational_state

        state.operational_state = (
            OperationalState.DOWN
        )

        return MonitoringEvent(
            service_name=state.service_name,
            event_type=EventType.INCIDENT_OPENED,
            previous_state=previous_state,
            new_state=OperationalState.DOWN,
            message=(
                f"{state.service_name} confirmed DOWN "
                f"after {FAILURE_THRESHOLD} "
                f"consecutive failed checks."
            ),
        )

    # ---------------------------------------------
    # SUCCESS OBSERVATION
    # ---------------------------------------------

    if is_success:

        state.consecutive_successes += 1
        state.consecutive_failures = 0

        # Service has never entered a failure state.
        if (
            state.operational_state
            == OperationalState.HEALTHY
        ):
            return None

        # A suspected failure recovered before an
        # incident was confirmed.
        if (
            state.operational_state
            == OperationalState.SUSPECTED_FAILURE
        ):
            state.operational_state = (
                OperationalState.HEALTHY
            )

            state.consecutive_successes = 0

            return None

        # Confirmed outage is showing signs
        # of recovery.
        if (
            state.operational_state
            == OperationalState.DOWN
        ):
            state.operational_state = (
                OperationalState.RECOVERING
            )

        # Recovery has not yet been confirmed.
        if (
            state.consecutive_successes
            < RECOVERY_THRESHOLD
        ):
            return None

        previous_state = state.operational_state

        state.operational_state = (
            OperationalState.HEALTHY
        )

        state.consecutive_successes = 0

        return MonitoringEvent(
            service_name=state.service_name,
            event_type=EventType.INCIDENT_RESOLVED,
            previous_state=previous_state,
            new_state=OperationalState.HEALTHY,
            message=(
                f"{state.service_name} recovered "
                f"after {RECOVERY_THRESHOLD} "
                f"consecutive successful checks."
            ),
        )

    return None
