import json
import logging
import os

from monitoring.models import ServiceConfig


logger = logging.getLogger(
    "novaops.services"
)


DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_LATENCY_THRESHOLD_MS = 2000


def _service_from_dict(data):
    """
    Convert one configuration dictionary
    into a ServiceConfig object.
    """

    name = data.get("name")
    health_url = data.get("health_url")

    if not name:
        raise ValueError(
            "Monitored service requires a name."
        )

    if not health_url:
        raise ValueError(
            f"Service '{name}' requires a health_url."
        )

    return ServiceConfig(
        name=name,
        health_url=health_url,
        timeout_seconds=int(
            data.get(
                "timeout_seconds",
                DEFAULT_TIMEOUT_SECONDS,
            )
        ),
        latency_threshold_ms=int(
            data.get(
                "latency_threshold_ms",
                DEFAULT_LATENCY_THRESHOLD_MS,
            )
        ),
    )


def get_monitored_services():
    """
    Load services monitored by NovaOps.

    Preferred configuration:

        NOVAOPS_SERVICES_JSON

    Example:

        [
          {
            "name": "NovaOps DEV Simulator",
            "health_url":
              "https://example.onrender.com/health"
          }
        ]

    Backward compatibility:

        NOVAOPS_SIMULATOR_URL

    If NOVAOPS_SERVICES_JSON is configured,
    NovaOps can monitor multiple services
    without changing Python source code.
    """

    services_json = os.getenv(
        "NOVAOPS_SERVICES_JSON"
    )

    if services_json:

        try:
            raw_services = json.loads(
                services_json
            )

        except json.JSONDecodeError as exc:
            raise ValueError(
                "NOVAOPS_SERVICES_JSON contains "
                "invalid JSON."
            ) from exc

        if not isinstance(
            raw_services,
            list,
        ):
            raise ValueError(
                "NOVAOPS_SERVICES_JSON must "
                "contain a JSON array."
            )

        services = [
            _service_from_dict(service)
            for service in raw_services
        ]

        logger.info(
            "Loaded %s monitored service(s) "
            "from NOVAOPS_SERVICES_JSON.",
            len(services),
        )

        return services

    # ---------------------------------------------
    # BACKWARD-COMPATIBLE DEV CONFIGURATION
    # ---------------------------------------------

    simulator_url = os.getenv(
        "NOVAOPS_SIMULATOR_URL"
    )

    if simulator_url:

        simulator_url = (
            simulator_url.rstrip("/")
        )

        logger.info(
            "Using NOVAOPS_SIMULATOR_URL "
            "fallback configuration."
        )

        return [
            ServiceConfig(
                name="NovaOps DEV Simulator",
                health_url=(
                    f"{simulator_url}/health"
                ),
                timeout_seconds=30,
                latency_threshold_ms=5000,
            )
        ]

    logger.warning(
        "No monitored services configured."
    )

    return []
