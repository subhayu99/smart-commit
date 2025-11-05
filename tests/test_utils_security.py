"""Tests for security-related utilities."""

import pytest
from smart_commit.utils import (
    detect_sensitive_data,
    check_sensitive_files,
    SENSITIVE_PATTERNS
)


class TestSensitiveDataDetection:
    """Test sensitive data detection functionality."""

    def test_detect_aws_access_key(self):
        """Test detection of AWS access keys."""
        diff = """
+AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
+SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
"""
        findings = detect_sensitive_data(diff)

        assert len(findings) > 0
        # Check that AWS key was detected
        aws_findings = [f for f in findings if f[0] == "AWS Access Key"]
        assert len(aws_findings) == 1
        assert "AKIA" in aws_findings[0][1]
        assert "..." in aws_findings[0][1]  # Should be masked

    def test_detect_github_token(self):
        """Test detection of GitHub tokens."""
        diff = """
+GITHUB_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwx
+export GH_TOKEN=gho_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh
"""
        findings = detect_sensitive_data(diff)

        assert len(findings) >= 2
        gh_findings = [f for f in findings if f[0] == "GitHub Token"]
        assert len(gh_findings) == 2

    def test_detect_jwt_token(self):
        """Test detection of JWT tokens."""
        diff = """
+token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
"""
        findings = detect_sensitive_data(diff)

        assert len(findings) > 0
        jwt_findings = [f for f in findings if f[0] == "JWT Token"]
        assert len(jwt_findings) == 1

    def test_detect_private_key(self):
        """Test detection of private keys."""
        diff = """
+-----BEGIN RSA PRIVATE KEY-----
+MIIEpAIBAAKCAQEAr7eUSQwxJO5UQ8JEAGx4KtnjPIvR5fy2YSz8iqr...
+-----END RSA PRIVATE KEY-----
"""
        findings = detect_sensitive_data(diff)

        assert len(findings) > 0
        key_findings = [f for f in findings if "Private Key" in f[0]]
        assert len(key_findings) == 1

    def test_detect_api_key(self):
        """Test detection of generic API keys."""
        diff = """
+API_KEY=api_FAKE1234567890abcdefghijklmnopqrstuvwxyz
+api_key: "AIzaSyD-TEST-FAKE1234567890abcdefghij"
"""
        findings = detect_sensitive_data(diff)

        assert len(findings) >= 2

    def test_detect_database_connection_string(self):
        """Test detection of database connection strings."""
        diff = """
+DATABASE_URL=postgresql://user:password123@localhost:5432/mydb
+MONGO_URI=mongodb://admin:secret@cluster0.mongodb.net/test
"""
        findings = detect_sensitive_data(diff)

        assert len(findings) >= 2
        db_findings = [f for f in findings if "Database" in f[0] or "Password" in f[0]]
        assert len(db_findings) >= 2

    def test_detect_slack_token(self):
        """Test detection of Slack tokens."""
        # Using obviously fake token that won't trigger GitHub protection
        diff = """
+SLACK_TOKEN=xoxb-TEST1234567890-TEST1234567890-FAKE_TEST_TOKEN_abcdef
+SLACK_WEBHOOK=https://hooks.slack.com/services/TXXXXXXXX/BXXXXXXXX/FAKE_WEBHOOK_TOKEN
"""
        findings = detect_sensitive_data(diff)

        assert len(findings) >= 1
        slack_findings = [f for f in findings if "Slack" in f[0] or "Token" in f[0]]
        assert len(slack_findings) >= 1

    def test_detect_stripe_key(self):
        """Test detection of Stripe keys."""
        # Using test mode keys to avoid GitHub secret detection
        diff = """
+STRIPE_SECRET_KEY=sk_test_FAKE1234567890abcdefghijklmn
+STRIPE_PUBLISHABLE_KEY=pk_test_FAKE1234567890abcdefgh
"""
        findings = detect_sensitive_data(diff)

        assert len(findings) >= 2
        stripe_findings = [f for f in findings if "Stripe" in f[0] or "API Key" in f[0]]
        assert len(stripe_findings) >= 1

    def test_detect_google_api_key(self):
        """Test detection of Google API keys."""
        diff = """
+GOOGLE_API_KEY=AIzaSyD1234567890abcdefghijklmnopqrstuvwxy
"""
        findings = detect_sensitive_data(diff)

        assert len(findings) > 0
        google_findings = [f for f in findings if "Google" in f[0]]
        assert len(google_findings) == 1

    def test_detect_bearer_token(self):
        """Test detection of Bearer tokens."""
        diff = """
+Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature
"""
        findings = detect_sensitive_data(diff)

        assert len(findings) > 0
        bearer_findings = [f for f in findings if "Bearer Token" in f[0]]
        assert len(bearer_findings) == 1

    def test_masking_in_findings(self):
        """Test that findings are properly masked."""
        diff = "+AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
        findings = detect_sensitive_data(diff)

        assert len(findings) > 0
        masked_text = findings[0][1]
        # Should show beginning and end but mask middle
        assert "AKIA" in masked_text
        assert "..." in masked_text
        assert len(masked_text) < len("AKIAIOSFODNN7EXAMPLE")

    def test_line_numbers(self):
        """Test that line numbers are correctly reported."""
        diff = """line 1
line 2
+AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
line 4
+GITHUB_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwx
"""
        findings = detect_sensitive_data(diff)

        assert len(findings) >= 2
        # Line numbers should be 3 and 5
        line_numbers = [f[2] for f in findings]
        assert 3 in line_numbers
        assert 5 in line_numbers

    def test_no_false_positives_short_strings(self):
        """Test that short strings don't trigger false positives."""
        diff = """
+key=abc
+token=xyz
+password=short
"""
        findings = detect_sensitive_data(diff)

        # Should not detect very short strings
        assert len(findings) == 0

    def test_clean_diff(self):
        """Test with clean diff (no secrets)."""
        diff = """
+def hello_world():
+    print("Hello, World!")
+    return True
"""
        findings = detect_sensitive_data(diff)

        assert len(findings) == 0


