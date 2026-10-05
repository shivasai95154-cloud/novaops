import logging
import os
import smtplib

from email.message import EmailMessage


logger = logging.getLogger(
    "novaops.notifications"
)


def email_is_configured() -> bool:
    """
    Return True only when all required
    email configuration is available.
    """

    required = [
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
        "ALERT_EMAIL_FROM",
        "ALERT_EMAIL_TO",
    ]

    return all(
        os.getenv(name)
        for name in required
    )


def send_email(
    subject: str,
    body: str,
) -> bool:
    """
    Send an email notification.

    Returns True when successfully sent.

    Returns False when configuration is
    missing or delivery fails.

    Notification failures must not crash
    the monitoring worker.
    """

    if not email_is_configured():

        logger.warning(
            "Email notification skipped: "
            "SMTP configuration incomplete."
        )

        return False

    host = os.environ["SMTP_HOST"]
    port = int(os.environ["SMTP_PORT"])

    username = os.environ[
        "SMTP_USERNAME"
    ]

    password = os.environ[
        "SMTP_PASSWORD"
    ]

    sender = os.environ[
        "ALERT_EMAIL_FROM"
    ]

    receiver = os.environ[
        "ALERT_EMAIL_TO"
    ]

    message = EmailMessage()

    message["From"] = sender
    message["To"] = receiver
    message["Subject"] = subject

    message.set_content(body)

    try:

        with smtplib.SMTP_SSL(
            host,
            port,
            timeout=15,
        ) as smtp:

            smtp.login(
                username,
                password,
            )

            smtp.send_message(
                message
            )

        logger.info(
            "Email notification sent. subject=%s",
            subject,
        )

        return True

    except Exception:

        logger.exception(
            "Email notification delivery failed."
        )

        return False
