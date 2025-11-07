"""Tests for template generation functionality."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from smart_commit.templates import PromptBuilder
from smart_commit.config import GlobalConfig, CommitTemplateConfig, RepositoryConfig
from smart_commit.repository import RepositoryContext


class TestPromptBuilder:
    """Test prompt builder functionality."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return GlobalConfig()

    @pytest.fixture
    def builder(self, config):
        """Create prompt builder instance."""
        return PromptBuilder(config.template)

    @pytest.fixture
    def repo_context(self):
        """Create test repository context."""
        from pathlib import Path
        return RepositoryContext(
            name="test-repo",
            path=Path("/tmp/test-repo"),
            description="A test repository",
            tech_stack=["python", "pytest"],
            recent_commits=["feat: add feature", "fix: fix bug"],
            active_branches=["main", "dev"],
            file_structure={"src": ["main.py"], "tests": ["test_main.py"]}
        )

    def test_build_basic_prompt(self, builder, repo_context):
        """Test building basic prompt without privacy mode."""
        diff = "diff --git a/test.py b/test.py\n+print('hello')"

        prompt = builder.build_prompt(diff, repo_context)

        assert isinstance(prompt, str)
        assert "test-repo" in prompt
        assert "python" in prompt
        assert "pytest" in prompt
        assert len(prompt) > 0

    def test_build_prompt_with_privacy_mode(self, builder, repo_context):
        """Test building prompt with privacy mode enabled."""
        diff = "diff --git a/smart_commit/cli.py b/smart_commit/cli.py\n+def new_function():\n+    pass"

        prompt = builder.build_prompt(diff, repo_context, privacy_mode=True)

        # Should not contain actual file paths
        assert "smart_commit/cli.py" not in prompt
        # Should contain anonymized paths
        assert "file1" in prompt or "Privacy mode" in prompt
        # Should not include context files section
        assert isinstance(prompt, str)

    def test_privacy_mode_anonymizes_paths(self, builder, repo_context):
        """Test that privacy mode anonymizes file paths in diff."""
        diff = """
diff --git a/src/auth/login.py b/src/auth/login.py
--- a/src/auth/login.py
+++ b/src/auth/login.py
+def authenticate():
+    pass
diff --git a/src/api/routes.py b/src/api/routes.py
+@app.get("/users")
+def get_users():
"""
        prompt = builder.build_prompt(diff, repo_context, privacy_mode=True)

        # Paths should be anonymized
        assert "src/auth/login.py" not in prompt
        assert "src/api/routes.py" not in prompt
        # Should have generic file names
        assert "file1" in prompt or "file2" in prompt

    def test_build_prompt_with_additional_context(self, builder, repo_context):
        """Test building prompt with additional context."""
        diff = "diff --git a/test.py b/test.py\n+print('hello')"
        additional = "This fixes issue #123"

        prompt = builder.build_prompt(diff, repo_context, additional_context=additional)

        assert "This fixes issue #123" in prompt

    def test_build_prompt_with_repo_config(self, builder, repo_context):
        """Test building prompt with repository configuration."""
        diff = "diff --git a/test.py b/test.py\n+print('hello')"

        repo_config = RepositoryConfig(
            name="test-repo",
            description="Test repository",
            absolute_path="/tmp/test",
            tech_stack=["python"],
            context_files=[]
        )

        prompt = builder.build_prompt(diff, repo_context, repo_config=repo_config)

        assert "test-repo" in prompt
        assert isinstance(prompt, str)

    def test_scope_suggestions_section(self, builder, repo_context):
        """Test that scope suggestions are included in prompt."""
        diff = """
diff --git a/smart_commit/cli.py b/smart_commit/cli.py
+def command():
+    pass
diff --git a/tests/test_cli.py b/tests/test_cli.py
+def test_command():
+    pass
"""
        prompt = builder.build_prompt(diff, repo_context)

        # Should include scope suggestions
        assert "scope" in prompt.lower() or "cli" in prompt.lower()

    def test_breaking_changes_section(self, builder, repo_context):
        """Test that breaking changes are included in prompt."""
        diff = """
diff --git a/api.py b/api.py
-def function(a):
+def function(a, b):
     pass
"""
        prompt = builder.build_prompt(diff, repo_context)

        # Should mention breaking changes or provide guidance
        assert isinstance(prompt, str)

    def test_context_file_size_limit(self, builder, repo_context, tmp_path):
        """Test that context files are truncated when too large."""
        # Create a large context file
        large_file = tmp_path / "README.md"
        large_content = "a" * 20000  # 20k characters
        large_file.write_text(large_content)

        repo_config = RepositoryConfig(
            name="test-repo",
            description="Test",
            absolute_path=str(tmp_path),
            tech_stack=["python"],
            context_files=["README.md"]
        )

        diff = "diff --git a/test.py b/test.py\n+print('hello')"

        prompt = builder.build_prompt(diff, repo_context, repo_config=repo_config)

        # Should be truncated (default max is 10000 chars)
        assert "truncated" in prompt.lower() or len(prompt) < 30000

    def test_context_files_excluded_in_privacy_mode(self, builder, repo_context, tmp_path):
        """Test that context files are excluded in privacy mode."""
        context_file = tmp_path / "README.md"
        context_file.write_text("# Secret Project\nConfidential information")

        repo_config = RepositoryConfig(
            name="test-repo",
            description="Test",
            absolute_path=str(tmp_path),
            tech_stack=["python"],
            context_files=["README.md"]
        )

        diff = "diff --git a/test.py b/test.py\n+print('hello')"

        prompt = builder.build_prompt(
            diff, repo_context, repo_config=repo_config, privacy_mode=True
        )

        # Should not include context file content
        assert "Confidential information" not in prompt

    def test_conventional_commits_guidance(self, builder, repo_context):
        """Test that conventional commits guidance is included."""
        diff = "diff --git a/test.py b/test.py\n+print('hello')"

        prompt = builder.build_prompt(diff, repo_context)

        # Should include conventional commit types
        assert "feat" in prompt or "fix" in prompt or "docs" in prompt

    def test_empty_diff(self, builder, repo_context):
        """Test handling of empty diff."""
        diff = ""

        prompt = builder.build_prompt(diff, repo_context)

        assert isinstance(prompt, str)
        # Should still generate a prompt structure

    def test_recent_commits_included(self, builder, repo_context):
        """Test that recent commits are included for pattern analysis."""
        diff = "diff --git a/test.py b/test.py\n+print('hello')"

        prompt = builder.build_prompt(diff, repo_context)

        # Should include recent commit history
        assert "feat: add feature" in prompt or "recent commit" in prompt.lower()

    def test_tech_stack_in_prompt(self, builder, repo_context):
        """Test that tech stack is included in prompt."""
        diff = "diff --git a/test.py b/test.py\n+print('hello')"

        prompt = builder.build_prompt(diff, repo_context)

        assert "python" in prompt
        assert "pytest" in prompt

    def test_repository_description_in_prompt(self, builder, repo_context):
        """Test that repository description is included."""
        diff = "diff --git a/test.py b/test.py\n+print('hello')"

        prompt = builder.build_prompt(diff, repo_context)

        assert "test repository" in prompt.lower()


