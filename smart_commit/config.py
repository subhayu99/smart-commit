"""Configuration management for smart-commit."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import toml
from pydantic import BaseModel, Field


class CommitTemplateConfig(BaseModel):
    """Configuration for commit message templates."""
    max_subject_length: int = Field(default=50, description="Maximum length for commit subject")
    include_body: bool = Field(default=True, description="Whether to include commit body")
    include_reasoning: bool = Field(default=True, description="Whether to include reasoning section")
    conventional_commits: bool = Field(default=True, description="Use conventional commit format")
    custom_prefixes: Dict[str, str] = Field(default_factory=dict, description="Custom commit type prefixes")


class AIConfig(BaseModel):
    """Configuration for AI provider."""
    provider: str = Field(default="openai", description="AI provider (openai, anthropic, etc.)")
    model: str = Field(default="gpt-4o", description="Model to use")
    api_key: Optional[str] = Field(default=None, description="API key (can be set via environment)")
    max_tokens: int = Field(default=500, description="Maximum tokens for response")
    temperature: float = Field(default=0.1, description="Temperature for AI generation")


class RepositoryConfig(BaseModel):
    """Repository-specific configuration."""
    name: str = Field(description="Repository name")
    description: Optional[str] = Field(default=None, description="Repository description")
    tech_stack: List[str] = Field(default_factory=list, description="Technologies used in the repo")
    commit_conventions: Dict[str, str] = Field(default_factory=dict, description="Project-specific commit conventions")
    ignore_patterns: List[str] = Field(default_factory=list, description="Patterns to ignore in diffs")
    context_files: List[str] = Field(default_factory=list, description="Files to include for context")


class GlobalConfig(BaseModel):
    """Global configuration for smart-commit."""
    ai: AIConfig = Field(default_factory=AIConfig)
    template: CommitTemplateConfig = Field(default_factory=CommitTemplateConfig)
    repositories: Dict[str, RepositoryConfig] = Field(default_factory=dict)
    
    
@dataclass
class ConfigManager:
    """Manages configuration loading and saving."""
    
    def __init__(self):
        self.global_config_path = Path.home() / ".config" / "smart-commit" / "config.toml"
        self.local_config_path = Path.cwd() / ".smart-commit.toml"
        
    def get_config_path(self, local: bool = False) -> Path:
        """Get the appropriate config path."""
        return self.local_config_path if local else self.global_config_path
        
    def load_config(self) -> GlobalConfig:
        """Load configuration from global and local files."""
        # Start with default config
        config_data = {}
        
        # Load global config
        if self.global_config_path.exists():
            with open(self.global_config_path, 'r') as f:
                global_data = toml.load(f)
                config_data.update(global_data)
        
        # Load local config and merge
        if self.local_config_path.exists():
            with open(self.local_config_path, 'r') as f:
                local_data = toml.load(f)
                # Merge local config with global
                self._deep_merge(config_data, local_data)
            
        return GlobalConfig(**config_data)
    
    def save_config(self, config: GlobalConfig, local: bool = False) -> None:
        """Save configuration to file."""
        config_path = self.get_config_path(local)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w') as f:
            toml.dump(config.model_dump(), f)
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """Deep merge two dictionaries."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
