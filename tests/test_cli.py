"""Tests for CLI interface."""

import pytest
from unittest.mock import Mock, patch
from typer.testing import CliRunner

from smart_commit.cli import app


runner = CliRunner()


class TestCLI:
    """Test CLI commands."""
    
    @patch('smart_commit.cli._get_staged_changes')
    @patch('smart_commit.cli.RepositoryAnalyzer')
    @patch('smart_commit.cli.get_ai_provider')
    def test_generate_command_no_changes(self, mock_provider, mock_analyzer, mock_staged):
        """Test generate command with no staged changes."""
        mock_staged.return_value = ""
        
        result = runner.invoke(app, ["generate"])
        
        assert result.exit_code == 1
        assert "No staged changes" in result.stdout
    
    @patch('smart_commit.cli._get_staged_changes')
    @patch('smart_commit.cli.RepositoryAnalyzer')
    @patch('smart_commit.cli.get_ai_provider')
    @patch('smart_commit.cli.config_manager')
    def test_generate_command_success(self, mock_config_manager, mock_provider, mock_analyzer, mock_staged):
        """Test successful commit message generation."""
        # Setup mocks
        mock_staged.return_value = "diff --git a/test.py b/test.py\n+print('test')"
        
        mock_context = Mock()
        mock_context.name = "test-repo"
        mock_analyzer.return_value.get_context.return_value = mock_context
        
        mock_ai = Mock()
        mock_ai.generate_commit_message.return_value = "feat: add test feature"
        mock_provider.return_value = mock_ai
        
        mock_config = Mock()
        mock_config.ai.provider = "openai"
        mock_config.ai.api_key = "test-key"
        mock_config.ai.model = "gpt-4o"
        mock_config.repositories = {}
        mock_config_manager.load_config.return_value = mock_config
        
        result = runner.invoke(app, ["generate", "--dry-run"])
        
        assert result.exit_code == 0
        assert "Generated Commit Message" in result.stdout
    
    def test_context_command(self, temp_repo):
        """Test context command."""
        result = runner.invoke(app, ["context", str(temp_repo)])
        
        assert result.exit_code == 0
        assert "Repository Context" in result.stdout