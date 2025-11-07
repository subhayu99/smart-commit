"""Tests for AI providers."""

import pytest
from unittest.mock import Mock, patch

from smart_commit.ai_providers import LiteLLMProvider, get_ai_provider


class TestLiteLLMProvider:
    """Test LiteLLM provider."""

    @patch('smart_commit.ai_providers.litellm.completion')
    def test_generate_commit_message(self, mock_completion):
        """Test commit message generation."""
        # Setup mock
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "feat: add new feature"
        mock_completion.return_value = mock_response

        # Test provider
        provider = LiteLLMProvider(api_key="test-key", model="openai/gpt-4o")
        result = provider.generate_commit_message("Test prompt")

        assert result == "feat: add new feature"
        mock_completion.assert_called_once()

    def test_litellm_provider_requires_api_key(self):
        """Test that LiteLLM provider requires API key."""
        with pytest.raises(ValueError, match="API_KEY is required"):
            LiteLLMProvider(api_key="", model="openai/gpt-4o")

    def test_litellm_provider_requires_model(self):
        """Test that LiteLLM provider requires model."""
        with pytest.raises(ValueError, match="AI_MODEL is required"):
            LiteLLMProvider(api_key="test-key", model="")

    def test_get_ai_provider_factory(self):
        """Test AI provider factory function."""
        provider = get_ai_provider(api_key="test-key", model="openai/gpt-4o")
        assert isinstance(provider, LiteLLMProvider)

    def test_litellm_custom_parameters(self):
        """Test that custom parameters are passed through."""
        provider = LiteLLMProvider(
            api_key="test-key",
            model="openai/gpt-4o",
            max_tokens=1000,
            temperature=0.5
        )
        assert provider.kwargs['max_tokens'] == 1000
        assert provider.kwargs['temperature'] == 0.5

    @patch('smart_commit.ai_providers.litellm.completion')
    def test_litellm_error_handling(self, mock_completion):
        """Test that LiteLLM errors are properly handled."""
        mock_completion.side_effect = Exception("API Error")

        provider = LiteLLMProvider(api_key="test-key", model="openai/gpt-4o")

        with pytest.raises(RuntimeError, match="LiteLLM failed"):
            provider.generate_commit_message("Test prompt")