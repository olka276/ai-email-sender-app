from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import SystemMessage

from config import settings
from tools.send_email_to_department import send_email_to_department
from typing import Any

class LLMService:
    def __init__(self):
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

    async def forward_email(self, original_sender: str, message: str) -> Any:
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
        prompt_result = await chain.ainvoke({
            "message": message,
            "original_sender": original_sender,
        })

        tool_calls = prompt_result.tool_calls

        for tool_call in tool_calls:
            if tool_call["name"] == "send_email_to_department":
                raw_args = tool_call["args"]
                department_value = raw_args.get("department") or "other"

                await send_email_to_department.ainvoke({
                    "department": department_value,
                    "original_sender": original_sender,
                    "subject": self.default_subject,
                    "message": message,
                })

                return raw_args

        return f"Mail not sent: {prompt_result.content}"
