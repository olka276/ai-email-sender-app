from pydantic import BaseModel, EmailStr, Field

# The system prompt takes ~800 of the model's 2048 context tokens; this limit keeps
# the message from pushing the instructions out of the context window.
MESSAGE_MAX_LENGTH = 2000


class SendEmailRequest(BaseModel):
    email: EmailStr
    message: str = Field(min_length=1, max_length=MESSAGE_MAX_LENGTH)
