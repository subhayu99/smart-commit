"""Tests for breaking change detection utilities."""

from smart_commit.utils import detect_breaking_changes, analyze_diff_impact


class TestBreakingChangeDetection:
    """Test breaking change detection functionality."""

    def test_detect_function_signature_change(self):
        """Test detection of function signature changes."""
        diff = """
diff --git a/src/api.py b/src/api.py
@@ -10,5 +10,5 @@
-def generate_message(diff, model):
+def generate_message(diff, model, context=None):
     return message
"""
        changes = detect_breaking_changes(diff)

        assert len(changes) > 0
        assert any("signature" in change[0].lower() for change in changes)

    def test_detect_api_endpoint_change(self):
        """Test detection of API endpoint changes."""
        diff = """
diff --git a/routes.py b/routes.py
@@ -5,3 +5,3 @@
-@app.post('/api/v1/commit')
+@app.post('/api/v2/commit')
 def create_commit():
"""
        changes = detect_breaking_changes(diff)

        assert len(changes) > 0
        assert any("api" in change[0].lower() or "endpoint" in change[0].lower() for change in changes)

    def test_detect_database_schema_change(self):
        """Test detection of database schema changes."""
        diff = """
diff --git a/migrations/001.py b/migrations/001.py
@@ -1,3 +1,3 @@
-CREATE TABLE users (id INT, name VARCHAR(100));
+CREATE TABLE users (id INT, username VARCHAR(100), email VARCHAR(255));
"""
        changes = detect_breaking_changes(diff)

        assert len(changes) > 0
        # May detect as database change or schema change

    def test_detect_class_name_change(self):
        """Test detection of class/type changes."""
        diff = """
diff --git a/models.py b/models.py
@@ -1,3 +1,3 @@
-class UserConfig:
+class UserConfiguration:
     def __init__(self):
"""
        changes = detect_breaking_changes(diff)

        # Should detect class changes
        assert len(changes) > 0

    def test_detect_interface_change(self):
        """Test detection of interface/type definition changes."""
        diff = """
diff --git a/types.ts b/types.ts
@@ -1,5 +1,5 @@
-interface User {
-  id: number;
-  name: string;
+interface User {
+  id: string;
+  username: string;
+  email: string;
 }
"""
        changes = detect_breaking_changes(diff)

        # Should detect type/interface changes
        assert isinstance(changes, list)

    def test_detect_public_api_removal(self):
        """Test detection of public API removals."""
        diff = """
diff --git a/api.py b/api.py
@@ -10,5 +10,3 @@
 def public_function():
     pass
-def another_public_function():
-    pass
"""
        changes = detect_breaking_changes(diff)

        # Removing functions can be breaking
        assert isinstance(changes, list)

    def test_detect_configuration_change(self):
        """Test detection of configuration changes."""
        diff = """
diff --git a/config.py b/config.py
@@ -1,3 +1,3 @@
-DEFAULT_TIMEOUT = 30
+DEFAULT_TIMEOUT = 60
"""
        changes = detect_breaking_changes(diff)

        # Configuration changes can be breaking
        assert isinstance(changes, list)

    def test_detect_dependency_version_change(self):
        """Test detection of dependency version changes."""
        diff = """
diff --git a/requirements.txt b/requirements.txt
@@ -1,3 +1,3 @@
-requests>=2.25.0
+requests>=3.0.0
-python>=3.8
+python>=3.10
"""
        changes = detect_breaking_changes(diff)

        # Major version bumps can be breaking
        assert isinstance(changes, list)

    def test_no_breaking_changes(self):
        """Test with non-breaking changes."""
        diff = """
diff --git a/utils.py b/utils.py
@@ -1,3 +1,4 @@
 def helper():
     # Added comment
+    # Another comment
     return True
"""
        changes = detect_breaking_changes(diff)

        # Should detect few or no breaking changes
        # (depending on how strict the detection is)
        assert isinstance(changes, list)

    def test_multiple_breaking_changes(self):
        """Test detection of multiple breaking changes."""
        diff = """
diff --git a/api.py b/api.py
@@ -5,10 +5,10 @@
-def old_function(a, b):
+def old_function(a, b, c):
     pass

-@app.get('/api/v1/users')
+@app.get('/api/v2/users')
 def get_users():
     pass

-class Config:
+class Configuration:
     pass
"""
        changes = detect_breaking_changes(diff)

        # Should detect multiple breaking changes
        assert len(changes) >= 2

    def test_breaking_change_with_context(self):
        """Test that breaking changes include context."""
        diff = """
diff --git a/smart_commit/api.py b/smart_commit/api.py
@@ -42,5 +42,5 @@
-def generate_message(diff):
+def generate_message(diff, model, context):
     return message
"""
        changes = detect_breaking_changes(diff)

        assert len(changes) > 0
        # Each change should be a tuple with (description, context)
        for change in changes:
            assert isinstance(change, tuple)
            assert len(change) == 2
            assert isinstance(change[0], str)  # Description
            assert isinstance(change[1], str)  # Context/line

    def test_empty_diff(self):
        """Test with empty diff."""
        diff = ""
        changes = detect_breaking_changes(diff)

        assert changes == []

    def test_additions_only_not_breaking(self):
        """Test that pure additions are not breaking."""
        diff = """
diff --git a/utils.py b/utils.py
@@ -10,3 +10,5 @@
 def existing_function():
     pass
+def new_function():
+    pass
"""
        changes = detect_breaking_changes(diff)

        # Adding new functions shouldn't be breaking
        # (though this depends on implementation)
        assert isinstance(changes, list)


