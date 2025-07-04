"""MCP (Model Context Protocol) server implementation using FastMCP."""

import os
import subprocess
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from smart_commit.ai_providers import get_ai_provider
from smart_commit.config import ConfigManager
from smart_commit.repository import RepositoryAnalyzer
from smart_commit.templates import PromptBuilder, CommitMessageFormatter


# Create FastMCP server
mcp = FastMCP("Smart Commit", description="AI-powered git commit message generator with repository context awareness")


def get_staged_changes_internal(repo_path: Optional[Path] = None) -> str:
    """Get staged changes from git - internal helper function."""
    try:
        cmd = ["git", "diff", "--staged"]
        if repo_path:
            result = subprocess.run(
                cmd, cwd=repo_path, capture_output=True, text=True, check=True
            )
        else:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError:
        return ""


@mcp.tool()
def analyze_repository(path: Optional[str] = None) -> str:
    """Analyze repository structure and context.
    
    Args:
        path: Repository path (optional, defaults to current directory)
    """
    try:
        repo_path = Path(path) if path else None
        analyzer = RepositoryAnalyzer(repo_path)
        context = analyzer.get_context()
        
        content = f"""# Repository Analysis: {context.name}

**Path:** {context.path}
**Description:** {context.description or 'No description available'}

## Technology Stack
{', '.join(context.tech_stack) if context.tech_stack else 'Not detected'}

## Active Branches
{', '.join(context.active_branches) if context.active_branches else 'None found'}

## Recent Commits
"""
        
        for commit in context.recent_commits[:10]:
            content += f"- {commit}\n"
        
        if context.file_structure:
            content += "\n## File Structure\n"
            for directory, files in context.file_structure.items():
                content += f"- **{directory}/**: {len(files)} files\n"
        
        return content
        
    except Exception as e:
        return f"Error analyzing repository: {str(e)}"


@mcp.tool()
def generate_commit_message(
    additional_context: Optional[str] = None,
    repository_path: Optional[str] = None,
    show_prompt: bool = False
) -> str:
    """Generate AI-powered commit message for staged changes.
    
    Args:
        additional_context: Additional context for commit message generation
        repository_path: Repository path (optional, defaults to current directory)
        show_prompt: Whether to include the generated prompt in the response
    """
    try:
        # ...
        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.load_config()

        # Get AI credentials from environment variables first, then from config
        api_key = os.getenv("AI_API_KEY") or config.ai.api_key
        model = os.getenv("AI_MODEL") or config.ai.model

        if not api_key or not model:
            return "Error: AI_MODEL and AI_API_KEY must be set as environment variables or in the config."
        
        repo_path = Path(repository_path) if repository_path else None
        
        # Get staged changes
        staged_changes = get_staged_changes_internal(repo_path)
        if not staged_changes:
            return "No staged changes found. Stage some changes first with 'git add'."
        
        # Initialize repository analyzer
        analyzer = RepositoryAnalyzer(repo_path)
        repo_context = analyzer.get_context()
        
        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        # Get repository-specific config
        repo_config = config.repositories.get(repo_context.name)
        
        # Filter diff if ignore patterns are configured
        if repo_config and repo_config.ignore_patterns:
            staged_changes = analyzer.filter_diff(staged_changes, repo_config.ignore_patterns)
        
        # Build prompt
        prompt_builder = PromptBuilder(config.template)
        prompt = prompt_builder.build_prompt(
            diff_content=staged_changes,
            repo_context=repo_context,
            repo_config=repo_config,
            additional_context=additional_context
        )
        
        # Generate commit message
        ai_provider = get_ai_provider(
            api_key=api_key,
            model=model,
            max_tokens=config.ai.max_tokens,
            temperature=config.ai.temperature
        )
        
        raw_message = ai_provider.generate_commit_message(prompt)
        
        # Format message
        formatter = CommitMessageFormatter(config.template)
        commit_message = formatter.format_message(raw_message)
        
        response = f"Generated commit message:\n\n{commit_message}"
        
        if show_prompt:
            response += f"\n\n--- Generated Prompt ---\n{prompt}"
        
        return response
        
    except Exception as e:
        return f"Error generating commit message: {str(e)}"


