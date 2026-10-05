import logging
import os
import signal
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
# LOGGING
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
# CONFIGURATION
# =================================================

CHECK_INTERVAL_SECONDS = int(
    os.getenv(
        "MONITOR_INTERVAL_SECONDS",
        "30",
    )
)


# =================================================
# WORKER LIFECYCLE
# =================================================

shutdown_requested = False


def request_shutdown(
    signum,
    frame,
):
    """
    Request a graceful worker shutdown.

    Deployment platforms commonly send
    SIGTERM before stopping a process.
    """

    del frame

    global shutdown_requested

    shutdown_requested = True

    logger.info(
        "Shutdown requested. signal=%s",
        signum,
    )


def install_signal_handlers():
    """
    Install operating-system signal handlers
    used by the continuous worker.
    """

    signal.signal(
        signal.SIGTERM,
        request_shutdown,
    )

    signal.signal(
        signal.SIGINT,
        request_shutdown,
    )


# =================================================
# SINGLE MONITORING CYCLE
# =================================================

def run_monitoring_cycle(
    services,
):
    """
    Run one complete monitoring cycle across
    all configured services.
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
            # HEALTH CHECK
            # -------------------------------------

            result = check_service(
                service
            )

            # -------------------------------------
            # STATE ENGINE
            # -------------------------------------

            event = process_health_result(
                state,
                result,
            )

            # -------------------------------------
            # PERSIST STATE
            # -------------------------------------

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

            # -------------------------------------
            # INCIDENT EVENT
            # -------------------------------------

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

                # ---------------------------------
                # NOTIFICATION
                # ---------------------------------

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
# CONTINUOUS WORKER
# =================================================

def run_worker():
    """
    Start NovaOps continuous monitoring.

    Startup sequence:

    1. Initialize database.
    2. Validate/load service configuration.
    3. Install shutdown handlers.
    4. Continuously monitor services.
    5. Exit cleanly when termination is requested.
    """

    global shutdown_requested

    shutdown_requested = False

    logger.info(
        "Starting NovaOps monitoring worker."
    )

    # ---------------------------------------------
    # DATABASE INITIALIZATION
    # ---------------------------------------------

    create_database()

    # ---------------------------------------------
    # SERVICE CONFIGURATION
    # ---------------------------------------------

    services = get_monitored_services()

    if not services:

        logger.error(
            "No monitored services configured. "
            "Worker cannot start."
        )

        return

    # ---------------------------------------------
    # SIGNAL HANDLERS
    # ---------------------------------------------

    install_signal_handlers()

    logger.info(
        "NovaOps worker started. "
        "services=%s interval_seconds=%s",
        len(services),
        CHECK_INTERVAL_SECONDS,
    )

    # ---------------------------------------------
    # CONTINUOUS MONITORING LOOP
    # ---------------------------------------------

    while not shutdown_requested:

        cycle_started = time.monotonic()

        try:

            run_monitoring_cycle(
                services
            )

        except Exception:

            # One failed cycle must not permanently
            # terminate the monitoring process.
            logger.exception(
                "Worker cycle failed. "
                "Monitoring will continue."
            )

        cycle_duration = (
            time.monotonic()
            - cycle_started
        )

        sleep_seconds = max(
            0,
            CHECK_INTERVAL_SECONDS
            - cycle_duration,
        )

        logger.info(
            "Monitoring cycle completed. "
            "duration_seconds=%.2f "
            "next_check_seconds=%.2f",
            cycle_duration,
            sleep_seconds,
        )

        # Sleep in short increments so SIGTERM/SIGINT
        # can stop the worker promptly instead of
        # waiting for the entire monitoring interval.
        sleep_remaining = sleep_seconds

        while (
            sleep_remaining > 0
            and not shutdown_requested
        ):

            sleep_chunk = min(
                1.0,
                sleep_remaining,
            )

            time.sleep(
                sleep_chunk
            )

            sleep_remaining -= sleep_chunk

    logger.info(
        "NovaOps monitoring worker stopped cleanly."
    )


# =================================================
# ENTRY POINT
# =================================================

if __name__ == "__main__":
    run_worker()
