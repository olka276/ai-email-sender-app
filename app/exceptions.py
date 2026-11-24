class EmailProcessingError(Exception):
    """Base exception for errors raised while processing a request."""


class LLMUnavailableError(EmailProcessingError):
    """The language model (Ollama) is unavailable or returned an error."""


class EmailDeliveryError(EmailProcessingError):
    """The message could not be delivered through the SMTP server."""
