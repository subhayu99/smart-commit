"""Tests for AI providers."""

import pytest
from unittest.mock import Mock, patch

from smart_commit.ai_providers import OpenAIProvider, get_ai_provider


class TestOpenAIProvider:
    """Test OpenAI provider."""
    
    @patch('smart_commit.ai_providers.OpenAI')
    def test_generate_commit_message(self, mock_openai):
        """Test commit message generation."""
        # Setup mock
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "feat: add new feature"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        # Test provider
        provider = OpenAIProvider(api_key="test-key", model="gpt-4o")
        result = provider.generate_commit_message("Test prompt")
        
        assert result == "feat: add new feature"
        mock_client.chat.completions.create.assert_called_once()
    
    def test_get_ai_provider_factory(self):
        """Test AI provider factory function."""
        provider = get_ai_provider("openai", "test-key", "gpt-4o")
        assert isinstance(provider, OpenAIProvider)
        
        with pytest.raises(ValueError):
            get_ai_provider("invalid", "test-key", "model")