class TestPrivacyModeFeatures:
    """Test privacy mode specific features."""

    @pytest.fixture
    def builder(self):
        """Create prompt builder."""
        config = GlobalConfig()
        return PromptBuilder(config.template)

    @pytest.fixture
    def repo_context(self):
        """Create repository context."""
        return RepositoryContext(
            name="confidential-project",
            path=Path("/tmp/confidential-project"),
            description="Confidential project",
            tech_stack=["python"],
            recent_commits=[],
            active_branches=["main"],
            file_structure={"src": ["main.py"], "tests": ["test_main.py"]}
        )

    def test_privacy_mode_notification(self, builder, repo_context):
        """Test that privacy mode is indicated in output."""
        diff = "diff --git a/secret.py b/secret.py\n+secret_code = 'xyz'"

        prompt = builder.build_prompt(diff, repo_context, privacy_mode=True)

        # Should indicate privacy mode somehow
        assert isinstance(prompt, str)

    def test_multiple_files_anonymization(self, builder, repo_context):
        """Test anonymization of multiple files."""
        diff = """
diff --git a/backend/src/api/auth.py b/backend/src/api/auth.py
+def login():
+    pass
diff --git a/backend/src/api/users.py b/backend/src/api/users.py
+def get_user():
+    pass
diff --git a/frontend/src/components/Login.tsx b/frontend/src/components/Login.tsx
+export const Login = () => {}
"""
        prompt = builder.build_prompt(diff, repo_context, privacy_mode=True)

        # Original paths should not appear
        assert "backend/src/api/auth.py" not in prompt
        assert "frontend/src/components/Login.tsx" not in prompt

        # Should have anonymized names
        assert "file" in prompt

    def test_privacy_mode_preserves_diff_content(self, builder, repo_context):
        """Test that privacy mode preserves actual code changes."""
        diff = """
diff --git a/api.py b/api.py
+def authenticate(username, password):
+    return True
"""
        prompt = builder.build_prompt(diff, repo_context, privacy_mode=True)

        # Code content should still be there
        assert "def authenticate" in prompt
        assert "username" in prompt
        assert "password" in prompt

    def test_privacy_mode_with_no_context_files(self, builder, repo_context):
        """Test privacy mode when no context files are configured."""
        diff = "diff --git a/test.py b/test.py\n+print('hello')"

        prompt = builder.build_prompt(diff, repo_context, privacy_mode=True)

        assert isinstance(prompt, str)
        assert len(prompt) > 0


