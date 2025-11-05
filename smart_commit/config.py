"""Configuration management for smart-commit."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import toml
from pydantic import BaseModel, Field


custom_prefixes = {
    "feat": "for new features",
    "fix": "for bug fixes",
    "docs": "for documentation changes",
    "style": "for formatting changes",
    "refactor": "for code refactoring",
    "test": "for test changes",
    "chore": "for maintenance tasks",
    "perf": "for performance improvements",
    "build": "for build system changes",
    "ci": "for CI/CD changes",
    "revert": "for reverting changes",
}

example_formats = [
    """feat: add user authentication system

- Implement JWT-based authentication
- Add login and logout endpoints
- Include password hashing with bcrypt
- Add authentication middleware for protected routes

This enables secure user sessions and protects sensitive endpoints from unauthorized access.""",
    """fix(database): resolve connection pool exhaustion

- Increase maximum pool size from 10 to 50
- Add connection timeout handling
- Implement proper connection cleanup
- Add monitoring for pool usage

Prevents application crashes during high traffic periods by ensuring adequate database connections.""",
]

commit_conventions = {
    "breaking": "Use BREAKING CHANGE: in footer for breaking changes that require major version bump",
    "scope": "Use scope in parentheses after type: feat(auth): add login system",
    "subject_case": "Use imperative mood in lowercase: 'add feature' not 'adds feature' or 'added feature'",
    "subject_length": "Keep subject line under 50 characters for better readability",
    "body_format": "Wrap body at 72 characters, use bullet points for multiple changes",
    "body_separation": "Separate subject from body with a blank line",
    "present_tense": "Use present tense: 'change' not 'changed' or 'changes'",
    "no_period": "Do not end the subject line with a period",
    "why_not_what": "Explain why the change was made, not just what was changed",
    "atomic_commits": "Make each commit a single logical change",
    "test_coverage": "Include test changes when adding new functionality",
    "docs_update": "Update documentation when changing public APIs or behavior"
}


class CommitTemplateConfig(BaseModel):
    """Configuration for commit message templates."""
    max_subject_length: int = Field(default=50, description="Maximum length for commit subject")
    max_recent_commits: int = Field(default=5, description="Number of recent commits to consider for context")
    max_context_file_size: int = Field(default=10000, description="Maximum characters to read from context files")
    include_body: bool = Field(default=True, description="Whether to include commit body")
    include_reasoning: bool = Field(default=True, description="Whether to include reasoning section")
    conventional_commits: bool = Field(default=True, description="Use conventional commit format")
    custom_prefixes: Dict[str, str] = Field(default=custom_prefixes, description="Custom commit type prefixes")
    example_formats: List[str] = Field(default=example_formats, description="Example commit formats for guidance")


class AIConfig(BaseModel):
    """Configuration for AI provider."""
    model: str = Field(default="openai/gpt-4o", description="Model to use (e.g., 'openai/gpt-4o', 'claude-3-sonnet-20240229')")
    api_key: Optional[str] = Field(default=None, description="API key (best set via AI_API_KEY environment variable)")
    max_tokens: int = Field(default=500, description="Maximum tokens for response")
    temperature: float = Field(default=0.1, description="Temperature for AI generation")


class RepositoryConfig(BaseModel):
    """Repository-specific configuration."""
    name: str = Field(description="Repository name")
    description: Optional[str] = Field(description="Repository description")
    absolute_path: Optional[str] = Field(default=None, description="Absolute path to the repository")
    tech_stack: List[str] = Field(default_factory=list, description="Technologies used in the repo")
    commit_conventions: Dict[str, str] = Field(default=commit_conventions, description="Project-specific commit conventions")
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
