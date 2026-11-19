from enum import Enum
from pydantic import BaseModel, EmailStr, Field

class Department(str, Enum):
    HUMAN_RESOURCES = "human_resources"
    KADRY = "kadry"
    HELP_DESK = "help_desk"
    IT = "it"
    OTHER = "other"

class SendEmailRequest(BaseModel):
    email: EmailStr
    message: str

class SendEmailToolInput(BaseModel):
    department: Department = Field(description="Docelowy dział organizacji wybrany na podstawie treści wiadomości e-mail")