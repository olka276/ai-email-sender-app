import asyncio
import logging

from aiolimiter import AsyncLimiter
from fastapi import APIRouter, BackgroundTasks, Depends, status

from config import settings
from dependencies import get_llm_service, get_logger
from exceptions import EmailProcessingError
from schemas import SendEmailAcceptedResponse, SendEmailRequest
from services.email_llm_service import LLMService

router = APIRouter(tags=["Email"])
rpm_limiter = AsyncLimiter(
    max_rate=settings.rpm_limit_max_rate,
    time_period=settings.rpm_limit_time_period,
)
semaphore = asyncio.Semaphore(settings.semaphore_limit)


async def process_email(
    service: LLMService, logger: logging.Logger, email: str, message: str
) -> None:
    """Background task: classify the message with the LLM and forward it to a department."""
    async with semaphore:
        async with rpm_limiter:
            try:
                result = await service.forward_email(email, message)
                logger.info("Processed message from %s: %s", email, result)
            except EmailProcessingError as exc:
                logger.error(
                    "Failed to process message from %s (%s): %s",
                    email, type(exc).__name__, exc,
                    exc_info=exc.__cause__ is not None,
                )
            except Exception:
                logger.exception("Unexpected error processing message from %s", email)


@router.post(
    "/send",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=SendEmailAcceptedResponse,
)
async def forward_mail(
    payload: SendEmailRequest,
    background_tasks: BackgroundTasks,
    service: LLMService = Depends(get_llm_service),
    logger: logging.Logger = Depends(get_logger),
):
    background_tasks.add_task(process_email, service, logger, payload.email, payload.message)
    return SendEmailAcceptedResponse()
