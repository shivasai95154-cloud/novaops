from unittest.mock import patch

from sqlalchemy import select

from database.connection import (
    Base,
    SessionLocal,
    engine,
)
from database.models import (
    IncidentRecord,
    ServiceStateRecord,
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
    name="Worker Test Service",
    health_url="https://example.com/health",
    timeout_seconds=5,
    latency_threshold_ms=1000,
)


def make_result(status):

    return HealthCheckResult(
        service_name="Worker Test Service",
        status=status,
        status_code=(
            200
            if status == HealthStatus.HEALTHY
            else 503
        ),
        latency_ms=50,
        message="worker test",
    )


def reset_database():

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


@patch(
    "monitoring.worker.check_service"
)
def test_worker_persists_failure_across_cycles(
    mock_check,
):

    reset_database()

    mock_check.return_value = make_result(
        HealthStatus.UNHEALTHY
    )

    # Each call represents a separate monitoring cycle.
    run_monitoring_cycle([TEST_SERVICE])
    run_monitoring_cycle([TEST_SERVICE])
    run_monitoring_cycle([TEST_SERVICE])

    session = SessionLocal()

    try:

        state = session.scalar(
            select(ServiceStateRecord).where(
                ServiceStateRecord.service_name
                == "Worker Test Service"
            )
        )

        incidents = session.scalars(
            select(IncidentRecord)
        ).all()

        assert state is not None

        assert (
            state.operational_state
            == "DOWN"
        )

        assert (
            state.consecutive_failures
            == 3
        )

        assert len(incidents) == 1

        assert (
            incidents[0].status
            == "OPEN"
        )

    finally:

        session.close()


@patch(
    "monitoring.worker.check_service"
)
def test_worker_persists_recovery(
    mock_check,
):

    reset_database()

    # First establish a confirmed outage.
    mock_check.return_value = make_result(
        HealthStatus.UNHEALTHY
    )

    for _ in range(3):
        run_monitoring_cycle(
            [TEST_SERVICE]
        )

    # Then simulate recovery.
    mock_check.return_value = make_result(
        HealthStatus.HEALTHY
    )

    run_monitoring_cycle(
        [TEST_SERVICE]
    )

    run_monitoring_cycle(
        [TEST_SERVICE]
    )

    session = SessionLocal()

    try:

        state = session.scalar(
            select(ServiceStateRecord).where(
                ServiceStateRecord.service_name
                == "Worker Test Service"
            )
        )

        incident = session.scalar(
            select(IncidentRecord)
        )

        assert (
            state.operational_state
            == "HEALTHY"
        )

        assert incident.status == "RESOLVED"

        assert incident.resolved_at is not None

    finally:

        session.close()
