"""Tests for scope detection utilities."""

import pytest
from smart_commit.utils import detect_scope_from_diff


class TestScopeDetection:
    """Test scope detection from diff."""

    def test_detect_cli_scope(self):
        """Test detection of CLI-related scope."""
        diff = """
diff --git a/smart_commit/cli.py b/smart_commit/cli.py
+def new_command():
+    pass
"""
        scopes = detect_scope_from_diff(diff)

        assert "cli" in scopes

    def test_detect_api_scope(self):
        """Test detection of API-related scope."""
        diff = """
diff --git a/src/api/routes.py b/src/api/routes.py
+@app.get("/endpoint")
+def endpoint():
+    pass
diff --git a/src/controllers/api_controller.py b/src/controllers/api_controller.py
+def handle_request():
+    pass
"""
        scopes = detect_scope_from_diff(diff)

        assert "api" in scopes

    def test_detect_docs_scope(self):
        """Test detection of documentation scope."""
        diff = """
diff --git a/README.md b/README.md
+## New Section
diff --git a/docs/guide.md b/docs/guide.md
+Documentation update
"""
        scopes = detect_scope_from_diff(diff)

        assert "docs" in scopes

    def test_detect_auth_scope(self):
        """Test detection of authentication scope."""
        diff = """
diff --git a/src/auth/login.py b/src/auth/login.py
+def authenticate():
+    pass
diff --git a/middleware/authentication.py b/middleware/authentication.py
+def verify_token():
+    pass
"""
        scopes = detect_scope_from_diff(diff)

        assert "auth" in scopes

    def test_detect_database_scope(self):
        """Test detection of database scope."""
        diff = """
diff --git a/migrations/001_create_users.py b/migrations/001_create_users.py
+CREATE TABLE users
diff --git a/src/db/models.py b/src/db/models.py
+class User(Model):
+    pass
"""
        scopes = detect_scope_from_diff(diff)

        assert "database" in scopes

    def test_detect_ui_scope(self):
        """Test detection of UI scope."""
        diff = """
diff --git a/src/components/Button.tsx b/src/components/Button.tsx
+export const Button = () => {}
diff --git a/src/views/HomePage.vue b/src/views/HomePage.vue
+<template>
"""
        scopes = detect_scope_from_diff(diff)

        assert "ui" in scopes

    def test_detect_config_scope(self):
        """Test detection of configuration scope."""
        diff = """
diff --git a/smart_commit/config.py b/smart_commit/config.py
+class Config:
+    pass
diff --git a/settings/production.py b/settings/production.py
+DEBUG = False
"""
        scopes = detect_scope_from_diff(diff)

        assert "config" in scopes

    def test_detect_tests_scope(self):
        """Test detection of tests scope."""
        diff = """
diff --git a/tests/test_main.py b/tests/test_main.py
+def test_feature():
+    pass
diff --git a/test/unit/test_utils.py b/test/unit/test_utils.py
+def test_util():
+    pass
"""
        scopes = detect_scope_from_diff(diff)

        assert "tests" in scopes

    def test_detect_utils_scope(self):
        """Test detection of utils scope."""
        diff = """
diff --git a/smart_commit/utils.py b/smart_commit/utils.py
+def helper_function():
+    pass
diff --git a/src/helpers/string_utils.py b/src/helpers/string_utils.py
+def format_string():
+    pass
"""
        scopes = detect_scope_from_diff(diff)

        assert "utils" in scopes

    def test_detect_styles_scope(self):
        """Test detection of styles scope."""
        diff = """
diff --git a/src/styles/main.css b/src/styles/main.css
+.button { color: blue; }
diff --git a/src/components/Button.scss b/src/components/Button.scss
+.btn { margin: 0; }
"""
        scopes = detect_scope_from_diff(diff)

        assert "styles" in scopes

    def test_multiple_scopes_detected(self):
        """Test detection of multiple scopes."""
        diff = """
diff --git a/smart_commit/cli.py b/smart_commit/cli.py
+def command():
+    pass
diff --git a/smart_commit/config.py b/smart_commit/config.py
+class Config:
+    pass
diff --git a/tests/test_cli.py b/tests/test_cli.py
+def test_cli():
+    pass
"""
        scopes = detect_scope_from_diff(diff)

        # Should detect cli, config, and tests
        assert "cli" in scopes
        assert "config" in scopes
        assert "tests" in scopes

    def test_top_5_scopes_limit(self):
        """Test that only top 5 scopes are returned."""
        diff = """
diff --git a/cli.py b/cli.py
diff --git a/api.py b/api.py
diff --git a/docs/guide.md b/docs/guide.md
diff --git a/auth/login.py b/auth/login.py
diff --git a/db/models.py b/db/models.py
diff --git a/components/Button.tsx b/components/Button.tsx
diff --git a/config.py b/config.py
diff --git a/tests/test.py b/tests/test.py
diff --git a/utils.py b/utils.py
diff --git a/styles/main.css b/styles/main.css
"""
        scopes = detect_scope_from_diff(diff)

        # Should return at most 5 scopes
        assert len(scopes) <= 5

    def test_case_insensitive_detection(self):
        """Test case-insensitive scope detection."""
        diff = """
diff --git a/SRC/API/Routes.PY b/SRC/API/Routes.PY
diff --git a/TESTS/TEST_Main.py b/TESTS/TEST_Main.py
"""
        scopes = detect_scope_from_diff(diff)

        # Should detect scopes regardless of case
        assert "api" in scopes or "tests" in scopes

    def test_nested_directories(self):
        """Test scope detection in nested directories."""
        diff = """
diff --git a/backend/src/api/v1/routes.py b/backend/src/api/v1/routes.py
diff --git a/frontend/src/components/ui/Button.tsx b/frontend/src/components/ui/Button.tsx
"""
        scopes = detect_scope_from_diff(diff)

        # Should detect scopes from nested paths
        assert "api" in scopes
        assert "ui" in scopes

    def test_scope_priority_by_frequency(self):
        """Test that more frequent scopes appear first."""
        diff = """
diff --git a/tests/test_1.py b/tests/test_1.py
diff --git a/tests/test_2.py b/tests/test_2.py
diff --git a/tests/test_3.py b/tests/test_3.py
diff --git a/cli.py b/cli.py
"""
        scopes = detect_scope_from_diff(diff)

        # 'tests' appears 3 times, 'cli' appears once
        # So 'tests' should come before 'cli'
        if "tests" in scopes and "cli" in scopes:
            assert scopes.index("tests") < scopes.index("cli")

    def test_no_clear_scope(self):
        """Test with files that don't match any clear scope."""
        diff = """
diff --git a/random_file.txt b/random_file.txt
diff --git a/data.json b/data.json
"""
        scopes = detect_scope_from_diff(diff)

        # Should return empty list or generic scopes
        # (depending on implementation)
        assert isinstance(scopes, list)

    def test_empty_diff(self):
        """Test with empty diff."""
        diff = ""
        scopes = detect_scope_from_diff(diff)

        assert scopes == []

    def test_scope_from_filename_only(self):
        """Test scope detection from filename patterns."""
        diff = """
diff --git a/authentication.py b/authentication.py
diff --git a/database.py b/database.py
"""
        scopes = detect_scope_from_diff(diff)

        # Should detect scopes from filenames
        assert "auth" in scopes or "database" in scopes

    def test_specialized_file_extensions(self):
        """Test scope detection based on file extensions."""
        diff = """
diff --git a/component.jsx b/component.jsx
diff --git a/styles.scss b/styles.scss
diff --git a/test.spec.js b/test.spec.js
"""
        scopes = detect_scope_from_diff(diff)

        # Should infer scopes from extensions
        # .spec.js -> tests, .scss -> styles
        assert "styles" in scopes or "tests" in scopes or "ui" in scopes


