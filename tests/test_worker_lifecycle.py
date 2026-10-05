import signal

import monitoring.worker as worker


def test_shutdown_request_sets_flag():
    """
    SIGTERM/SIGINT handling should request
    a graceful worker shutdown.
    """

    worker.shutdown_requested = False

    worker.request_shutdown(
        signal.SIGTERM,
        None,
    )

    assert worker.shutdown_requested is True


def test_worker_does_not_start_without_services(
    monkeypatch,
):
    """
    The worker should exit safely when no
    monitoring targets are configured.
    """

    database_created = {
        "called": False,
    }

    def fake_create_database():
        database_created["called"] = True

    monkeypatch.setattr(
        worker,
        "create_database",
        fake_create_database,
    )

    monkeypatch.setattr(
        worker,
        "get_monitored_services",
        lambda: [],
    )

    monkeypatch.setattr(
        worker,
        "install_signal_handlers",
        lambda: None,
    )

    worker.run_worker()

    assert database_created["called"] is True


def test_worker_runs_monitoring_cycle(
    monkeypatch,
):
    """
    A configured worker should execute a
    monitoring cycle.
    """

    fake_service = object()

    cycle_calls = {
        "count": 0,
    }

    def fake_cycle(services):
        assert services == [fake_service]

        cycle_calls["count"] += 1

        # Stop after the first cycle.
        worker.shutdown_requested = True

    monkeypatch.setattr(
        worker,
        "create_database",
        lambda: None,
    )

    monkeypatch.setattr(
        worker,
        "get_monitored_services",
        lambda: [fake_service],
    )

    monkeypatch.setattr(
        worker,
        "install_signal_handlers",
        lambda: None,
    )

    monkeypatch.setattr(
        worker,
        "run_monitoring_cycle",
        fake_cycle,
    )

    worker.run_worker()

    assert cycle_calls["count"] == 1


def test_worker_survives_failed_cycle(
    monkeypatch,
):
    """
    One failed monitoring cycle must not
    permanently terminate the worker.
    """

    fake_service = object()

    cycle_calls = {
        "count": 0,
    }

    def fake_cycle(services):
        assert services == [fake_service]

        cycle_calls["count"] += 1

        if cycle_calls["count"] == 1:
            raise RuntimeError(
                "simulated monitoring failure"
            )

        worker.shutdown_requested = True

    monkeypatch.setattr(
        worker,
        "create_database",
        lambda: None,
    )

    monkeypatch.setattr(
        worker,
        "get_monitored_services",
        lambda: [fake_service],
    )

    monkeypatch.setattr(
        worker,
        "install_signal_handlers",
        lambda: None,
    )

    monkeypatch.setattr(
        worker,
        "run_monitoring_cycle",
        fake_cycle,
    )

    monkeypatch.setattr(
        worker,
        "CHECK_INTERVAL_SECONDS",
        0,
    )

    worker.run_worker()

    assert cycle_calls["count"] == 2


def test_worker_initializes_database_before_services(
    monkeypatch,
):
    """
    Database initialization must happen before
    service configuration is loaded.
    """

    calls = []

    def fake_create_database():
        calls.append(
            "database"
        )

    def fake_get_services():
        calls.append(
            "services"
        )

        return []

    monkeypatch.setattr(
        worker,
        "create_database",
        fake_create_database,
    )

    monkeypatch.setattr(
        worker,
        "get_monitored_services",
        fake_get_services,
    )

    worker.run_worker()

    assert calls == [
        "database",
        "services",
    ]
