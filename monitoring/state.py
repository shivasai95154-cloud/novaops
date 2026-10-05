from dataclasses import dataclass
from enum import Enum


class OperationalState(str, Enum):
    HEALTHY = "HEALTHY"
    SUSPECTED_FAILURE = "SUSPECTED_FAILURE"
    DOWN = "DOWN"
    RECOVERING = "RECOVERING"


class EventType(str, Enum):
    INCIDENT_OPENED = "INCIDENT_OPENED"
    INCIDENT_RESOLVED = "INCIDENT_RESOLVED"


@dataclass
class ServiceState:
    service_name: str

    operational_state: OperationalState = (
        OperationalState.HEALTHY
    )

    consecutive_failures: int = 0
    consecutive_successes: int = 0


@dataclass
class MonitoringEvent:
    service_name: str
    event_type: EventType
    previous_state: OperationalState
    new_state: OperationalState
    message: str
