from fastapi import APIRouter
from services.email_service import EmailService
from pydantic import BaseModel, EmailStr

router = APIRouter(tags=["Email"])

class SendEmailRequest(BaseModel):
    mail: EmailStr  # lub str, jeśli nie chcesz walidacji formatu e-mail
    message: str

@router.post("/send")
async def send_email(payload: SendEmailRequest):
    email = EmailService()
    email.send_email(payload.mail, "test", payload.message)
    return {"message": payload.mail}