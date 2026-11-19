from aiolimiter import AsyncLimiter
from config import settings
from fastapi import APIRouter, HTTPException, status
from schemas import SendEmailRequest
from services.email_llm_service import LLMService

import asyncio

router = APIRouter(tags=["Email"])
rpm_limiter = AsyncLimiter(
    max_rate=settings.rpm_limit_max_rate,
    time_period=settings.rpm_limit_time_period
)
semaphore = asyncio.Semaphore(settings.semaphore_limit)
email_llm_service = LLMService()

@router.post("/send")
async def forward_mail(payload: SendEmailRequest):
    async with semaphore:
        async with rpm_limiter:
            try:
                result = await email_llm_service.forward_email(payload.email, payload.message)
                return {"status": "sent", "classification": result}
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to process email: {str(e)}")