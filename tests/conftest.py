"""Test configuration and fixtures."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock

from smart_commit.config import GlobalConfig


@pytest.fixture
def temp_repo():
    """Create a temporary git repository for testing."""
    import git
    
    temp_dir = Path(tempfile.mkdtemp())
    repo = git.Repo.init(temp_dir)
    
    # Create some basic files
    (temp_dir / "README.md").write_text("# Test Repository\nA test repository.")
    (temp_dir / "main.py").write_text("print('Hello, World!')")
    (temp_dir / "requirements.txt").write_text("requests>=2.25.0\nclick>=8.0.0")
    
    # Add and commit files
    repo.index.add(["README.md", "main.py", "requirements.txt"])
    repo.index.commit("Initial commit")
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    config = GlobalConfig()
    config.ai.api_key = "test-api-key"
    config.ai.provider = "openai"
    config.ai.model = "gpt-4o"
    return config


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "feat: add new feature\n\nImplemented awesome functionality."
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client
