from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_num_ctx: int = 2048
    ollama_num_predict: int = 64
    ollama_temperature: float = 0.0

    smtp_host: str = "mailhog"
    smtp_port: int = 1025
    smtp_sender: str = "agent@my-app.local"
    smtp_timeout: int = 10
    default_email_subject: str = "Wiadomość przekierowana przez Agenta AI"

    prompt_path: Path = APP_DIR / "prompts" / "email_recipient_prompt.md"
    model_config = SettingsConfigDict(extra="ignore")

    semaphore_limit: int = 3
    rpm_limit_max_rate: int = 10
    rpm_limit_time_period: int = 60


settings = Settings()
