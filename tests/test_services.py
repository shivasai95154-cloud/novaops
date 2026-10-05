import json

import pytest

from monitoring.services import (
    get_monitored_services,
)


def test_no_configuration_returns_empty_list(
    monkeypatch,
):
    """
    No service configuration should produce
    an empty service list.
    """

    monkeypatch.delenv(
        "NOVAOPS_SERVICES_JSON",
        raising=False,
    )

    monkeypatch.delenv(
        "NOVAOPS_SIMULATOR_URL",
        raising=False,
    )

    services = get_monitored_services()

    assert services == []


def test_simulator_url_fallback(
    monkeypatch,
):
    """
    Existing NOVAOPS_SIMULATOR_URL configuration
    must remain supported.
    """

    monkeypatch.delenv(
        "NOVAOPS_SERVICES_JSON",
        raising=False,
    )

    monkeypatch.setenv(
        "NOVAOPS_SIMULATOR_URL",
        "https://example.com/",
    )

    services = get_monitored_services()

    assert len(services) == 1

    service = services[0]

    assert (
        service.name
        == "NovaOps DEV Simulator"
    )

    assert (
        service.health_url
        == "https://example.com/health"
    )

    assert service.timeout_seconds == 30

    assert (
        service.latency_threshold_ms
        == 5000
    )


def test_single_service_json_configuration(
    monkeypatch,
):
    """
    One service can be configured entirely
    through NOVAOPS_SERVICES_JSON.
    """

    config = [
        {
            "name": "Customer API",
            "health_url":
                "https://api.example.com/health",
            "timeout_seconds": 5,
            "latency_threshold_ms": 1500,
        }
    ]

    monkeypatch.setenv(
        "NOVAOPS_SERVICES_JSON",
        json.dumps(config),
    )

    services = get_monitored_services()

    assert len(services) == 1

    service = services[0]

    assert service.name == "Customer API"

    assert (
        service.health_url
        == "https://api.example.com/health"
    )

    assert service.timeout_seconds == 5

    assert (
        service.latency_threshold_ms
        == 1500
    )


def test_multiple_services_json_configuration(
    monkeypatch,
):
    """
    Multiple services should be loaded
    without changing application code.
    """

    config = [
        {
            "name": "Customer API",
            "health_url":
                "https://api.example.com/health",
        },
        {
            "name": "Website",
            "health_url":
                "https://www.example.com/health",
        },
        {
            "name": "Authentication API",
            "health_url":
                "https://auth.example.com/health",
        },
    ]

    monkeypatch.setenv(
        "NOVAOPS_SERVICES_JSON",
        json.dumps(config),
    )

    services = get_monitored_services()

    assert len(services) == 3

    assert [
        service.name
        for service in services
    ] == [
        "Customer API",
        "Website",
        "Authentication API",
    ]


def test_default_service_values(
    monkeypatch,
):
    """
    Optional timeout and latency settings
    should receive sensible defaults.
    """

    config = [
        {
            "name": "Orders API",
            "health_url":
                "https://orders.example.com/health",
        }
    ]

    monkeypatch.setenv(
        "NOVAOPS_SERVICES_JSON",
        json.dumps(config),
    )

    services = get_monitored_services()

    service = services[0]

    assert service.timeout_seconds == 10

    assert (
        service.latency_threshold_ms
        == 2000
    )


def test_json_configuration_takes_priority(
    monkeypatch,
):
    """
    New multi-service configuration should
    override the legacy simulator setting.
    """

    config = [
        {
            "name": "Primary API",
            "health_url":
                "https://primary.example.com/health",
        }
    ]

    monkeypatch.setenv(
        "NOVAOPS_SERVICES_JSON",
        json.dumps(config),
    )

    monkeypatch.setenv(
        "NOVAOPS_SIMULATOR_URL",
        "https://simulator.example.com",
    )

    services = get_monitored_services()

    assert len(services) == 1

    assert (
        services[0].name
        == "Primary API"
    )


def test_invalid_json_raises_error(
    monkeypatch,
):
    """
    Invalid JSON must fail clearly instead
    of silently disabling monitoring.
    """

    monkeypatch.setenv(
        "NOVAOPS_SERVICES_JSON",
        "this-is-not-json",
    )

    with pytest.raises(
        ValueError,
        match="invalid JSON",
    ):
        get_monitored_services()


def test_json_must_be_array(
    monkeypatch,
):
    """
    Top-level configuration must be an array
    because NovaOps supports multiple services.
    """

    config = {
        "name": "Customer API",
        "health_url":
            "https://api.example.com/health",
    }

    monkeypatch.setenv(
        "NOVAOPS_SERVICES_JSON",
        json.dumps(config),
    )

    with pytest.raises(
        ValueError,
        match="JSON array",
    ):
        get_monitored_services()


def test_service_requires_name(
    monkeypatch,
):
    config = [
        {
            "health_url":
                "https://example.com/health",
        }
    ]

    monkeypatch.setenv(
        "NOVAOPS_SERVICES_JSON",
        json.dumps(config),
    )

    with pytest.raises(
        ValueError,
        match="requires a name",
    ):
        get_monitored_services()


def test_service_requires_health_url(
    monkeypatch,
):
    config = [
        {
            "name": "Broken Config",
        }
    ]

    monkeypatch.setenv(
        "NOVAOPS_SERVICES_JSON",
        json.dumps(config),
    )

    with pytest.raises(
        ValueError,
        match="requires a health_url",
    ):
        get_monitored_services()