@mcp.tool()
def get_staged_changes(repository_path: Optional[str] = None) -> str:
    """Get current staged changes in git diff format.
    
    Args:
        repository_path: Repository path (optional, defaults to current directory)
    """
    try:
        repo_path = Path(repository_path) if repository_path else None
        staged_changes = get_staged_changes_internal(repo_path)
        
        if not staged_changes:
            return "No staged changes found."
        
        return f"Staged changes:\n\n```diff\n{staged_changes}\n```"
        
    except Exception as e:
        return f"Error getting staged changes: {str(e)}"


@mcp.tool()
def configure_smart_commit(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    max_subject_length: Optional[int] = None,
    conventional_commits: Optional[bool] = None,
    include_body: Optional[bool] = None,
    include_reasoning: Optional[bool] = None
) -> str:
    """Configure smart-commit settings.
    
    Args:
        provider: AI provider (openai or anthropic)
        model: Model name
        api_key: API key for the provider
        max_tokens: Maximum tokens for AI response
        temperature: Temperature for AI generation
        max_subject_length: Maximum length for commit subject line
        conventional_commits: Whether to use conventional commits format
        include_body: Whether to include commit body
        include_reasoning: Whether to include reasoning in commit message
    """
    try:
        if provider and provider not in ["openai", "anthropic"]:
            return "Error: Provider must be 'openai' or 'anthropic'"
        
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        # Update AI configuration
        if provider:
            config.ai.provider = provider
        if model:
            config.ai.model = model
        if api_key:
            config.ai.api_key = api_key
        if max_tokens is not None:
            config.ai.max_tokens = max_tokens
        if temperature is not None:
            config.ai.temperature = temperature
        
        # Update template configuration
        if max_subject_length is not None:
            config.template.max_subject_length = max_subject_length
        if conventional_commits is not None:
            config.template.conventional_commits = conventional_commits
        if include_body is not None:
            config.template.include_body = include_body
        if include_reasoning is not None:
            config.template.include_reasoning = include_reasoning
        
        # Save configuration
        config_manager.save_config(config)
        
        return f"✓ Smart-commit configuration updated successfully!\nProvider: {config.ai.provider}\nModel: {config.ai.model}"
        
    except Exception as e:
        return f"Error updating configuration: {str(e)}"


@mcp.tool()
def show_configuration() -> str:
    """Show current smart-commit configuration."""
    try:
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        ai_key_display = ("***" + config.ai.api_key[-4:]) if config.ai.api_key else "Not set"
        
        return f"""Smart Commit Configuration:

AI Configuration:
- Provider: {config.ai.provider}
- Model: {config.ai.model}
- API Key: {ai_key_display}
- Max Tokens: {config.ai.max_tokens}
- Temperature: {config.ai.temperature}

Template Configuration:
- Max Subject Length: {config.template.max_subject_length}
- Conventional Commits: {config.template.conventional_commits}
- Include Body: {config.template.include_body}
- Include Reasoning: {config.template.include_reasoning}

Config Locations:
- Global: {config_manager.global_config_path}
- Local: {config_manager.local_config_path}
"""
        
    except Exception as e:
        return f"Error loading configuration: {str(e)}"


@mcp.tool()
def quick_setup(
    provider: str = "openai",
    model: str = "gpt-4o",
    api_key: str = ""
) -> str:
    """Quick setup for smart-commit configuration.
    
    Args:
        provider: AI provider (openai, anthropic)
        model: Model to use
        api_key: API key for the provider
    """
    try:
        if provider not in ["openai", "anthropic"]:
            return "Error: Provider must be 'openai' or 'anthropic'"
        
        if not api_key:
            return "Error: API key is required for setup"
        
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        config.ai.provider = provider
        config.ai.model = model
        config.ai.api_key = api_key
        
        # Save global config
        config_manager.save_config(config, local=False)
        
        return f"""✓ Smart-commit setup completed successfully!

Configuration:
- Provider: {provider}
- Model: {model}
- Config saved to: {config_manager.global_config_path}

You can now use generate_commit_message to create AI-powered commit messages!
"""
        
    except Exception as e:
        return f"Error during setup: {str(e)}"