class TestSensitiveFileDetection:
    """Test sensitive file detection functionality."""

    def test_detect_env_file(self):
        """Test detection of .env files."""
        diff = """
diff --git a/.env b/.env
new file mode 100644
+DATABASE_URL=postgres://localhost/db
"""
        findings = check_sensitive_files(diff)

        assert len(findings) > 0
        assert ".env" in findings[0]

    def test_detect_env_variants(self):
        """Test detection of .env.* variants."""
        diff = """
diff --git a/.env.production b/.env.production
diff --git a/.env.local b/.env.local
"""
        findings = check_sensitive_files(diff)

        assert len(findings) >= 2
        assert any(".env.production" in f for f in findings)
        assert any(".env.local" in f for f in findings)

    def test_detect_credentials_json(self):
        """Test detection of credentials.json."""
        diff = """
diff --git a/config/credentials.json b/config/credentials.json
new file mode 100644
"""
        findings = check_sensitive_files(diff)

        assert len(findings) > 0
        assert "credentials.json" in findings[0]

    def test_detect_secrets_yaml(self):
        """Test detection of secrets.yaml/yml."""
        diff = """
diff --git a/secrets.yaml b/secrets.yaml
diff --git a/config/secrets.yml b/config/secrets.yml
"""
        findings = check_sensitive_files(diff)

        assert len(findings) >= 2

    def test_detect_private_key_files(self):
        """Test detection of private key files."""
        diff = """
diff --git a/server.pem b/server.pem
diff --git a/private.key b/private.key
diff --git a/cert.p12 b/cert.p12
"""
        findings = check_sensitive_files(diff)

        assert len(findings) >= 3

    def test_detect_ssh_keys(self):
        """Test detection of SSH keys."""
        diff = """
diff --git a/.ssh/id_rsa b/.ssh/id_rsa
diff --git a/.ssh/id_dsa b/.ssh/id_dsa
"""
        findings = check_sensitive_files(diff)

        assert len(findings) >= 2

    def test_detect_password_files(self):
        """Test detection of password files."""
        diff = """
diff --git a/.password b/.password
diff --git a/.pgpass b/.pgpass
diff --git a/.netrc b/.netrc
"""
        findings = check_sensitive_files(diff)

        assert len(findings) >= 3

    def test_clean_diff_no_sensitive_files(self):
        """Test with clean diff (no sensitive files)."""
        diff = """
diff --git a/src/main.py b/src/main.py
diff --git a/tests/test_main.py b/tests/test_main.py
diff --git a/README.md b/README.md
"""
        findings = check_sensitive_files(diff)

        assert len(findings) == 0

    def test_case_insensitive_detection(self):
        """Test case-insensitive file detection."""
        diff = """
diff --git a/Credentials.JSON b/Credentials.JSON
diff --git a/.ENV b/.ENV
"""
        findings = check_sensitive_files(diff)

        # Should detect regardless of case
        assert len(findings) >= 2


class TestPatternCoverage:
    """Test that all pattern types are properly defined."""

    def test_sensitive_patterns_defined(self):
        """Test that SENSITIVE_PATTERNS is properly defined."""
        assert isinstance(SENSITIVE_PATTERNS, dict)
        assert len(SENSITIVE_PATTERNS) >= 14

        # Check for key pattern types
        expected_patterns = [
            "AWS Access Key",
            "AWS Secret Key",
            "GitHub Token",
            "API Key",
            "JWT Token",
            "Private Key",
            "Database Connection String",
            "Slack Token",
            "Stripe Key",
            "Google API Key",
            "Bearer Token",
            "Password",
        ]

        for pattern_name in expected_patterns:
            assert pattern_name in SENSITIVE_PATTERNS

    def test_sensitive_files_patterns(self):
        """Test that sensitive file patterns work correctly."""
        # Test that the function detects various sensitive file patterns
        test_cases = [
            (".env", True),
            ("credentials.json", True),
            ("secrets.yaml", True),
            ("server.pem", True),
            ("private.key", True),
            ("id_rsa", True),
            ("id_dsa", True),
            ("normal_file.py", False),
            ("README.md", False),
        ]

        for filename, should_detect in test_cases:
            diff = f"diff --git a/{filename} b/{filename}\n+content"
            findings = check_sensitive_files(diff)

            if should_detect:
                assert len(findings) > 0, f"Should detect {filename}"
                assert filename in findings[0]
            else:
                assert len(findings) == 0, f"Should not detect {filename}"