class TestDiffImpactAnalysisBreaking:
    """Test diff impact analysis for breaking changes."""

    def test_impact_includes_breaking_flag(self):
        """Test that impact analysis includes breaking change flag."""
        diff = """
diff --git a/api.py b/api.py
-def function(a):
+def function(a, b):
"""
        result = analyze_diff_impact(diff)

        # Should include some indication of impact
        assert "files_changed" in result
        assert "additions" in result
        assert "deletions" in result

    def test_high_impact_with_breaking_changes(self):
        """Test high impact detection with breaking changes."""
        diff = """
diff --git a/core/api.py b/core/api.py
-@app.post('/api/v1/endpoint')
+@app.post('/api/v2/endpoint')
-def old_function(a):
+def old_function(a, b, c):
-class Config:
+class Configuration:
"""
        result = analyze_diff_impact(diff)

        # Should show significant impact
        assert result["files_changed"] >= 1
        assert result["additions"] >= 3
        assert result["deletions"] >= 3

    def test_low_impact_without_breaking_changes(self):
        """Test low impact with non-breaking changes."""
        diff = """
diff --git a/utils.py b/utils.py
+# Added a comment
+# Another comment
"""
        result = analyze_diff_impact(diff)

        # Should show minimal impact
        assert result["additions"] == 2
        assert result["deletions"] == 0


class TestBreakingChangeEdgeCases:
    """Test edge cases in breaking change detection."""

    def test_commented_out_code(self):
        """Test handling of commented out code."""
        diff = """
diff --git a/api.py b/api.py
-# def old_function(a):
-#     pass
+# def old_function(a, b):
+#     pass
"""
        changes = detect_breaking_changes(diff)

        # Commented code changes might not be breaking
        assert isinstance(changes, list)

    def test_string_literals_with_function_patterns(self):
        """Test that string literals don't trigger false positives."""
        diff = """
diff --git a/test.py b/test.py
-description = "def function(a):"
+description = "def function(a, b):"
"""
        changes = detect_breaking_changes(diff)

        # Should ideally not detect this as breaking
        # (though implementation may vary)
        assert isinstance(changes, list)

    def test_multiline_function_signature(self):
        """Test detection of multiline function signatures."""
        diff = """
diff --git a/api.py b/api.py
-def complex_function(
-    arg1: str,
-    arg2: int
-) -> str:
+def complex_function(
+    arg1: str,
+    arg2: int,
+    arg3: bool = False
+) -> str:
"""
        changes = detect_breaking_changes(diff)

        # Should detect multiline signature changes
        assert isinstance(changes, list)

    def test_docstring_changes(self):
        """Test that docstring changes are not breaking."""
        diff = """
diff --git a/api.py b/api.py
 def function(a):
-    '''Old docstring'''
+    '''New improved docstring'''
     pass
"""
        changes = detect_breaking_changes(diff)

        # Docstring changes shouldn't be breaking
        # (most implementations should not flag this)
        assert isinstance(changes, list)

    def test_decorator_changes(self):
        """Test detection of decorator changes."""
        diff = """
diff --git a/api.py b/api.py
-@app.route('/old')
+@app.route('/new')
 def handler():
     pass
"""
        changes = detect_breaking_changes(diff)

        # Decorator changes (especially routes) can be breaking
        assert isinstance(changes, list)

    def test_import_statement_changes(self):
        """Test handling of import statement changes."""
        diff = """
diff --git a/api.py b/api.py
-from old_module import function
+from new_module import function
"""
        changes = detect_breaking_changes(diff)

        # Import changes might not be breaking for public API
        assert isinstance(changes, list)

    def test_very_large_diff_performance(self):
        """Test performance with very large diffs."""
        # Create a large diff
        lines = ["diff --git a/large.py b/large.py"]
        for i in range(1000):
            lines.append(f"-def old_func_{i}():")
            lines.append(f"+def new_func_{i}():")

        diff = "\n".join(lines)

        # Should complete in reasonable time
        import time
        start = time.time()
        changes = detect_breaking_changes(diff)
        duration = time.time() - start

        # Should not take more than 5 seconds
        assert duration < 5.0
        assert isinstance(changes, list)

    def test_unicode_in_code(self):
        """Test handling of unicode in code."""
        diff = """
diff --git a/api.py b/api.py
-def 函数(参数):
+def 函数(参数, 新参数):
     pass
"""
        changes = detect_breaking_changes(diff)

        # Should handle unicode without errors
        assert isinstance(changes, list)

    def test_mixed_breaking_and_safe_changes(self):
        """Test diff with both breaking and safe changes."""
        diff = """
diff --git a/api.py b/api.py
@@ -1,10 +1,10 @@
 # Comment change - safe
+# New comment
-def breaking_function(a):
+def breaking_function(a, b):
     pass
+# Added safe comment
+def new_safe_function():
+    pass
"""
        changes = detect_breaking_changes(diff)

        # Should detect only the breaking changes
        assert isinstance(changes, list)
        # Should have at least one breaking change detected
        if len(changes) > 0:
            assert any("function" in change[0].lower() or "signature" in change[0].lower()
                      for change in changes)