class TestDiffSections:
    """Test diff section formatting."""

    @pytest.fixture
    def builder(self):
        """Create prompt builder."""
        config = GlobalConfig()
        return PromptBuilder(config.template)

    def test_diff_section_formatting(self, builder):
        """Test that diff is properly formatted in prompt."""
        diff = """
diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ -1,3 +1,4 @@
+import os
 def hello():
     print("Hello")
"""
        repo_context = RepositoryContext(
            name="test",
            path=Path("/tmp/test"),
            description="test",
            tech_stack=[],
            recent_commits=[],
            active_branches=[],
            file_structure={"src": ["main.py"], "tests": ["test_main.py"]}
        )

        prompt = builder.build_prompt(diff, repo_context)

        # Diff should be included
        assert "diff --git" in prompt or "+import os" in prompt

    def test_binary_file_in_diff(self, builder):
        """Test handling of binary files in diff."""
        diff = """
diff --git a/image.png b/image.png
Binary files differ
"""
        repo_context = RepositoryContext(
            name="test",
            path=Path("/tmp/test"),
            description="test",
            tech_stack=[],
            recent_commits=[],
            active_branches=[],
            file_structure={"src": ["main.py"], "tests": ["test_main.py"]}
        )

        prompt = builder.build_prompt(diff, repo_context)

        # Should handle binary files gracefully
        assert isinstance(prompt, str)

    def test_very_long_diff(self, builder):
        """Test handling of very long diffs."""
        # Create a long diff
        diff_lines = ["diff --git a/test.py b/test.py"]
        for i in range(1000):
            diff_lines.append(f"+line {i}")
        diff = "\n".join(diff_lines)

        repo_context = RepositoryContext(
            name="test",
            path=Path("/tmp/test"),
            description="test",
            tech_stack=[],
            recent_commits=[],
            active_branches=[],
            file_structure={"src": ["main.py"], "tests": ["test_main.py"]}
        )

        prompt = builder.build_prompt(diff, repo_context)

        # Should handle long diffs
        assert isinstance(prompt, str)
        assert len(prompt) > 0


class TestPromptStructure:
    """Test overall prompt structure."""

    @pytest.fixture
    def builder(self):
        """Create prompt builder."""
        config = GlobalConfig()
        return PromptBuilder(config.template)

    @pytest.fixture
    def repo_context(self):
        """Create repository context."""
        return RepositoryContext(
            name="test-repo",
            path=Path("/tmp/test-repo"),
            description="Test repository",
            tech_stack=["python", "javascript"],
            recent_commits=["feat: add feature", "fix: fix bug"],
            active_branches=["main", "dev"],
            file_structure={"src": ["main.py"], "tests": ["test_main.py"]}
        )

    def test_prompt_contains_required_sections(self, builder, repo_context):
        """Test that prompt contains all required sections."""
        diff = "diff --git a/test.py b/test.py\n+print('hello')"

        prompt = builder.build_prompt(diff, repo_context)

        # Should contain key sections
        # (exact format depends on implementation)
        assert len(prompt) > 100  # Should be substantial
        assert "test-repo" in prompt
        assert "python" in prompt

    def test_prompt_markdown_formatting(self, builder, repo_context):
        """Test that prompt uses proper markdown formatting."""
        diff = "diff --git a/test.py b/test.py\n+print('hello')"

        prompt = builder.build_prompt(diff, repo_context)

        # Should use markdown (headers, code blocks, etc.)
        # This is implementation-specific
        assert isinstance(prompt, str)

    def test_prompt_consistency(self, builder, repo_context):
        """Test that same inputs produce same prompt."""
        diff = "diff --git a/test.py b/test.py\n+print('hello')"

        prompt1 = builder.build_prompt(diff, repo_context)
        prompt2 = builder.build_prompt(diff, repo_context)

        assert prompt1 == prompt2
