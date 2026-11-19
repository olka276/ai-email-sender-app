from langchain_core.tools import tool
from services.email_service import EmailService

email_service = EmailService()

@tool
def send_email_tool(to_email: str, subject: str, message: str) -> str:
    try:
        email_service.send_email(to_email=to_email, subject=subject, message=message)
        return f"Success: E-mail with subject: '{subject}' has been sent to: {to_email}."
    except Exception as e:
        return f"Error during sending an e-mail: {str(e)}"