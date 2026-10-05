from unittest.mock import patch

from database.connection import (
    Base,
    engine,
)

from monitoring.models import (
    HealthCheckResult,
    HealthStatus,
    ServiceConfig,
)

from monitoring.worker import (
    run_monitoring_cycle,
)


TEST_SERVICE = ServiceConfig(
    name="Notification Test Service",
    health_url="https://example.com/health",
    timeout_seconds=5,
    latency_threshold_ms=1000,
)


def make_result(status):

    return HealthCheckResult(
        service_name="Notification Test Service",
        status=status,
        status_code=(
            200
            if status == HealthStatus.HEALTHY
            else 503
        ),
        latency_ms=50,
        message="notification integration test",
    )


def reset_database():

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


@patch(
    "monitoring.worker.notify_incident_event"
)
@patch(
    "monitoring.worker.check_service"
)
def test_worker_sends_one_open_notification(
    mock_check,
    mock_notify,
):

    reset_database()

    mock_notify.return_value = True

    mock_check.return_value = make_result(
        HealthStatus.UNHEALTHY
    )

    # Failure #1
    run_monitoring_cycle([TEST_SERVICE])

    # Failure #2
    run_monitoring_cycle([TEST_SERVICE])

    assert mock_notify.call_count == 0

    # Failure #3 confirms incident.
    run_monitoring_cycle([TEST_SERVICE])

    assert mock_notify.call_count == 1

    event = mock_notify.call_args.args[0]

    assert (
        event.event_type.value
        == "INCIDENT_OPENED"
    )

    # Continued outage must NOT generate
    # another notification.
    run_monitoring_cycle([TEST_SERVICE])

    assert mock_notify.call_count == 1


@patch(
    "monitoring.worker.notify_incident_event"
)
@patch(
    "monitoring.worker.check_service"
)
def test_worker_sends_recovery_notification(
    mock_check,
    mock_notify,
):

    reset_database()

    mock_notify.return_value = True

    # Confirm outage first.
    mock_check.return_value = make_result(
        HealthStatus.UNHEALTHY
    )

    for _ in range(3):
        run_monitoring_cycle(
            [TEST_SERVICE]
        )

    assert mock_notify.call_count == 1

    # Recovery observation #1.
    mock_check.return_value = make_result(
        HealthStatus.HEALTHY
    )

    run_monitoring_cycle(
        [TEST_SERVICE]
    )

    # Still only the opening notification.
    assert mock_notify.call_count == 1

    # Recovery observation #2 confirms recovery.
    run_monitoring_cycle(
        [TEST_SERVICE]
    )

    assert mock_notify.call_count == 2

    recovery_event = (
        mock_notify.call_args.args[0]
    )

    assert (
        recovery_event.event_type.value
        == "INCIDENT_RESOLVED"
    )