@mcp.tool()
def get_repository_context(path: Optional[str] = None) -> str:
    """Get detailed repository context information.
    
    Args:
        path: Repository path (optional, defaults to current directory)
    """
    try:
        repo_path = Path(path) if path else None
        analyzer = RepositoryAnalyzer(repo_path)
        repo_context = analyzer.get_context()
        
        # Load config to check for repo-specific settings
        config_manager = ConfigManager()
        config = config_manager.load_config()
        repo_config = config.repositories.get(repo_context.name)
        
        context_info = f"""Repository Context: {repo_context.name}

Basic Information:
- Path: {repo_context.path}
- Description: {repo_context.description or 'No description available'}

Technology Stack: {', '.join(repo_context.tech_stack) if repo_context.tech_stack else 'Not detected'}

Active Branches: {', '.join(repo_context.active_branches) if repo_context.active_branches else 'None found'}

Recent Commits:"""
        
        for commit in repo_context.recent_commits[:10]:
            context_info += f"\n- {commit}"
        
        if repo_context.file_structure:
            context_info += "\n\nFile Structure:"
            for directory, files in repo_context.file_structure.items():
                context_info += f"\n- {directory}/: {len(files)} files"
        
        if repo_config:
            context_info += f"\n\nRepository-specific configuration found with {len(repo_config.ignore_patterns) if repo_config.ignore_patterns else 0} ignore patterns."
        
        return context_info
        
    except Exception as e:
        return f"Error getting repository context: {str(e)}"


@mcp.resource("repository://current")
def get_current_repository_info() -> str:
    """Get information about the current repository"""
    try:
        analyzer = RepositoryAnalyzer()
        context = analyzer.get_context()
        
        return f"""Current Repository: {context.name}
Path: {context.path}
Description: {context.description or 'No description'}
Tech Stack: {', '.join(context.tech_stack) if context.tech_stack else 'Not detected'}
Active Branches: {', '.join(context.active_branches) if context.active_branches else 'None'}
Recent Commits: {len(context.recent_commits)} found
"""
    except Exception as e:
        return f"Error getting repository info: {str(e)}"


@mcp.resource("config://smart-commit")
def get_smart_commit_config() -> str:
    """Get current smart-commit configuration"""
    try:
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        return f"""Smart Commit Configuration:
AI Provider: {config.ai.provider}
Model: {config.ai.model}
Max Tokens: {config.ai.max_tokens}
Temperature: {config.ai.temperature}
Conventional Commits: {config.template.conventional_commits}
Max Subject Length: {config.template.max_subject_length}
"""
    except Exception as e:
        return f"Error loading config: {str(e)}"


@mcp.prompt()
def commit_message_template(
    diff_content: str = "",
    repo_context: str = "",
    additional_context: str = ""
) -> str:
    """Generate a prompt template for commit message creation based on the smart-commit approach"""
    return f"""You are an expert at writing clear, concise git commit messages. You analyze code changes and repository context to generate meaningful commit messages.

Repository Context:
{repo_context if repo_context else "No repository context provided"}

Code Changes (Git Diff):
{diff_content if diff_content else "No diff content provided"}

Additional Context:
{additional_context if additional_context else "No additional context provided"}

Please generate a commit message that:
1. Has a clear, descriptive subject line (50 characters or less)
2. Uses imperative mood ("Add" not "Added")
3. Follows conventional commits format if appropriate (feat:, fix:, docs:, etc.)
4. Includes body text if needed to explain WHY the change was made
5. References any relevant issue numbers if mentioned in context

Analyze the changes carefully and provide a commit message that accurately describes what was changed and why it matters to the project.

Format your response as a complete commit message ready to use with git commit.
"""


@mcp.prompt()
def repository_analysis_prompt(repo_path: str = ".") -> str:
    """Generate a prompt for analyzing repository structure and suggesting improvements"""
    return f"""Please analyze the repository at path: {repo_path}

Use the analyze_repository and get_repository_context tools to gather information, then focus on:

1. Project structure and organization
2. Technology stack and dependencies  
3. Recent development patterns from commit history
4. Code quality and commit message patterns
5. Potential areas for improvement in development workflow

Provide actionable recommendations for:
- Improving commit message quality
- Repository organization
- Development workflow optimization
- Smart-commit configuration suggestions

Use the available tools to gather comprehensive information before making recommendations.
"""


# Run the server
if __name__ == "__main__":
    mcp.run()