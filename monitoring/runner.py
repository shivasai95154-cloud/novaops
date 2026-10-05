from monitoring.http_checker import (
    check_service,
)
from monitoring.services import (
    get_monitored_services,
)


def run_monitoring_cycle():

    services = get_monitored_services()

    if not services:

        print(
            "No monitored services configured."
        )

        return []


    results = []


    for service in services:

        result = check_service(
            service
        )

        results.append(
            result
        )


        print(
            f"{result.service_name} | "
            f"{result.status.value} | "
            f"HTTP={result.status_code} | "
            f"Latency={result.latency_ms}ms | "
            f"{result.message}"
        )


    return results


if __name__ == "__main__":

    run_monitoring_cycle()
