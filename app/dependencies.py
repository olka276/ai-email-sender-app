import logging
from functools import lru_cache

from services.email_llm_service import LLMService


def get_logger() -> logging.Logger:
    return logging.getLogger("app")


@lru_cache
def get_llm_service() -> LLMService:
    return LLMService(logger=get_logger())
