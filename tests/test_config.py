"""Tests for configuration management."""

import pytest
import tempfile
import toml
from pathlib import Path

from smart_commit.config import ConfigManager, GlobalConfig, AIConfig


class TestConfigManager:
    """Test configuration manager."""
    
    def test_load_default_config(self):
        """Test loading default configuration."""
        config_manager = ConfigManager()
        config = GlobalConfig()
        
        assert config.ai.provider == "openai"
        assert config.ai.model == "gpt-4o"
        assert config.template.conventional_commits is True
    
    def test_save_and_load_config(self, tmp_path):
        """Test saving and loading configuration."""
        config_manager = ConfigManager()
        config_manager.global_config_path = tmp_path / "config.toml"
        config_manager.local_config_path = tmp_path / "config.toml"
        
        # Create test config
        config = GlobalConfig()
        config.ai.api_key = "test-key"
        config.ai.model = "gpt-3.5-turbo"
        
        # Save config
        config_manager.save_config(config, local=False)
        
        # Load config
        loaded_config = config_manager.load_config()
        
        assert loaded_config.ai.api_key == "test-key"
        assert loaded_config.ai.model == "gpt-3.5-turbo"
    
    def test_merge_local_config(self, tmp_path):
        """Test merging local configuration with global."""
        config_manager = ConfigManager()
        config_manager.global_config_path = tmp_path / "global.toml"
        config_manager.local_config_path = tmp_path / "local.toml"
        
        # Create global config
        global_config = {"ai": {"provider": "openai", "model": "gpt-4o"}}
        with open(config_manager.global_config_path, 'w') as f:
            toml.dump(global_config, f)
        
        # Create local config
        local_config = {"ai": {"model": "gpt-3.5-turbo"}}
        with open(config_manager.local_config_path, 'w') as f:
            toml.dump(local_config, f)
        
        # Load merged config
        config = config_manager.load_config()
        
        assert config.ai.provider == "openai"  # From global
        assert config.ai.model == "gpt-3.5-turbo"  # From local (override)


