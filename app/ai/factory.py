from app.core.config import settings
from app.ai.base import DocumentUnderstandingProvider
from app.ai.mock_provider import (
    RuleBasedDocumentUnderstandingProvider,
    MockDocumentUnderstandingProvider,
)
from app.ai.gemini_provider import GeminiDocumentUnderstandingProvider
from app.ai.openai_provider import OpenAIDocumentUnderstandingProvider


def get_ai_provider() -> DocumentUnderstandingProvider:
    """Instantiates and returns the configured AI DocumentUnderstandingProvider."""
    provider_name = (settings.AI_PROVIDER or "rule_based").lower()

    if provider_name == "gemini":
        return GeminiDocumentUnderstandingProvider()
    elif provider_name == "openai":
        return OpenAIDocumentUnderstandingProvider()
    else:
        return RuleBasedDocumentUnderstandingProvider()


__all__ = [
    "DocumentUnderstandingProvider",
    "RuleBasedDocumentUnderstandingProvider",
    "MockDocumentUnderstandingProvider",
    "GeminiDocumentUnderstandingProvider",
    "OpenAIDocumentUnderstandingProvider",
    "get_ai_provider",
]
