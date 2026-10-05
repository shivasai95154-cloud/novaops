from datetime import (
    datetime,
    timezone,
)

from sqlalchemy import select

from database.models import (
    IncidentRecord,
    MonitoringEventRecord,
    ServiceStateRecord,
)

from monitoring.state import (
    EventType,
    MonitoringEvent,
    OperationalState,
    ServiceState,
)


def get_or_create_service_state(
    session,
    service_name: str,
) -> ServiceState:

    record = session.scalar(
        select(ServiceStateRecord).where(
            ServiceStateRecord.service_name
            == service_name
        )
    )

    if record is None:

        record = ServiceStateRecord(
            service_name=service_name,
            operational_state=(
                OperationalState.HEALTHY.value
            ),
        )

        session.add(record)
        session.commit()
        session.refresh(record)

    return ServiceState(
        service_name=record.service_name,
        operational_state=OperationalState(
            record.operational_state
        ),
        consecutive_failures=(
            record.consecutive_failures
        ),
        consecutive_successes=(
            record.consecutive_successes
        ),
    )


def save_service_state(
    session,
    state: ServiceState,
):

    record = session.scalar(
        select(ServiceStateRecord).where(
            ServiceStateRecord.service_name
            == state.service_name
        )
    )

    if record is None:
        record = ServiceStateRecord(
            service_name=state.service_name
        )
        session.add(record)

    record.operational_state = (
        state.operational_state.value
    )

    record.consecutive_failures = (
        state.consecutive_failures
    )

    record.consecutive_successes = (
        state.consecutive_successes
    )

    record.updated_at = datetime.now(
        timezone.utc
    )

    session.commit()


def save_monitoring_event(
    session,
    event: MonitoringEvent,
):

    record = MonitoringEventRecord(
        service_name=event.service_name,
        event_type=event.event_type.value,
        previous_state=(
            event.previous_state.value
        ),
        new_state=event.new_state.value,
        message=event.message,
    )

    session.add(record)
    session.commit()


def open_incident(
    session,
    event: MonitoringEvent,
):

    count = session.query(
        IncidentRecord
    ).count()

    incident_number = (
        f"INC-{count + 1:04d}"
    )

    incident = IncidentRecord(
        incident_number=incident_number,
        service_name=event.service_name,
        status="OPEN",
        summary=event.message,
    )

    session.add(incident)
    session.commit()

    return incident


def resolve_incident(
    session,
    service_name: str,
):

    incident = session.scalar(
        select(IncidentRecord)
        .where(
            IncidentRecord.service_name
            == service_name,
            IncidentRecord.status
            == "OPEN",
        )
        .order_by(
            IncidentRecord.id.desc()
        )
    )

    if incident is None:
        return None

    incident.status = "RESOLVED"

    incident.resolved_at = datetime.now(
        timezone.utc
    )

    session.commit()

    return incident


def handle_monitoring_event(
    session,
    event: MonitoringEvent,
):

    save_monitoring_event(
        session,
        event,
    )

    if (
        event.event_type
        == EventType.INCIDENT_OPENED
    ):

        return open_incident(
            session,
            event,
        )

    if (
        event.event_type
        == EventType.INCIDENT_RESOLVED
    ):

        return resolve_incident(
            session,
            event.service_name,
        )

    return None
