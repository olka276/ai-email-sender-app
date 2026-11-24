from config import settings
from exceptions import EmailDeliveryError
from email.message import EmailMessage
from langchain_core.tools import tool, InjectedToolArg
from schemas import Department, SendEmailToolInput
from typing import Annotated

import aiosmtplib

DEPARTMENT_EMAIL_MAP: dict[Department, str] = {
    Department.HUMAN_RESOURCES: "human-resources@example.com",
    Department.KADRY: "kadry@example.com",
    Department.HELP_DESK: "help-desk@example.com",
    Department.IT: "it@example.com",
    Department.OTHER: "other@example.com",
}

@tool("send_email_to_department", args_schema=SendEmailToolInput)
async def send_email_to_department(
        department: Department,
        original_sender: Annotated[str, InjectedToolArg] = "",
        subject: Annotated[str, InjectedToolArg] = "",
        message: Annotated[str, InjectedToolArg] = ""
) -> str:
    """
        Przekazuje wiadomość do odpowiedniego działu na podstawie analizy jej treści i tematu.
    """

    department_email = DEPARTMENT_EMAIL_MAP.get(
        department, DEPARTMENT_EMAIL_MAP[Department.OTHER]
    )

    email_message = EmailMessage()
    email_message["Subject"] = subject
    email_message["From"] = settings.smtp_sender
    email_message["To"] = department_email
    email_message["Reply-To"] = original_sender
    email_message.set_content(message)

    try:
        await aiosmtplib.send(
            email_message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            timeout=settings.smtp_timeout,
        )
    except (aiosmtplib.SMTPException, OSError) as exc:
        raise EmailDeliveryError(
            f"SMTP delivery to {department_email} failed: {exc}"
        ) from exc

    return f"Success: E-mail with body: '{message}' has been sent to: {department_email}."

