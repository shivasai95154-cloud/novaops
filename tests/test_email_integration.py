import os

import pytest

from notifications.email import send_email


@pytest.mark.email_integration
def test_real_email_delivery():
    """
    Controlled integration test that sends
    one real NovaOps test email.

    The test is skipped when SMTP credentials
    are not available.
    """

    required = [
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
        "ALERT_EMAIL_FROM",
        "ALERT_EMAIL_TO",
    ]

    missing = [
        name
        for name in required
        if not os.getenv(name)
    ]

    if missing:
        pytest.skip(
            "Real email configuration not available."
        )

    sent = send_email(
        subject="NovaOps DEV — Email Integration Test",
        body=(
            "NovaOps successfully connected to "
            "the configured SMTP service.\n\n"
            "This is a controlled DEV integration "
            "test and not a real incident."
        ),
    )

    assert sent is True
