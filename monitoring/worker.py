import logging
import os
import time

from monitoring.http_checker import check_service
from monitoring.services import get_monitored_services
from monitoring.state import ServiceState
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


def run_worker():
    """
    Continuously monitor all configured services.

    The worker:
    - performs real HTTP checks
    - maintains service state
    - detects confirmed failures
    - detects confirmed recoveries
    - emits monitoring events

    Incident persistence and notifications
    are handled by later NovaOps components.
    """

    services = get_monitored_services()

    if not services:
        logger.error(
            "No monitored services configured. "
            "Set NOVAOPS_SIMULATOR_URL."
        )
        return

    states = {
        service.name: ServiceState(
            service_name=service.name
        )
        for service in services
    }

    logger.info(
        "NovaOps monitoring worker started."
    )

    logger.info(
        "Monitoring %s service(s) every %s seconds.",
        len(services),
        CHECK_INTERVAL_SECONDS,
    )

    while True:

        for service in services:

            result = check_service(service)

            state = states[service.name]

            event = process_health_result(
                state,
                result,
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

            if event:

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

        time.sleep(
            CHECK_INTERVAL_SECONDS
        )


if __name__ == "__main__":
    run_worker()