class TestScopeDetectionEdgeCases:
    """Test edge cases in scope detection."""

    def test_malformed_diff_headers(self):
        """Test handling of malformed diff headers."""
        diff = """
this is not a proper diff
random text
"""
        scopes = detect_scope_from_diff(diff)

        # Should handle gracefully without errors
        assert isinstance(scopes, list)

    def test_unicode_in_filenames(self):
        """Test handling of unicode in filenames."""
        diff = """
diff --git a/src/文件.py b/src/文件.py
diff --git a/docs/ドキュメント.md b/docs/ドキュメント.md
"""
        scopes = detect_scope_from_diff(diff)

        # Should handle unicode filenames
        assert "docs" in scopes

    def test_spaces_in_filenames(self):
        """Test handling of spaces in filenames."""
        diff = """
diff --git a/my api file.py b/my api file.py
diff --git a/test file.py b/test file.py
"""
        scopes = detect_scope_from_diff(diff)

        # Should detect scopes despite spaces
        assert "api" in scopes or "tests" in scopes

    def test_very_long_filenames(self):
        """Test handling of very long filenames."""
        long_name = "a" * 500
        diff = f"""
diff --git a/cli_{long_name}.py b/cli_{long_name}.py
"""
        scopes = detect_scope_from_diff(diff)

        # Should handle long names without errors
        assert "cli" in scopes

    def test_special_characters_in_path(self):
        """Test handling of special characters in paths."""
        diff = """
diff --git a/src/@types/api.ts b/src/@types/api.ts
diff --git a/tests/[utils].test.js b/tests/[utils].test.js
"""
        scopes = detect_scope_from_diff(diff)

        # Should detect scopes despite special chars
        assert "api" in scopes or "tests" in scopes
