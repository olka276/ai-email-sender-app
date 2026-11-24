from unittest.mock import AsyncMock, patch

import aiosmtplib
import pytest

from exceptions import EmailDeliveryError

from schemas import Department
from tools.send_email_to_department import (
    DEPARTMENT_EMAIL_MAP,
    send_email_to_department,
)


@pytest.mark.parametrize("department", list(Department))
async def test_sends_to_correct_address_with_reply_to(department):
    with patch("tools.send_email_to_department.aiosmtplib.send", new=AsyncMock()) as send:
        await send_email_to_department.ainvoke(
            {
                "department": department,
                "original_sender": "jan.nowak@example.com",
                "subject": "Temat",
                "message": "Treść",
            }
        )

    sent = send.await_args.args[0]
    assert sent["To"] == DEPARTMENT_EMAIL_MAP[department]
    assert sent["Reply-To"] == "jan.nowak@example.com"
    assert sent["Subject"] == "Temat"
    assert "Treść" in sent.get_content()


def test_every_department_has_an_address():
    assert set(DEPARTMENT_EMAIL_MAP) == set(Department)


@pytest.mark.parametrize("error", [aiosmtplib.SMTPException("boom"), ConnectionRefusedError()])
async def test_smtp_failure_raises_delivery_error(error):
    with patch(
        "tools.send_email_to_department.aiosmtplib.send", new=AsyncMock(side_effect=error)
    ):
        with pytest.raises(EmailDeliveryError):
            await send_email_to_department.ainvoke(
                {
                    "department": Department.IT,
                    "original_sender": "jan.nowak@example.com",
                    "subject": "Temat",
                    "message": "Treść",
                }
            )
