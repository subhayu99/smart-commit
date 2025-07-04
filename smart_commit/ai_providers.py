"""AI provider implementations."""
from abc import ABC, abstractmethod
import litellm
from smart_commit.utils import remove_backticks


class AIProvider(ABC):
    """Abstract base class for AI providers."""
    
    @abstractmethod
    def generate_commit_message(self, prompt: str, **kwargs) -> str:
        """Generate a commit message using the AI provider."""
        pass

class LiteLLMProvider(AIProvider):
    """LiteLLM provider implementation."""

    def __init__(self, api_key: str, model: str, **kwargs):
        if not api_key:
            raise ValueError("API_KEY is required for LiteLLMProvider.")
        if not model:
            raise ValueError("AI_MODEL is required for LiteLLMProvider.")
        
        self.api_key = api_key
        self.model = model
        self.kwargs = kwargs

    def generate_commit_message(self, prompt: str, **kwargs) -> str:
        """Generate commit message using LiteLLM."""
        merged_kwargs = {**self.kwargs, **kwargs}
        
        try:
            response = litellm.completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                api_key=self.api_key,
                max_tokens=merged_kwargs.get("max_tokens", 500),
                temperature=merged_kwargs.get("temperature", 0.1),
            )
            # The response object is a ModelResponse, which is dict-like
            return remove_backticks((response.choices[0].message.content or "").strip())
        except Exception as e:
            # LiteLLM provides rich exception types, you can handle them specifically if needed
            # For now, we'll just re-raise a generic error.
            raise RuntimeError(f"LiteLLM failed to generate a response: {e}") from e

def get_ai_provider(api_key: str, model: str, **kwargs) -> AIProvider:
    """Factory function to get the LiteLLM AI provider."""
    # The factory is now much simpler.
    return LiteLLMProvider(api_key=api_key, model=model, **kwargs)
