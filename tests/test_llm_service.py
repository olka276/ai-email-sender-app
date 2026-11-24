from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import logging
import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from exceptions import LLMUnavailableError
from services.email_llm_service import LLMService


TOOL_PATH = "services.email_llm_service.send_email_to_department"


def fake_tool():
    tool = MagicMock()
    tool.ainvoke = AsyncMock()
    return tool


def fake_llm(message: AIMessage):
    return RunnableLambda(lambda _: message)


@pytest.fixture
def service():
    return LLMService()


async def test_tool_call_triggers_email_with_injected_args(service):
    service.llm_with_tools = fake_llm(
        AIMessage(
            content="",
            tool_calls=[
                {"name": "send_email_to_department", "args": {"department": "it"}, "id": "1"}
            ],
        )
    )

    with patch(TOOL_PATH, new=fake_tool()) as tool:
        result = await service.forward_email("jan@example.com", "Nie działa komputer")

    assert result == "Mail forwarded to: it"
    payload = tool.ainvoke.await_args.args[0]
    assert payload["department"] == "it"
    assert payload["original_sender"] == "jan@example.com"
    assert payload["message"] == "Nie działa komputer"


async def test_missing_department_falls_back_to_other(service):
    service.llm_with_tools = fake_llm(
        AIMessage(
            content="",
            tool_calls=[{"name": "send_email_to_department", "args": {}, "id": "1"}],
        )
    )

    with patch(TOOL_PATH, new=fake_tool()) as tool:
        await service.forward_email("jan@example.com", "?")

    assert tool.ainvoke.await_args.args[0]["department"] == "other"


async def test_no_tool_call_falls_back_to_other(service):
    service.llm_with_tools = fake_llm(AIMessage(content="nie wiem"))

    with patch(TOOL_PATH, new=fake_tool()) as tool:
        result = await service.forward_email("jan@example.com", "?")

    assert result == "Mail forwarded to: other"
    payload = tool.ainvoke.await_args.args[0]
    assert payload["department"] == "other"
    assert payload["message"] == "?"
    assert payload["original_sender"] == "jan@example.com"


async def test_unknown_department_falls_back_to_other(service, caplog):
    service.llm_with_tools = fake_llm(
        AIMessage(
            content="",
            tool_calls=[
                {"name": "send_email_to_department", "args": {"department": "sales"}, "id": "1"}
            ],
        )
    )

    with patch(TOOL_PATH, new=fake_tool()) as tool, caplog.at_level(logging.WARNING):
        result = await service.forward_email("jan@example.com", "?")

    assert result == "Mail forwarded to: other"
    assert tool.ainvoke.await_args.args[0]["department"] == "other"
    assert "sales" in caplog.text


async def test_other_tool_name_is_ignored(service):
    service.llm_with_tools = fake_llm(
        AIMessage(
            content="",
            tool_calls=[{"name": "something_else", "args": {"department": "it"}, "id": "1"}],
        )
    )

    with patch(TOOL_PATH, new=fake_tool()) as tool:
        await service.forward_email("jan@example.com", "?")

    assert tool.ainvoke.await_args.args[0]["department"] == "other"


async def test_llm_connection_error_is_wrapped(service):
    def boom(_):
        raise httpx.ConnectError("connection refused")

    service.llm_with_tools = RunnableLambda(boom)

    with pytest.raises(LLMUnavailableError) as exc_info:
        await service.forward_email("jan@example.com", "?")

    assert isinstance(exc_info.value.__cause__, httpx.ConnectError)


async def test_routing_decision_is_logged(service, caplog):
    service.llm_with_tools = fake_llm(
        AIMessage(
            content="",
            tool_calls=[
                {"name": "send_email_to_department", "args": {"department": "kadry"}, "id": "1"}
            ],
        )
    )

    with patch(TOOL_PATH, new=fake_tool()), caplog.at_level(logging.INFO):
        await service.forward_email("jan@example.com", "urlop")

    assert "kadry" in caplog.text
    assert "jan@example.com" in caplog.text


async def test_missing_tool_call_is_logged_as_warning(service, caplog):
    service.llm_with_tools = fake_llm(AIMessage(content="nie wiem"))

    with patch(TOOL_PATH, new=fake_tool()), caplog.at_level(logging.WARNING):
        await service.forward_email("jan@example.com", "?")

    assert any(r.levelno == logging.WARNING for r in caplog.records)
