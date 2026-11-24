import asyncio
import logging

from aiolimiter import AsyncLimiter
from fastapi import APIRouter, BackgroundTasks, Depends, status

from config import settings
from dependencies import get_llm_service
from schemas import SendEmailAcceptedResponse, SendEmailRequest
from services.email_llm_service import LLMService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Email"])
rpm_limiter = AsyncLimiter(
    max_rate=settings.rpm_limit_max_rate,
    time_period=settings.rpm_limit_time_period,
)
semaphore = asyncio.Semaphore(settings.semaphore_limit)


async def process_email(service: LLMService, email: str, message: str) -> None:
    """Zadanie w tle: klasyfikacja wiadomości przez LLM i wysyłka do działu."""
    async with semaphore:
        async with rpm_limiter:
            try:
                result = await service.forward_email(email, message)
                logger.info("Processed message from %s: %s", email, result)
            except Exception:
                logger.exception("Failed to process message from %s", email)


@router.post(
    "/send",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=SendEmailAcceptedResponse,
)
async def forward_mail(
    payload: SendEmailRequest,
    background_tasks: BackgroundTasks,
    service: LLMService = Depends(get_llm_service),
):
    background_tasks.add_task(process_email, service, payload.email, payload.message)
    return SendEmailAcceptedResponse()
