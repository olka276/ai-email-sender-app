from functools import lru_cache

from services.email_llm_service import LLMService


@lru_cache
def get_llm_service() -> LLMService:
    return LLMService()
