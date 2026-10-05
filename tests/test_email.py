from unittest.mock import patch

from notifications.email import (
    email_is_configured,
    send_email,
)


EMAIL_ENV = {
    "SMTP_HOST": "smtp.example.com",
    "SMTP_PORT": "465",
    "SMTP_USERNAME": "test-user",
    "SMTP_PASSWORD": "test-password",
    "ALERT_EMAIL_FROM": "sender@example.com",
    "ALERT_EMAIL_TO": "receiver@example.com",
}


@patch.dict(
    "os.environ",
    {},
    clear=True,
)
def test_missing_configuration_returns_false():

    assert email_is_configured() is False

    assert (
        send_email(
            "Test",
            "Test message",
        )
        is False
    )


@patch.dict(
    "os.environ",
    EMAIL_ENV,
    clear=True,
)
@patch(
    "notifications.email.smtplib.SMTP_SSL"
)
def test_email_delivery(
    mock_smtp,
):

    smtp_instance = (
        mock_smtp.return_value
        .__enter__.return_value
    )

    result = send_email(
        "NovaOps Test",
        "Testing notification service.",
    )

    assert result is True

    smtp_instance.login.assert_called_once_with(
        "test-user",
        "test-password",
    )

    smtp_instance.send_message.assert_called_once()


@patch.dict(
    "os.environ",
    EMAIL_ENV,
    clear=True,
)
@patch(
    "notifications.email.smtplib.SMTP_SSL"
)
def test_smtp_failure_returns_false(
    mock_smtp,
):

    smtp_instance = (
        mock_smtp.return_value
        .__enter__.return_value
    )

    smtp_instance.login.side_effect = (
        RuntimeError(
            "SMTP unavailable"
        )
    )

    result = send_email(
        "Test",
        "Test",
    )

    assert result is False
