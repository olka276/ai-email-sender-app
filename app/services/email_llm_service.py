import logging

import httpx
import ollama
from config import settings
from exceptions import LLMUnavailableError
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import AIMessage, SystemMessage
from schemas import Department
from tools.send_email_to_department import send_email_to_department

class LLMService:
    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or logging.getLogger(__name__)
        llm = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            num_ctx=settings.ollama_num_ctx,
            num_predict=settings.ollama_num_predict,
            temperature=settings.ollama_temperature
        )

        self.llm_with_tools = llm.bind_tools([send_email_to_department])
        self.system_prompt = settings.prompt_path.read_text(encoding="utf-8")
        self.default_subject = settings.default_email_subject

    async def forward_email(self, original_sender: str, message: str) -> str:
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=self.system_prompt),
            HumanMessagePromptTemplate.from_template(
                "<user_message>\n"
                "Nadawca: {original_sender}\n"
                "Treść wiadomości:\n{message}\n"
                "</user_message>"
            ),
        ])

        chain = prompt | self.llm_with_tools
        try:
            prompt_result = await chain.ainvoke({
                "message": message,
                "original_sender": original_sender,
            })
        except (httpx.HTTPError, ollama.ResponseError, OSError) as exc:
            raise LLMUnavailableError(f"LLM request failed: {exc}") from exc

        department = self._select_department(original_sender, prompt_result)

        await send_email_to_department.ainvoke({
            "department": department.value,
            "original_sender": original_sender,
            "subject": self.default_subject,
            "message": message,
        })

        return f"Mail forwarded to: {department.value}"

    def _select_department(self, original_sender: str, prompt_result: AIMessage) -> Department:
        """Pick the department from the LLM answer; fall back to OTHER so no message is lost."""
        for tool_call in prompt_result.tool_calls:
            if tool_call["name"] != "send_email_to_department":
                continue

            raw_department = tool_call["args"].get("department")
            try:
                department = Department(raw_department)
            except ValueError:
                self.logger.warning(
                    "LLM returned unknown department %r for message from %s, falling back to 'other'",
                    raw_department, original_sender,
                )
                return Department.OTHER

            self.logger.info(
                "LLM routed message from %s to department '%s'",
                original_sender, department.value,
            )
            return department

        self.logger.warning(
            "LLM did not call the email tool for message from %s (answer: %r), falling back to 'other'",
            original_sender, prompt_result.content,
        )
        return Department.OTHER
