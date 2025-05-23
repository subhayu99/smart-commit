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