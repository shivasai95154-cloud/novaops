import logging
import os
import time

# Import database models so SQLAlchemy registers
# their tables with Base.metadata.
import database.models  # noqa: F401

from database.connection import (
    SessionLocal,
    create_database,
)

from database.repository import (
    get_or_create_service_state,
    handle_monitoring_event,
    save_service_state,
)

from monitoring.http_checker import check_service
from monitoring.services import get_monitored_services
from monitoring.state_engine import process_health_result

from notifications.incident import (
    notify_incident_event,
)


# =================================================
# LOGGING CONFIGURATION
# =================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | %(levelname)s | %(message)s"
    ),
)

logger = logging.getLogger(
    "novaops.monitor"
)


# =================================================
# MONITORING CONFIGURATION
# =================================================

CHECK_INTERVAL_SECONDS = int(
    os.getenv(
        "MONITOR_INTERVAL_SECONDS",
        "30",
    )
)


# =================================================
# SINGLE MONITORING CYCLE
# =================================================

def run_monitoring_cycle(
    services,
):
    """
    Run one complete monitoring cycle.

    For every configured service:

    1. Load previous state from database.
    2. Perform HTTP health check.
    3. Process result through state engine.
    4. Persist updated state.
    5. Persist incident/event when required.
    6. Send notification for meaningful events.
    """

    session = SessionLocal()

    try:

        for service in services:

            # -------------------------------------
            # LOAD PERSISTED STATE
            # -------------------------------------

            state = get_or_create_service_state(
                session,
                service.name,
            )

            # -------------------------------------
            # PERFORM HTTP HEALTH CHECK
            # -------------------------------------

            result = check_service(
                service
            )

            # -------------------------------------
            # PROCESS STATE TRANSITION
            # -------------------------------------

            event = process_health_result(
                state,
                result,
            )

            # -------------------------------------
            # PERSIST CURRENT STATE
            # -------------------------------------

            save_service_state(
                session,
                state,
            )

            # -------------------------------------
            # LOG CURRENT OBSERVATION
            # -------------------------------------

            logger.info(
                "service=%s "
                "health=%s "
                "operational_state=%s "
                "http=%s "
                "latency_ms=%s "
                "failures=%s "
                "successes=%s",
                service.name,
                result.status.value,
                state.operational_state.value,
                result.status_code,
                result.latency_ms,
                state.consecutive_failures,
                state.consecutive_successes,
            )

            # -------------------------------------
            # HANDLE MEANINGFUL STATE CHANGE
            # -------------------------------------

            if event:

                # Persist monitoring event and
                # open/resolve corresponding incident.
                incident = handle_monitoring_event(
                    session,
                    event,
                )

                logger.warning(
                    "EVENT=%s "
                    "service=%s "
                    "previous=%s "
                    "new=%s "
                    "message=%s",
                    event.event_type.value,
                    event.service_name,
                    event.previous_state.value,
                    event.new_state.value,
                    event.message,
                )

                if incident:

                    logger.warning(
                        "INCIDENT=%s "
                        "status=%s "
                        "service=%s",
                        incident.incident_number,
                        incident.status,
                        incident.service_name,
                    )

                # ---------------------------------
                # SEND INCIDENT NOTIFICATION
                # ---------------------------------
                #
                # Notification happens ONLY when the
                # state engine generates an event.
                #
                # This prevents NovaOps from sending
                # an email every monitoring cycle
                # while a service remains down.

                notification_sent = (
                    notify_incident_event(
                        event,
                        incident,
                    )
                )

                logger.info(
                    "notification_sent=%s "
                    "event=%s "
                    "service=%s",
                    notification_sent,
                    event.event_type.value,
                    event.service_name,
                )

    except Exception:

        session.rollback()

        logger.exception(
            "Monitoring cycle failed."
        )

        raise

    finally:

        session.close()


# =================================================
# PERSISTENT MONITORING WORKER
# =================================================

def run_worker():
    """
    Start the persistent NovaOps monitoring worker.

    The worker continuously:

    - checks configured services
    - evaluates service health
    - tracks consecutive failures
    - tracks consecutive recoveries
    - persists monitoring state
    - creates/resolves incidents
    - sends incident notifications
    """

    # Ensure database tables exist.
    create_database()

    # Load monitored services.
    services = get_monitored_services()

    if not services:

        logger.error(
            "No monitored services configured. "
            "Set NOVAOPS_SIMULATOR_URL."
        )

        return

    logger.info(
        "NovaOps persistent monitoring worker started."
    )

    logger.info(
        "Monitoring %s service(s) every %s seconds.",
        len(services),
        CHECK_INTERVAL_SECONDS,
    )

    # ---------------------------------------------
    # CONTINUOUS MONITORING LOOP
    # ---------------------------------------------

    while True:

        try:

            run_monitoring_cycle(
                services
            )

        except Exception:

            # One monitoring-cycle failure should
            # not permanently terminate NovaOps.
            logger.exception(
                "Worker cycle failed. "
                "Monitoring will continue."
            )

        time.sleep(
            CHECK_INTERVAL_SECONDS
        )


# =================================================
# APPLICATION ENTRY POINT
# =================================================

if __name__ == "__main__":
    run_worker()
