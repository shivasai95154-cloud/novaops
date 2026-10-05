from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from database.models import (
    IncidentRecord,
    MonitoringEventRecord,
    ServiceStateRecord,
)
from database.repository import (
    get_or_create_service_state,
    handle_monitoring_event,
    save_service_state,
)
from monitoring.models import (
    HealthCheckResult,
    HealthStatus,
)
from monitoring.state import (
    OperationalState,
)
from monitoring.state_engine import (
    process_health_result,
)


def create_test_session():
    """
    Create an isolated in-memory SQLite database.

    Nothing from these tests is written to the
    real NovaOps database.
    """

    engine = create_engine(
        "sqlite:///:memory:"
    )

    Base.metadata.create_all(engine)

    TestSession = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    return TestSession()


def make_result(status):
    return HealthCheckResult(
        service_name="Test Service",
        status=status,
        status_code=(
            200
            if status == HealthStatus.HEALTHY
            else 503
        ),
        latency_ms=50,
        message="test observation",
    )


def process_and_persist(
    session,
    state,
    status,
):
    """
    Process one health observation and persist
    both state and any resulting event.
    """

    event = process_health_result(
        state,
        make_result(status),
    )

    save_service_state(
        session,
        state,
    )

    if event:
        handle_monitoring_event(
            session,
            event,
        )

    return event


def test_service_state_is_persisted():

    session = create_test_session()

    state = get_or_create_service_state(
        session,
        "Test Service",
    )

    process_and_persist(
        session,
        state,
        HealthStatus.UNHEALTHY,
    )

    # Simulate forgetting the in-memory object
    # and loading state again from the database.

    restored_state = (
        get_or_create_service_state(
            session,
            "Test Service",
        )
    )

    assert (
        restored_state.operational_state
        == OperationalState.SUSPECTED_FAILURE
    )

    assert (
        restored_state.consecutive_failures
        == 1
    )

    session.close()


def test_confirmed_failure_creates_one_incident():

    session = create_test_session()

    state = get_or_create_service_state(
        session,
        "Test Service",
    )

    for _ in range(3):
        process_and_persist(
            session,
            state,
            HealthStatus.UNHEALTHY,
        )

    incidents = session.scalars(
        select(IncidentRecord)
    ).all()

    assert len(incidents) == 1

    assert incidents[0].status == "OPEN"

    assert (
        incidents[0].service_name
        == "Test Service"
    )

    session.close()


def test_continued_failure_does_not_duplicate_incident():

    session = create_test_session()

    state = get_or_create_service_state(
        session,
        "Test Service",
    )

    # Confirm outage.
    for _ in range(3):
        process_and_persist(
            session,
            state,
            HealthStatus.UNHEALTHY,
        )

    # Continue receiving failed checks.
    for _ in range(5):
        process_and_persist(
            session,
            state,
            HealthStatus.UNHEALTHY,
        )

    incidents = session.scalars(
        select(IncidentRecord)
    ).all()

    assert len(incidents) == 1

    assert incidents[0].status == "OPEN"

    session.close()


def test_recovery_resolves_existing_incident():

    session = create_test_session()

    state = get_or_create_service_state(
        session,
        "Test Service",
    )

    # Open incident.
    for _ in range(3):
        process_and_persist(
            session,
            state,
            HealthStatus.UNHEALTHY,
        )

    # Confirm recovery.
    for _ in range(2):
        process_and_persist(
            session,
            state,
            HealthStatus.HEALTHY,
        )

    incidents = session.scalars(
        select(IncidentRecord)
    ).all()

    assert len(incidents) == 1

    incident = incidents[0]

    assert incident.status == "RESOLVED"

    assert incident.resolved_at is not None

    assert (
        state.operational_state
        == OperationalState.HEALTHY
    )

    session.close()


def test_monitoring_events_are_auditable():

    session = create_test_session()

    state = get_or_create_service_state(
        session,
        "Test Service",
    )

    # Open incident.
    for _ in range(3):
        process_and_persist(
            session,
            state,
            HealthStatus.UNHEALTHY,
        )

    # Recover.
    for _ in range(2):
        process_and_persist(
            session,
            state,
            HealthStatus.HEALTHY,
        )

    events = session.scalars(
        select(MonitoringEventRecord).order_by(
            MonitoringEventRecord.id
        )
    ).all()

    assert len(events) == 2

    assert (
        events[0].event_type
        == "INCIDENT_OPENED"
    )

    assert (
        events[1].event_type
        == "INCIDENT_RESOLVED"
    )

    session.close()


def test_service_state_record_is_unique():

    session = create_test_session()

    get_or_create_service_state(
        session,
        "Test Service",
    )

    get_or_create_service_state(
        session,
        "Test Service",
    )

    records = session.scalars(
        select(ServiceStateRecord)
    ).all()

    assert len(records) == 1

    session.close()
