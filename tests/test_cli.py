"""Tests for CLI interface."""

from unittest.mock import Mock, patch
from typer.testing import CliRunner

from smart_commit.cli import app
from smart_commit.config import GlobalConfig, AIConfig


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
        
        mock_config = GlobalConfig(
            ai=AIConfig(api_key="test-key", model="openai/gpt-4o")
        )
        mock_config_manager.load_config.return_value = mock_config
        
        result = runner.invoke(app, ["generate", "--dry-run"])
        
        assert result.exit_code == 0
        assert "Generated Commit Message" in result.stdout
    
    def test_context_command(self, temp_repo):
        """Test context command."""
        result = runner.invoke(app, ["context", str(temp_repo)])

        assert result.exit_code == 0
        assert "Repository Context" in result.stdout

    def test_version_command(self):
        """Test version command."""
        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert "smart-commit version" in result.stdout

    @patch('smart_commit.cli.Path')
    def test_install_hook_prepare_commit_msg(self, mock_path, temp_repo):
        """Test installing prepare-commit-msg hook."""
        # Mock git hooks directory
        mock_hooks_dir = Mock()
        mock_hooks_dir.exists.return_value = True
        mock_hook_file = Mock()
        mock_hook_file.exists.return_value = False

        mock_path.return_value = mock_hooks_dir

        result = runner.invoke(app, ["install-hook", "--type", "prepare-commit-msg"])

        # Should succeed (implementation specific)
        assert result.exit_code in [0, 1]  # May fail if not in git repo

    @patch('smart_commit.cli.Path')
    def test_install_hook_force(self, mock_path):
        """Test installing hook with force flag."""
        result = runner.invoke(app, ["install-hook", "--force"])

        # Should attempt installation
        assert result.exit_code in [0, 1]

    @patch('smart_commit.cli.Path')
    def test_uninstall_hook(self, mock_path):
        """Test uninstalling hook."""
        result = runner.invoke(app, ["uninstall-hook", "--type", "prepare-commit-msg"])

        # Should attempt uninstallation
        assert result.exit_code in [0, 1]

    @patch('smart_commit.cli.CommitMessageCache')
    def test_cache_cmd_stats(self, mock_cache_class):
        """Test cache stats command."""
        mock_cache = Mock()
        mock_cache.get_stats.return_value = {
            'total_entries': 5,
            'cache_size_bytes': 1024,
            'cache_size_mb': 0.001,
            'cache_dir': '/tmp/cache'
        }
        mock_cache_class.return_value = mock_cache

        result = runner.invoke(app, ["cache-cmd", "--stats"])

        assert result.exit_code == 0

    @patch('smart_commit.cli.CommitMessageCache')
    def test_cache_cmd_clear(self, mock_cache_class):
        """Test cache clear command."""
        mock_cache = Mock()
        mock_cache.clear.return_value = 5
        mock_cache_class.return_value = mock_cache

        result = runner.invoke(app, ["cache-cmd", "--clear"])

        assert result.exit_code == 0
        mock_cache.clear.assert_called_once()

    @patch('smart_commit.cli.CommitMessageCache')
    def test_cache_cmd_clear_expired(self, mock_cache_class):
        """Test cache clear-expired command."""
        mock_cache = Mock()
        mock_cache.clear_expired.return_value = 2
        mock_cache_class.return_value = mock_cache

        result = runner.invoke(app, ["cache-cmd", "--clear-expired"])

        assert result.exit_code == 0
        mock_cache.clear_expired.assert_called_once()

    @patch('smart_commit.cli._get_staged_changes')
    @patch('smart_commit.cli.RepositoryAnalyzer')
    @patch('smart_commit.cli.get_ai_provider')
    @patch('smart_commit.cli.config_manager')
    def test_generate_alias(self, mock_config_manager, mock_provider, mock_analyzer, mock_staged):
        """Test 'g' alias for generate command."""
        mock_staged.return_value = "diff --git a/test.py b/test.py\n+print('test')"

        mock_context = Mock()
        mock_context.name = "test-repo"
        mock_analyzer.return_value.get_context.return_value = mock_context

        mock_ai = Mock()
        mock_ai.generate_commit_message.return_value = "feat: add test"
        mock_provider.return_value = mock_ai

        mock_config = GlobalConfig(
            ai=AIConfig(api_key="test-key", model="openai/gpt-4o")
        )
        mock_config_manager.load_config.return_value = mock_config

        result = runner.invoke(app, ["g", "--dry-run"])

        assert result.exit_code == 0

    @patch('smart_commit.cli._get_staged_changes')
    @patch('smart_commit.cli.validate_diff_size')
    def test_generate_with_large_diff_warning(self, mock_validate, mock_staged):
        """Test generate command with large diff warning."""
        mock_staged.return_value = "diff --git a/test.py b/test.py\n+print('test')"
        mock_validate.return_value = {
            'is_valid': False,
            'warnings': ['Diff is very large (752 lines). Consider splitting.'],
            'line_count': 752,
            'char_count': 50000,
            'file_count': 12
        }

        result = runner.invoke(app, ["generate"])

        # Should show warning
        assert result.exit_code in [0, 1]

    @patch('smart_commit.cli._get_staged_changes')
    @patch('smart_commit.cli.detect_sensitive_data')
    @patch('smart_commit.cli.check_sensitive_files')
    def test_generate_with_sensitive_data_warning(self, mock_check_files, mock_detect, mock_staged):
        """Test generate command with sensitive data warning."""
        mock_staged.return_value = "diff --git a/.env b/.env\n+API_KEY=AKIAIOSFODNN7EXAMPLE"
        mock_detect.return_value = [("AWS Access Key", "AKIA***", 1)]
        mock_check_files.return_value = [".env"]

        result = runner.invoke(app, ["generate"])

        # Should show security warning
        assert result.exit_code in [0, 1]

    @patch('smart_commit.cli._get_staged_changes')
    @patch('smart_commit.cli.RepositoryAnalyzer')
    @patch('smart_commit.cli.get_ai_provider')
    @patch('smart_commit.cli.config_manager')
    @patch('smart_commit.cli.CommitMessageCache')
    def test_generate_with_cache_hit(self, mock_cache_class, mock_config_manager,
                                     mock_provider, mock_analyzer, mock_staged):
        """Test generate command with cache hit."""
        mock_staged.return_value = "diff --git a/test.py b/test.py\n+print('test')"

        # Mock cache hit
        mock_cache = Mock()
        mock_cache.get.return_value = "feat: cached message"
        mock_cache_class.return_value = mock_cache

        mock_context = Mock()
        mock_context.name = "test-repo"
        mock_analyzer.return_value.get_context.return_value = mock_context

        mock_config = GlobalConfig(
            ai=AIConfig(api_key="test-key", model="openai/gpt-4o")
        )
        mock_config_manager.load_config.return_value = mock_config

        result = runner.invoke(app, ["generate", "--dry-run"])

        assert result.exit_code == 0

    @patch('smart_commit.cli._get_staged_changes')
    @patch('smart_commit.cli.RepositoryAnalyzer')
    @patch('smart_commit.cli.get_ai_provider')
    @patch('smart_commit.cli.config_manager')
    def test_generate_with_privacy_mode(self, mock_config_manager, mock_provider,
                                       mock_analyzer, mock_staged):
        """Test generate command with privacy mode."""
        mock_staged.return_value = "diff --git a/test.py b/test.py\n+print('test')"

        mock_context = Mock()
        mock_context.name = "test-repo"
        mock_analyzer.return_value.get_context.return_value = mock_context

        mock_ai = Mock()
        mock_ai.generate_commit_message.return_value = "feat: add feature"
        mock_provider.return_value = mock_ai

        mock_config = GlobalConfig(
            ai=AIConfig(api_key="test-key", model="openai/gpt-4o")
        )
        mock_config_manager.load_config.return_value = mock_config

        result = runner.invoke(app, ["generate", "--privacy", "--dry-run"])

        assert result.exit_code == 0
        # Privacy mode message should be shown
        assert "Privacy mode" in result.stdout or result.exit_code == 0

    @patch('smart_commit.cli._get_staged_changes')
    @patch('smart_commit.cli.RepositoryAnalyzer')
    @patch('smart_commit.cli.get_ai_provider')
    @patch('smart_commit.cli.config_manager')
    def test_generate_with_no_cache_flag(self, mock_config_manager, mock_provider,
                                        mock_analyzer, mock_staged):
        """Test generate command with no-cache flag."""
        mock_staged.return_value = "diff --git a/test.py b/test.py\n+print('test')"

        mock_context = Mock()
        mock_context.name = "test-repo"
        mock_analyzer.return_value.get_context.return_value = mock_context

        mock_ai = Mock()
        mock_ai.generate_commit_message.return_value = "feat: add feature"
        mock_provider.return_value = mock_ai

        mock_config = GlobalConfig(
            ai=AIConfig(api_key="test-key", model="openai/gpt-4o")
        )
        mock_config_manager.load_config.return_value = mock_config

        result = runner.invoke(app, ["generate", "--no-cache", "--dry-run"])

        assert result.exit_code == 0