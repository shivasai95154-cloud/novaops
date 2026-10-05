from monitoring.models import (
    HealthCheckResult,
    HealthStatus,
)

from monitoring.state import (
    EventType,
    OperationalState,
    ServiceState,
)

from monitoring.state_engine import (
    process_health_result,
)


def result(status):
    return HealthCheckResult(
        service_name="Test Service",
        status=status,
        status_code=(
            200
            if status == HealthStatus.HEALTHY
            else 503
        ),
        latency_ms=50,
        message="test",
    )


def test_single_failure_does_not_open_incident():

    state = ServiceState(
        service_name="Test Service"
    )

    event = process_health_result(
        state,
        result(HealthStatus.UNHEALTHY),
    )

    assert event is None

    assert (
        state.operational_state
        == OperationalState.SUSPECTED_FAILURE
    )

    assert state.consecutive_failures == 1


def test_three_failures_open_incident_once():

    state = ServiceState(
        service_name="Test Service"
    )

    first = process_health_result(
        state,
        result(HealthStatus.UNHEALTHY),
    )

    second = process_health_result(
        state,
        result(HealthStatus.UNHEALTHY),
    )

    third = process_health_result(
        state,
        result(HealthStatus.UNHEALTHY),
    )

    assert first is None
    assert second is None

    assert third is not None

    assert (
        third.event_type
        == EventType.INCIDENT_OPENED
    )

    assert (
        state.operational_state
        == OperationalState.DOWN
    )


def test_continued_failure_does_not_duplicate_incident():

    state = ServiceState(
        service_name="Test Service"
    )

    for _ in range(3):
        process_health_result(
            state,
            result(HealthStatus.UNHEALTHY),
        )

    duplicate_event = process_health_result(
        state,
        result(HealthStatus.UNHEALTHY),
    )

    assert duplicate_event is None

    assert (
        state.operational_state
        == OperationalState.DOWN
    )


def test_suspected_failure_can_self_recover():

    state = ServiceState(
        service_name="Test Service"
    )

    process_health_result(
        state,
        result(HealthStatus.UNHEALTHY),
    )

    event = process_health_result(
        state,
        result(HealthStatus.HEALTHY),
    )

    assert event is None

    assert (
        state.operational_state
        == OperationalState.HEALTHY
    )

    assert state.consecutive_failures == 0


def test_two_successes_resolve_confirmed_incident():

    state = ServiceState(
        service_name="Test Service"
    )

    # Confirm outage.
    for _ in range(3):
        process_health_result(
            state,
            result(HealthStatus.UNHEALTHY),
        )

    first_recovery = process_health_result(
        state,
        result(HealthStatus.HEALTHY),
    )

    assert first_recovery is None

    assert (
        state.operational_state
        == OperationalState.RECOVERING
    )

    second_recovery = process_health_result(
        state,
        result(HealthStatus.HEALTHY),
    )

    assert second_recovery is not None

    assert (
        second_recovery.event_type
        == EventType.INCIDENT_RESOLVED
    )

    assert (
        state.operational_state
        == OperationalState.HEALTHY
    )
