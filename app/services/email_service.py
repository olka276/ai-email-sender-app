import os
import smtplib
from email.message import EmailMessage

class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "mailhog")
        self.smtp_port = int(os.getenv("SMTP_PORT", 1025))
        self.sender = os.getenv("SMTP_SENDER", "agent@my-app.local")

    def send_email(self, to_email: str, subject: str, message: str) -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = to_email
        msg.set_content(message)

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.send_message(msg)