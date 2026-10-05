from fastapi.testclient import TestClient

from simulator.main import app, service_state


client = TestClient(app)


def reset_service():
    """Reset simulator before a test."""
    service_state.status = "healthy"
    service_state.response_time_ms = 50


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["service"] == "NovaOps Service Simulator"
    assert data["environment"] == "DEV"
    assert data["status"] == "running"


def test_health_when_service_is_healthy():
    reset_service()

    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert data["response_time_ms"] == 50


def test_failure_simulation():
    reset_service()

    failure_response = client.post(
        "/test/failure"
    )

    assert failure_response.status_code == 200
    assert (
        failure_response.json()["status"]
        == "unhealthy"
    )

    health_response = client.get(
        "/health"
    )

    assert health_response.status_code == 503

    data = health_response.json()

    assert (
        data["detail"]["status"]
        == "unhealthy"
    )


def test_recovery_simulation():
    reset_service()

    client.post(
        "/test/failure"
    )

    recovery_response = client.post(
        "/test/recovery"
    )

    assert recovery_response.status_code == 200

    assert (
        recovery_response.json()["status"]
        == "healthy"
    )

    health_response = client.get(
        "/health"
    )

    assert health_response.status_code == 200

    data = health_response.json()

    assert data["status"] == "healthy"
    assert data["response_time_ms"] == 50


def test_complete_incident_lifecycle():
    """
    Simulate the complete service lifecycle:

    HEALTHY -> FAILURE -> RECOVERY
    """

    reset_service()

    # 1. Service starts healthy
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

    # 2. Simulate real failure
    response = client.post(
        "/test/failure"
    )

    assert response.status_code == 200

    # 3. Monitor would now observe HTTP 503
    response = client.get("/health")

    assert response.status_code == 503

    assert (
        response.json()["detail"]["status"]
        == "unhealthy"
    )

    # 4. Restore service
    response = client.post(
        "/test/recovery"
    )

    assert response.status_code == 200

    # 5. Monitor sees service healthy again
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
