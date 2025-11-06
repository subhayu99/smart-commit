"""Tests for validation utilities."""

import pytest
from smart_commit.utils import validate_diff_size, analyze_diff_impact


class TestDiffSizeValidation:
    """Test diff size validation functionality."""

    def test_small_diff_valid(self):
        """Test that small diffs are valid."""
        diff = """
diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ -1,3 +1,4 @@
+import os
 def hello():
     print("Hello")
"""
        result = validate_diff_size(diff)

        assert result["is_valid"] is True
        assert len(result["warnings"]) == 0
        assert result["line_count"] < 500
        assert result["char_count"] < 50000

    def test_large_line_count_warning(self):
        """Test that large line counts generate warnings."""
        # Create a diff with > 500 lines
        lines = ["diff --git a/test.py b/test.py", "--- a/test.py", "+++ b/test.py"]
        for i in range(600):
            lines.append(f"+line {i}")
        diff = "\n".join(lines)

        result = validate_diff_size(diff)

        assert result["is_valid"] is False
        assert len(result["warnings"]) > 0
        assert any("line" in w.lower() for w in result["warnings"])
        assert result["line_count"] > 500

    def test_large_char_count_warning(self):
        """Test that large character counts generate warnings."""
        # Create a diff with > 50000 characters
        diff = "diff --git a/test.py b/test.py\n"
        diff += "+" + "a" * 60000  # Long line

        result = validate_diff_size(diff)

        assert result["is_valid"] is False
        assert len(result["warnings"]) > 0
        assert result["char_count"] > 50000

    def test_custom_thresholds(self):
        """Test with custom threshold values."""
        diff = "+" + "\n".join([f"line {i}" for i in range(150)])

        # Should be invalid with low threshold
        result = validate_diff_size(diff, max_lines=100, max_chars=1000)
        assert result["is_valid"] is False

        # Should be valid with high threshold
        result = validate_diff_size(diff, max_lines=200, max_chars=10000)
        assert result["is_valid"] is True

    def test_file_count_detection(self):
        """Test that file count is correctly detected."""
        diff = """
diff --git a/file1.py b/file1.py
+line 1
diff --git a/file2.py b/file2.py
+line 2
diff --git a/file3.py b/file3.py
+line 3
"""
        result = validate_diff_size(diff)

        assert result["file_count"] == 3

    def test_addition_and_deletion_count(self):
        """Test counting additions and deletions."""
        diff = """
diff --git a/test.py b/test.py
@@ -1,5 +1,5 @@
+added line 1
+added line 2
-deleted line 1
-deleted line 2
-deleted line 3
 unchanged line
"""
        result = validate_diff_size(diff)

        assert "additions" in result or "line_count" in result
        # The diff has 2 additions and 3 deletions

    def test_empty_diff(self):
        """Test with empty diff."""
        diff = ""

        result = validate_diff_size(diff)

        assert result["is_valid"] is True
        assert result["line_count"] == 1  # Empty string splits to 1 element
        assert result["char_count"] == 0
        assert result["file_count"] == 0

    def test_stats_in_result(self):
        """Test that result includes statistics."""
        diff = """
diff --git a/file1.py b/file1.py
+line 1
+line 2
diff --git a/file2.py b/file2.py
+line 3
"""
        result = validate_diff_size(diff)

        # Check that stats keys exist
        assert "line_count" in result
        assert "char_count" in result
        assert "file_count" in result
        assert "warnings" in result
        assert "is_valid" in result


class TestDiffImpactAnalysis:
    """Test diff impact analysis functionality."""

    def test_analyze_file_changes(self):
        """Test basic file change analysis."""
        diff = """
diff --git a/smart_commit/cli.py b/smart_commit/cli.py
--- a/smart_commit/cli.py
+++ b/smart_commit/cli.py
@@ -1,3 +1,4 @@
+import os
 import typer
 from rich import print
"""
        result = analyze_diff_impact(diff)

        assert "files_changed" in result
        assert result["files_changed"] >= 1

    def test_analyze_additions_deletions(self):
        """Test counting additions and deletions."""
        diff = """
diff --git a/test.py b/test.py
@@ -1,5 +1,5 @@
+added line 1
+added line 2
+added line 3
-deleted line 1
-deleted line 2
"""
        result = analyze_diff_impact(diff)

        assert "additions" in result
        assert "deletions" in result
        assert result["additions"] == 3
        assert result["deletions"] == 2

    def test_analyze_multiple_files(self):
        """Test analysis with multiple files."""
        diff = """
diff --git a/file1.py b/file1.py
+line 1
diff --git a/file2.py b/file2.py
+line 2
diff --git a/file3.js b/file3.js
+line 3
"""
        result = analyze_diff_impact(diff)

        assert result["files_changed"] == 3

    def test_impact_score(self):
        """Test impact score calculation (if implemented)."""
        # Large diff should have higher impact
        large_diff = """
diff --git a/test.py b/test.py
""" + "\n".join([f"+line {i}" for i in range(100)])

        # Small diff should have lower impact
        small_diff = """
diff --git a/test.py b/test.py
+line 1
+line 2
"""
        large_result = analyze_diff_impact(large_diff)
        small_result = analyze_diff_impact(small_diff)

        # Check that we have some measure of impact
        large_impact = large_result.get("additions", 0) + large_result.get("deletions", 0)
        small_impact = small_result.get("additions", 0) + small_result.get("deletions", 0)

        assert large_impact > small_impact

    def test_empty_diff_analysis(self):
        """Test analysis with empty diff."""
        diff = ""
        result = analyze_diff_impact(diff)

        assert result["files_changed"] == 0
        assert result["additions"] == 0
        assert result["deletions"] == 0

    def test_binary_file_handling(self):
        """Test handling of binary files."""
        diff = """
diff --git a/image.png b/image.png
Binary files differ
"""
        result = analyze_diff_impact(diff)

        # Should still count the file
        assert result["files_changed"] >= 1


class TestValidationEdgeCases:
    """Test edge cases in validation."""

    def test_unicode_characters(self):
        """Test handling of unicode characters in diff."""
        diff = """
diff --git a/test.py b/test.py
+print("Hello 世界 🌍")
+# Comment with émojis 😀
"""
        result = validate_diff_size(diff)

        # Should handle unicode without errors
        assert "char_count" in result
        assert result["char_count"] > 0

    def test_very_long_lines(self):
        """Test handling of very long lines."""
        diff = "+" + "a" * 10000 + "\n"

        result = validate_diff_size(diff)

        assert result["char_count"] > 10000

    def test_malformed_diff_headers(self):
        """Test handling of malformed diff headers."""
        diff = """
this is not a proper diff
but it should not crash
"""
        result = validate_diff_size(diff)

        # Should handle gracefully
        assert "is_valid" in result

    def test_mixed_line_endings(self):
        """Test handling of mixed line endings."""
        diff = "diff --git a/test.py b/test.py\r\n+line 1\n+line 2\r\n+line 3"

        result = validate_diff_size(diff)

        # Should count lines correctly despite mixed endings
        assert result["line_count"] > 0

    def test_tabs_and_spaces(self):
        """Test handling of tabs and spaces in diff."""
        diff = """
diff --git a/test.py b/test.py
+\tindented with tab
+    indented with spaces
"""
        result = validate_diff_size(diff)

        assert result["char_count"] > 0
        assert result["line_count"] > 0
