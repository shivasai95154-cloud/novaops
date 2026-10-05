from unittest.mock import patch

from monitoring.state import (
    EventType,
    MonitoringEvent,
    OperationalState,
)

from notifications.incident import (
    notify_incident_event,
)


class FakeIncident:

    incident_number = "INC-0001"


def opened_event():

    return MonitoringEvent(
        service_name="Test API",
        event_type=EventType.INCIDENT_OPENED,
        previous_state=(
            OperationalState.SUSPECTED_FAILURE
        ),
        new_state=OperationalState.DOWN,
        message=(
            "Test API confirmed DOWN after "
            "3 consecutive failed checks."
        ),
    )


def resolved_event():

    return MonitoringEvent(
        service_name="Test API",
        event_type=EventType.INCIDENT_RESOLVED,
        previous_state=(
            OperationalState.RECOVERING
        ),
        new_state=OperationalState.HEALTHY,
        message=(
            "Test API recovered after "
            "2 consecutive successful checks."
        ),
    )


@patch(
    "notifications.incident.send_email"
)
def test_incident_open_sends_notification(
    mock_send,
):

    mock_send.return_value = True

    result = notify_incident_event(
        opened_event(),
        FakeIncident(),
    )

    assert result is True

    mock_send.assert_called_once()

    subject, body = (
        mock_send.call_args.args
    )

    assert "INC-0001" in subject
    assert "DOWN" in subject
    assert "Test API" in body


@patch(
    "notifications.incident.send_email"
)
def test_incident_resolution_sends_notification(
    mock_send,
):

    mock_send.return_value = True

    result = notify_incident_event(
        resolved_event(),
        FakeIncident(),
    )

    assert result is True

    mock_send.assert_called_once()

    subject, body = (
        mock_send.call_args.args
    )

    assert "Recovery" in subject
    assert "INC-0001" in subject
    assert "RESOLVED" in body


@patch(
    "notifications.incident.send_email"
)
def test_notification_failure_does_not_raise(
    mock_send,
):

    mock_send.return_value = False

    result = notify_incident_event(
        opened_event(),
        FakeIncident(),
    )

    assert result is False
