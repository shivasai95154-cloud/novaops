from database.models import IncidentRecord

from monitoring.state import (
    EventType,
    MonitoringEvent,
)

from notifications.email import (
    send_email,
)


def notify_incident_event(
    event: MonitoringEvent,
    incident: IncidentRecord | None,
) -> bool:
    """
    Convert monitoring events into
    human-readable incident notifications.
    """

    if (
        event.event_type
        == EventType.INCIDENT_OPENED
    ):

        incident_number = (
            incident.incident_number
            if incident
            else "UNKNOWN"
        )

        subject = (
            f"🚨 NovaOps Incident "
            f"{incident_number}: "
            f"{event.service_name} DOWN"
        )

        body = f"""
NovaOps detected a confirmed service incident.

Incident: {incident_number}
Service: {event.service_name}
Status: DOWN

Previous State:
{event.previous_state.value}

Current State:
{event.new_state.value}

Details:
{event.message}

NovaOps confirmed this incident only after the configured consecutive failure threshold was reached.

This notification was generated automatically by NovaOps.
""".strip()

        return send_email(
            subject,
            body,
        )

    if (
        event.event_type
        == EventType.INCIDENT_RESOLVED
    ):

        incident_number = (
            incident.incident_number
            if incident
            else "UNKNOWN"
        )

        subject = (
            f"✅ NovaOps Recovery "
            f"{incident_number}: "
            f"{event.service_name}"
        )

        body = f"""
NovaOps detected service recovery.

Incident: {incident_number}
Service: {event.service_name}
Status: RESOLVED

Previous State:
{event.previous_state.value}

Current State:
{event.new_state.value}

Details:
{event.message}

NovaOps confirmed recovery after the configured consecutive successful health checks.

This notification was generated automatically by NovaOps.
""".strip()

        return send_email(
            subject,
            body,
        )

    return False
