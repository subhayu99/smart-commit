"""Commit message templates and formatters."""

from dataclasses import dataclass
from typing import List, Optional

from smart_commit.config import CommitTemplateConfig, RepositoryConfig
from smart_commit.repository import RepositoryContext


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
        
        prompt_parts = [
            self._get_system_prompt(),
            self._get_repository_context_section(repo_context, repo_config),
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
        
        if repo_context.description:
            context_parts.append(f"- **Description:** {repo_context.description}")
        
        if isinstance(repo_context.tech_stack, list):
            context_parts.append(f"- **Tech Stack:** {', '.join(repo_context.tech_stack)}")
        
        if isinstance(repo_context.recent_commits, list):
            context_parts.append("- **Recent Commits:**")
            for commit in repo_context.recent_commits[:5]:
                context_parts.append(f"  - {commit}")
        
        if repo_config and repo_config.commit_conventions:
            context_parts.append("- **Project Conventions:**")
            for key, value in repo_config.commit_conventions.items():
                context_parts.append(f"  - {key}: {value}")
        
        return "\n".join(context_parts)
    
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
                "   - `feat:` for new features",
                "   - `fix:` for bug fixes", 
                "   - `docs:` for documentation changes",
                "   - `style:` for formatting changes",
                "   - `refactor:` for code refactoring",
                "   - `test:` for test changes",
                "   - `chore:` for maintenance tasks",
                "   - `perf:` for performance improvements",
                "   - `build:` for build system changes",
                "   - `ci:` for CI/CD changes",
            ])
        
        if self.config.max_subject_length:
            requirements.append(f"5. Keep subject line under {self.config.max_subject_length} characters")
        
        if self.config.include_body:
            requirements.append("6. Include a detailed body explaining the changes")
        
        if self.config.include_reasoning:
            requirements.append("7. Include reasoning for the changes when helpful")
        
        return "\n".join(requirements)
    
    def _get_examples_section(self) -> str:
        """Build the examples section."""
        examples = [
            "**Example Format:**",
            "```",
            "feat: add user authentication system",
            "",
            "- Implement JWT-based authentication",
            "- Add login and logout endpoints", 
            "- Include password hashing with bcrypt",
            "- Add authentication middleware for protected routes",
            "",
            "This enables secure user sessions and protects sensitive endpoints",
            "from unauthorized access.",
            "```"
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
        return raw_message.strip()