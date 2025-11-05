"""Configuration management for smart-commit."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import toml
from pydantic import BaseModel, Field, field_validator, model_validator


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

    # Message templates for different scenarios
    templates: Dict[str, str] = Field(default_factory=dict, description="Predefined templates for common scenarios")

    @field_validator('max_subject_length')
    @classmethod
    def validate_max_subject_length(cls, v):
        if v < 10 or v > 200:
            raise ValueError(f"max_subject_length must be between 10 and 200 (got {v})")
        return v

    @field_validator('max_recent_commits')
    @classmethod
    def validate_max_recent_commits(cls, v):
        if v < 0 or v > 50:
            raise ValueError(f"max_recent_commits must be between 0 and 50 (got {v})")
        return v

    @field_validator('max_context_file_size')
    @classmethod
    def validate_max_context_file_size(cls, v):
        if v < 100 or v > 1000000:
            raise ValueError(f"max_context_file_size must be between 100 and 1,000,000 (got {v})")
        return v


class AIConfig(BaseModel):
    """Configuration for AI provider."""
    model: str = Field(default="openai/gpt-4o", description="Model to use (e.g., 'openai/gpt-4o', 'claude-3-sonnet-20240229')")
    api_key: Optional[str] = Field(default=None, description="API key (best set via AI_API_KEY environment variable)")
    max_tokens: int = Field(default=500, description="Maximum tokens for response")
    temperature: float = Field(default=0.1, description="Temperature for AI generation")

    @field_validator('model')
    @classmethod
    def validate_model(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Model name cannot be empty")
        return v.strip()

    @field_validator('max_tokens')
    @classmethod
    def validate_max_tokens(cls, v):
        if v < 50 or v > 100000:
            raise ValueError(f"max_tokens must be between 50 and 100,000 (got {v})")
        return v

    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v):
        if v < 0.0 or v > 2.0:
            raise ValueError(f"temperature must be between 0.0 and 2.0 (got {v})")
        return v


class RepositoryConfig(BaseModel):
    """Repository-specific configuration."""
    name: str = Field(description="Repository name")
    description: Optional[str] = Field(description="Repository description")
    absolute_path: Optional[str] = Field(default=None, description="Absolute path to the repository")
    tech_stack: List[str] = Field(default_factory=list, description="Technologies used in the repo")
    commit_conventions: Dict[str, str] = Field(default=commit_conventions, description="Project-specific commit conventions")
    ignore_patterns: List[str] = Field(default_factory=list, description="Patterns to ignore in diffs")
    context_files: List[str] = Field(default_factory=list, description="Files to include for context")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Repository name cannot be empty")
        return v.strip()

    @field_validator('absolute_path')
    @classmethod
    def validate_absolute_path(cls, v):
        if v is not None and len(v.strip()) > 0:
            path = Path(v)
            if not path.is_absolute():
                raise ValueError(f"absolute_path must be an absolute path, got: {v}")
        return v

    @field_validator('context_files')
    @classmethod
    def validate_context_files(cls, v):
        if len(v) > 20:
            raise ValueError(f"Too many context_files ({len(v)}). Maximum is 20 to avoid token overflow.")
        return v


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
            try:
                with open(self.global_config_path, 'r') as f:
                    global_data = toml.load(f)
                    config_data.update(global_data)
            except toml.TomlDecodeError as e:
                raise ValueError(
                    f"Invalid TOML syntax in global config at {self.global_config_path}:\n{e}\n\n"
                    f"Please fix the syntax error or run 'smart-commit config --reset' to reset."
                )
            except Exception as e:
                raise ValueError(
                    f"Error reading global config at {self.global_config_path}: {e}"
                )

        # Load local config and merge
        if self.local_config_path.exists():
            try:
                with open(self.local_config_path, 'r') as f:
                    local_data = toml.load(f)
                    # Merge local config with global
                    self._deep_merge(config_data, local_data)
            except toml.TomlDecodeError as e:
                raise ValueError(
                    f"Invalid TOML syntax in local config at {self.local_config_path}:\n{e}\n\n"
                    f"Please fix the syntax error or remove the file."
                )
            except Exception as e:
                raise ValueError(
                    f"Error reading local config at {self.local_config_path}: {e}"
                )

        # Validate and create config object
        try:
            return GlobalConfig(**config_data)
        except Exception as e:
            # Provide helpful error message
            error_msg = self._format_validation_error(e, config_data)
            raise ValueError(error_msg)
    
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

    def _format_validation_error(self, error: Exception, config_data: Dict[str, Any]) -> str:
        """Format validation error with helpful context."""
        error_str = str(error)

        # Build helpful error message
        msg = f"Configuration validation error:\n\n{error_str}\n\n"

        # Add suggestions based on common errors
        if "max_subject_length" in error_str:
            msg += "Hint: max_subject_length must be between 10 and 200.\n"
            msg += "Edit your config file and set a valid value.\n"
        elif "max_recent_commits" in error_str:
            msg += "Hint: max_recent_commits must be between 0 and 50.\n"
        elif "max_context_file_size" in error_str:
            msg += "Hint: max_context_file_size must be between 100 and 1,000,000.\n"
        elif "max_tokens" in error_str:
            msg += "Hint: max_tokens must be between 50 and 100,000.\n"
        elif "temperature" in error_str:
            msg += "Hint: temperature must be between 0.0 and 2.0.\n"
        elif "Model name cannot be empty" in error_str:
            msg += "Hint: Set AI_MODEL environment variable or configure 'model' in config.\n"
            msg += "Example: model = \"openai/gpt-4o\"\n"
        elif "absolute_path must be an absolute path" in error_str:
            msg += "Hint: Use an absolute path starting with / (Linux/Mac) or C:\\ (Windows).\n"
        elif "Too many context_files" in error_str:
            msg += "Hint: Maximum 20 context files allowed. Reduce the number in your config.\n"

        # Add config file locations
        msg += f"\nConfig files:\n"
        msg += f"  Global: {self.global_config_path}\n"
        msg += f"  Local: {self.local_config_path}\n"
        msg += f"\nTo fix: Edit the config file or run 'smart-commit config --reset' to reset."

        return msg
