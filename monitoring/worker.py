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


logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | %(levelname)s | %(message)s"
    ),
)

logger = logging.getLogger("novaops.monitor")


CHECK_INTERVAL_SECONDS = int(
    os.getenv(
        "MONITOR_INTERVAL_SECONDS",
        "30",
    )
)


def run_monitoring_cycle(
    services,
):
    """
    Run one complete monitoring cycle.

    Keeping a single cycle separate from the
    infinite loop makes the worker easier to test.
    """

    session = SessionLocal()

    try:

        for service in services:

            # Load persisted state instead of
            # assuming the service is healthy.
            state = get_or_create_service_state(
                session,
                service.name,
            )

            # Perform the real HTTP observation.
            result = check_service(
                service
            )

            # Process observation through the
            # state-change engine.
            event = process_health_result(
                state,
                result,
            )

            # Persist state after every observation.
            save_service_state(
                session,
                state,
            )

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

            # Only meaningful transitions create
            # monitoring events/incidents.
            if event:

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

    except Exception:

        session.rollback()

        logger.exception(
            "Monitoring cycle failed."
        )

        raise

    finally:

        session.close()


def run_worker():
    """
    Continuously monitor all configured services.
    """

    # Ensure required database tables exist.
    create_database()

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

    while True:

        try:

            run_monitoring_cycle(
                services
            )

        except Exception:

            # A single failed monitoring cycle
            # should not permanently kill the worker.
            logger.exception(
                "Worker cycle failed. "
                "Monitoring will continue."
            )

        time.sleep(
            CHECK_INTERVAL_SECONDS
        )


if __name__ == "__main__":
    run_worker()
