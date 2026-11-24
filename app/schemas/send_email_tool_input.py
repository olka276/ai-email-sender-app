from pydantic import BaseModel, Field

from .department import Department


class SendEmailToolInput(BaseModel):
    department: Department = Field(description="Docelowy dział organizacji wybrany na podstawie treści wiadomości e-mail")
