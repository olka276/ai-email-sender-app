from pydantic import BaseModel, EmailStr


class SendEmailRequest(BaseModel):
    email: EmailStr
    message: str