class TestConfigValidation:
    """Test configuration validation."""

    def test_max_tokens_validation_too_low(self):
        """Test max_tokens validation with value too low."""
        with pytest.raises(ValueError, match="max_tokens must be between"):
            config = GlobalConfig()
            config.ai.max_tokens = 10  # Too low

    def test_max_tokens_validation_too_high(self):
        """Test max_tokens validation with value too high."""
        with pytest.raises(ValueError, match="max_tokens must be between"):
            config = GlobalConfig()
            config.ai.max_tokens = 200000  # Too high

    def test_max_tokens_validation_valid(self):
        """Test max_tokens validation with valid value."""
        config = GlobalConfig()
        config.ai.max_tokens = 500  # Valid

        assert config.ai.max_tokens == 500

    def test_temperature_validation_too_low(self):
        """Test temperature validation with value too low."""
        with pytest.raises(ValueError, match="temperature must be between"):
            config = GlobalConfig()
            config.ai.temperature = -0.5  # Too low

    def test_temperature_validation_too_high(self):
        """Test temperature validation with value too high."""
        with pytest.raises(ValueError, match="temperature must be between"):
            config = GlobalConfig()
            config.ai.temperature = 3.0  # Too high

    def test_temperature_validation_valid(self):
        """Test temperature validation with valid values."""
        config = GlobalConfig()

        # Test boundary values
        config.ai.temperature = 0.0
        assert config.ai.temperature == 0.0

        config.ai.temperature = 2.0
        assert config.ai.temperature == 2.0

        config.ai.temperature = 1.0
        assert config.ai.temperature == 1.0

    def test_max_subject_length_validation_too_short(self):
        """Test max_subject_length validation with value too short."""
        with pytest.raises(ValueError, match="max_subject_length must be between"):
            config = GlobalConfig()
            config.template.max_subject_length = 5  # Too short

    def test_max_subject_length_validation_too_long(self):
        """Test max_subject_length validation with value too long."""
        with pytest.raises(ValueError, match="max_subject_length must be between"):
            config = GlobalConfig()
            config.template.max_subject_length = 250  # Too long

    def test_max_subject_length_validation_valid(self):
        """Test max_subject_length validation with valid value."""
        config = GlobalConfig()
        config.template.max_subject_length = 72

        assert config.template.max_subject_length == 72

    def test_max_recent_commits_validation_negative(self):
        """Test max_recent_commits validation with negative value."""
        with pytest.raises(ValueError, match="max_recent_commits must be between"):
            config = GlobalConfig()
            config.template.max_recent_commits = -1  # Negative

    def test_max_recent_commits_validation_too_high(self):
        """Test max_recent_commits validation with value too high."""
        with pytest.raises(ValueError, match="max_recent_commits must be between"):
            config = GlobalConfig()
            config.template.max_recent_commits = 100  # Too high

    def test_max_recent_commits_validation_valid(self):
        """Test max_recent_commits validation with valid values."""
        config = GlobalConfig()

        config.template.max_recent_commits = 0
        assert config.template.max_recent_commits == 0

        config.template.max_recent_commits = 10
        assert config.template.max_recent_commits == 10

        config.template.max_recent_commits = 50
        assert config.template.max_recent_commits == 50

    def test_max_context_file_size_validation_too_small(self):
        """Test max_context_file_size validation with value too small."""
        with pytest.raises(ValueError, match="max_context_file_size must be between"):
            config = GlobalConfig()
            config.template.max_context_file_size = 50  # Too small

    def test_max_context_file_size_validation_too_large(self):
        """Test max_context_file_size validation with value too large."""
        with pytest.raises(ValueError, match="max_context_file_size must be between"):
            config = GlobalConfig()
            config.template.max_context_file_size = 2000000  # Too large

    def test_max_context_file_size_validation_valid(self):
        """Test max_context_file_size validation with valid value."""
        config = GlobalConfig()
        config.template.max_context_file_size = 10000

        assert config.template.max_context_file_size == 10000

    def test_absolute_path_validation_not_absolute(self):
        """Test absolute_path validation with relative path."""
        from smart_commit.config import RepositoryConfig

        with pytest.raises(ValueError, match="absolute_path must be an absolute path"):
            RepositoryConfig(
                name="test",
                absolute_path="relative/path",  # Not absolute
                tech_stack=[]
            )

    def test_absolute_path_validation_valid(self, tmp_path):
        """Test absolute_path validation with valid absolute path."""
        from smart_commit.config import RepositoryConfig

        config = RepositoryConfig(
            name="test",
            absolute_path=str(tmp_path),
            tech_stack=[]
        )

        assert config.absolute_path == str(tmp_path)

    def test_context_files_validation_too_many(self):
        """Test context_files validation with too many files."""
        from smart_commit.config import RepositoryConfig

        with pytest.raises(ValueError, match="cannot have more than 20 context files"):
            RepositoryConfig(
                name="test",
                absolute_path="/tmp/test",
                tech_stack=[],
                context_files=[f"file{i}.md" for i in range(25)]  # 25 files
            )

    def test_context_files_validation_valid(self):
        """Test context_files validation with valid number."""
        from smart_commit.config import RepositoryConfig

        config = RepositoryConfig(
            name="test",
            absolute_path="/tmp/test",
            tech_stack=[],
            context_files=[f"file{i}.md" for i in range(10)]  # 10 files
        )

        assert len(config.context_files) == 10

    def test_repository_name_validation_empty(self):
        """Test repository name validation with empty name."""
        from smart_commit.config import RepositoryConfig

        with pytest.raises(ValueError, match="name cannot be empty"):
            RepositoryConfig(
                name="",  # Empty
                absolute_path="/tmp/test",
                tech_stack=[]
            )

    def test_model_validation_empty(self):
        """Test model validation with empty model."""
        with pytest.raises(ValueError, match="model cannot be empty"):
            config = GlobalConfig()
            config.ai.model = ""  # Empty