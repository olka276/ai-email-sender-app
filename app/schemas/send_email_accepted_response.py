from pydantic import BaseModel


class SendEmailAcceptedResponse(BaseModel):
    status: str = "accepted"
