"""Commit message templates and formatters."""

from dataclasses import dataclass
from pathlib import Path 
from typing import List, Optional

from smart_commit.config import CommitTemplateConfig, RepositoryConfig
from smart_commit.repository import RepositoryContext
from smart_commit.utils import remove_backticks, detect_scope_from_diff, detect_breaking_changes


@dataclass
class CommitMessageData:
    """Data structure for commit message generation."""
    changes_summary: str
    change_type: str
    affected_files: List[str]
    reasoning: Optional[str] = None


class PromptBuilder:
    """Builds prompts for AI commit message generation."""
    
    def __init__(self, template_config: CommitTemplateConfig):
        self.config = template_config
    
    def build_prompt(
        self,
        diff_content: str,
        repo_context: RepositoryContext,
        repo_config: Optional[RepositoryConfig] = None,
        additional_context: Optional[str] = None
    ) -> str:
        """Build a comprehensive prompt for commit message generation."""

        # Detect potential scopes and breaking changes
        suggested_scopes = detect_scope_from_diff(diff_content)
        breaking_changes = detect_breaking_changes(diff_content)

        prompt_parts = [
            self._get_system_prompt(),
            self._get_repository_context_section(repo_context, repo_config),
            self._get_scope_suggestions_section(suggested_scopes),
            self._get_breaking_changes_section(breaking_changes),
            self._get_diff_section(diff_content),
            self._get_requirements_section(),
            self._get_examples_section(),
        ]

        if additional_context:
            prompt_parts.append(f"\n**Additional Context:**\n{additional_context}")

        prompt_parts.append("*IMPORTANT: Your output should only contain the commit message, nothing else.*")

        return "\n\n".join(filter(None, prompt_parts))
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt."""
        return """You are an expert software engineer specializing in writing clear, meaningful git commit messages. 
Analyze the provided git diff and repository context to generate a commit message that accurately reflects 
the changes and follows best practices."""
    
    def _get_repository_context_section(
        self, 
        repo_context: RepositoryContext, 
        repo_config: Optional[RepositoryConfig]
    ) -> str:
        """Build repository context section."""
        context_parts = [
            "**Repository Context:**",
            f"- **Name:** {repo_context.name}",
        ]
        
        # Determine the repository path
        repo_path = Path(repo_config.absolute_path) if repo_config and repo_config.absolute_path else Path(".")
        context_parts.append(f"- **Path:** {repo_path.resolve()}")
        
        # Include context files only if the repository matches
        if repo_config and repo_config.context_files and repo_path.exists():
            context_parts.append("- **Context Files:**")
            max_size = self.config.max_context_file_size

            for context_file in repo_config.context_files:
                file_path = repo_path / context_file
                if file_path.exists() and file_path.is_file():
                    try:
                        # Check file size first
                        file_size = file_path.stat().st_size

                        content = file_path.read_text(encoding="utf-8").strip()

                        # Truncate if too large
                        if len(content) > max_size:
                            content = content[:max_size] + f"\n\n... (truncated, file is {len(content)} chars, showing first {max_size})"

                        context_parts.append(f"  - **{context_file}:**\n    ```\n    {content}\n    ```")
                    except Exception as e:
                        context_parts.append(f"  - **{context_file}:** (Error reading file: {e})")
                else:
                    context_parts.append(f"  - **{context_file}:** (File not found)")
        
        if repo_context.description:
            context_parts.append(f"- **Description:** {repo_context.description}")
        
        if isinstance(repo_context.tech_stack, list):
            context_parts.append(f"- **Tech Stack:** {', '.join(repo_context.tech_stack)}")
        
        if isinstance(repo_context.recent_commits, list):
            max_recent_commits = max(self.config.max_recent_commits, 0) or 5
            context_parts.append(f"- **Recent Commits (up to {max_recent_commits}):**")
            for commit in repo_context.recent_commits[:max_recent_commits]:
                context_parts.append(f"  - {commit}")
        
        if repo_config and repo_config.commit_conventions:
            context_parts.append("- **Project Conventions:**")
            for key, value in repo_config.commit_conventions.items():
                context_parts.append(f"  - {key}: {value}")
        
        return "\n".join(context_parts)
    
    def _get_scope_suggestions_section(self, suggested_scopes: List[str]) -> str:
        """Build the scope suggestions section."""
        if not suggested_scopes:
            return ""

        scopes_list = ", ".join(f"`{scope}`" for scope in suggested_scopes)
        return f"**Suggested Scopes (based on changed files):**\n{scopes_list}\n\nConsider using one of these scopes if appropriate for conventional commits."

    def _get_breaking_changes_section(self, breaking_changes: List[tuple]) -> str:
        """Build the breaking changes warning section."""
        if not breaking_changes:
            return ""

        changes_list = "\n".join([f"  - {reason}: {detail}" for reason, detail in breaking_changes[:5]])
        return f"""**⚡ BREAKING CHANGES DETECTED:**
{changes_list}

IMPORTANT: If these are truly breaking changes, add a 'BREAKING CHANGE:' footer to your commit message explaining the impact and migration path. This is critical for semantic versioning (triggers major version bump)."""

    def _get_diff_section(self, diff_content: str) -> str:
        """Build the diff section."""
        return f"**Git Diff:**\n```diff\n{diff_content}\n```"
    
    def _get_requirements_section(self) -> str:
        """Build the requirements section."""
        requirements = [
            "**Requirements:**",
            "1. Analyze the changes to understand their purpose and scope",
            "2. Use conventional commit format if enabled",
            "3. Keep the subject line concise and descriptive",
        ]
        
        if self.config.conventional_commits:
            requirements.extend([
                "4. Use appropriate conventional commit prefixes:",
            ])

            # Add custom prefixes if configured
            if self.config.custom_prefixes:
                requirements.append("  Custom commit prefixes:")
                for prefix, description in self.config.custom_prefixes.items():
                    requirements.append(f"   - `{prefix}:` {description}")

        if self.config.max_subject_length:
            requirements.append(f"5. Keep subject line under {self.config.max_subject_length} characters")
        
        if self.config.include_body:
            requirements.append("6. Include a detailed body explaining the changes")
        
        if self.config.include_reasoning:
            requirements.append("7. Include reasoning for the changes when helpful")
        
        return "\n".join(requirements)
    
    def _get_examples_section(self) -> str:
        """Build the examples section."""
        examples = [f"```\n{example}\n```" for example in self.config.example_formats]
        examples = [
            "**Example Formats of Commit Messages (each separated in its own code block):**",
            *examples,
        ]
        
        return "\n".join(examples)


class CommitMessageFormatter:
    """Formats commit messages according to configuration."""
    
    def __init__(self, config: CommitTemplateConfig):
        self.config = config
    
    def format_message(self, raw_message: str) -> str:
        """Format the raw AI-generated message according to configuration."""
        # For now, return as-is, but this could include:
        # - Enforcing length limits
        # - Adding custom prefixes
        # - Reformatting structure
        return remove_backticks(raw_message.strip())