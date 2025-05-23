"""Tests for repository analysis."""

import pytest
from pathlib import Path

from smart_commit.repository import RepositoryAnalyzer


class TestRepositoryAnalyzer:
    """Test repository analyzer."""
    
    def test_analyze_repository(self, temp_repo):
        """Test basic repository analysis."""
        analyzer = RepositoryAnalyzer(temp_repo)
        context = analyzer.get_context()
        
        assert context.name
        assert context.path == Path(temp_repo)
        assert "python" in context.tech_stack
        assert len(context.recent_commits) > 0
    
    def test_detect_tech_stack(self, temp_repo):
        """Test technology stack detection."""
        analyzer = RepositoryAnalyzer(temp_repo)
        context = analyzer.get_context()
        
        # Should detect Python from requirements.txt and .py files
        assert "python" in context.tech_stack
    
    def test_get_repo_description(self, temp_repo):
        """Test repository description extraction."""
        analyzer = RepositoryAnalyzer(temp_repo)
        context = analyzer.get_context()
        
        # Should extract description from README.md
        assert "test repository" in context.description.lower()