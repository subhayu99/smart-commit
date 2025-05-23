"""AI provider implementations."""

from abc import ABC, abstractmethod

from openai import OpenAI

from smart_commit.utils import remove_backticks


class AIProvider(ABC):
    """Abstract base class for AI providers."""
    
    @abstractmethod
    def generate_commit_message(self, prompt: str, **kwargs) -> str:
        """Generate a commit message using the AI provider."""
        pass


class OpenAIProvider(AIProvider):
    """OpenAI provider implementation."""
    
    def __init__(self, api_key: str, model: str = "gpt-4o", **kwargs):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.kwargs = kwargs
    
    def generate_commit_message(self, prompt: str, **kwargs) -> str:
        """Generate commit message using OpenAI."""
        merged_kwargs = {**self.kwargs, **kwargs}
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=merged_kwargs.get("max_tokens", 500),
            temperature=merged_kwargs.get("temperature", 0.1),
        )
        
        return remove_backticks((response.choices[0].message.content or "").strip())


class AnthropicProvider(AIProvider):
    """Anthropic provider implementation (placeholder)."""
    
    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229", **kwargs):
        # This would require the anthropic library
        # import anthropic
        # self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.kwargs = kwargs
        raise NotImplementedError("Anthropic provider not implemented yet")
    
    def generate_commit_message(self, prompt: str, **kwargs) -> str:
        """Generate commit message using Anthropic."""
        # Implementation would go here
        raise NotImplementedError("Anthropic provider not implemented yet")


def get_ai_provider(provider_name: str, api_key: str, model: str, **kwargs) -> AIProvider:
    """Factory function to get AI provider."""
    providers = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
    }
    
    if provider_name not in providers:
        raise ValueError(f"Unsupported AI provider: {provider_name}")
    
    return providers[provider_name](api_key=api_key, model=model, **kwargs)
