import re
from typing import Any, Dict, List, Tuple


def remove_backticks(text: str) -> str:
    """Remove code block backticks from text."""
    return re.sub(r"```\w*\n(.*)\n```", r"\1", text, flags=re.DOTALL)


def validate_diff_size(diff_content: str, max_lines: int = 500, max_chars: int = 50000) -> Dict[str, Any]:
    """
    Validate diff size and provide warnings.

    Args:
        diff_content: The git diff content
        max_lines: Maximum recommended lines (default: 500)
        max_chars: Maximum recommended characters (default: 50000)

    Returns:
        Dict with validation results:
        - is_valid: bool
        - warnings: List[str]
        - line_count: int
        - char_count: int
        - file_count: int
    """
    lines = diff_content.split('\n')
    line_count = len(lines)
    char_count = len(diff_content)

    # Count changed files
    file_count = len([line for line in lines if line.startswith('diff --git')])

    # Generate warnings
    warnings = []
    is_valid = True

    if line_count > max_lines:
        is_valid = False
        warnings.append(
            f"Diff is very large ({line_count} lines). "
            f"Consider splitting into smaller commits for better commit messages."
        )

    if char_count > max_chars:
        is_valid = False
        warnings.append(
            f"Diff size is {char_count} characters, which may exceed token limits. "
            f"Consider committing files separately."
        )

    if file_count > 20:
        warnings.append(
            f"You're changing {file_count} files. "
            f"Consider grouping related changes into separate commits."
        )

    return {
        "is_valid": is_valid,
        "warnings": warnings,
        "line_count": line_count,
        "char_count": char_count,
        "file_count": file_count,
    }


def count_diff_stats(diff_content: str) -> Dict[str, int]:
    """
    Count statistics from diff content.

    Returns:
        Dict with:
        - additions: number of added lines
        - deletions: number of deleted lines
        - files_changed: number of files changed
    """
    lines = diff_content.split('\n')

    additions = len([line for line in lines if line.startswith('+')])
    deletions = len([line for line in lines if line.startswith('-')])
    files_changed = len([line for line in lines if line.startswith('diff --git')])

    return {
        "additions": additions,
        "deletions": deletions,
        "files_changed": files_changed,
    }


# Patterns for detecting sensitive data
SENSITIVE_PATTERNS = {
    "AWS Access Key": r"(?i)AKIA[0-9A-Z]{16}",
    "AWS Secret Key": r"(?i)aws.{0,20}?[\'\"][0-9a-zA-Z\/+]{40}[\'\"]",
    "Generic API Key": r"(?i)api[_\-]?key[\'\"\s:=]+[a-zA-Z0-9\-_]{20,}",
    "Generic Secret": r"(?i)secret[\'\"\s:=]+[a-zA-Z0-9\-_]{20,}",
    "Generic Token": r"(?i)token[\'\"\s:=]+[a-zA-Z0-9\-_]{20,}",
    "Generic Password": r"(?i)password[\'\"\s:=]+[a-zA-Z0-9\-_!@#$%^&*]{8,}",
    "GitHub Token": r"(?i)gh[pousr]_[a-zA-Z0-9]{36,}",
    "Generic Bearer Token": r"(?i)bearer\s+[a-zA-Z0-9\-_\.=]+",
    "Private Key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "Google API Key": r"AIza[0-9A-Za-z\-_]{35}",
    "Slack Token": r"xox[baprs]-[0-9]{10,12}-[0-9]{10,12}-[a-zA-Z0-9]{24,}",
    "Stripe Key": r"(?i)(?:sk|pk)_(live|test)_[0-9a-zA-Z]{24,}",
    "JWT Token": r"eyJ[a-zA-Z0-9\-_]+\.eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+",
    "Database Connection String": r"(?i)(postgres|mysql|mongodb|redis)://[^\s]+",
}


def detect_sensitive_data(diff_content: str) -> List[Tuple[str, str, int]]:
    """
    Detect potentially sensitive data in diff content.

    Args:
        diff_content: The git diff content

    Returns:
        List of tuples (pattern_name, matched_text, line_number)
    """
    findings = []
    lines = diff_content.split('\n')

    for line_num, line in enumerate(lines, 1):
        # Only check added lines (starting with '+')
        if not line.startswith('+'):
            continue

        # Skip diff metadata lines
        if line.startswith('+++'):
            continue

        for pattern_name, pattern in SENSITIVE_PATTERNS.items():
            matches = re.finditer(pattern, line)
            for match in matches:
                # Mask the sensitive data for display
                matched_text = match.group(0)
                if len(matched_text) > 20:
                    masked = matched_text[:10] + "..." + matched_text[-5:]
                else:
                    masked = matched_text[:5] + "..."

                findings.append((pattern_name, masked, line_num))

    return findings


def check_sensitive_files(diff_content: str) -> List[str]:
    """
    Check if any sensitive files are being committed.

    Args:
        diff_content: The git diff content

    Returns:
        List of potentially sensitive filenames
    """
    sensitive_file_patterns = [
        r"\.env$",
        r"\.env\.",
        r"credentials\.json$",
        r"secrets\.ya?ml$",
        r"\.pem$",
        r"\.key$",
        r"\.p12$",
        r"\.pfx$",
        r"id_rsa",
        r"id_dsa",
        r"\.password$",
        r"\.pgpass$",
        r"\.netrc$",
    ]

    lines = diff_content.split('\n')
    sensitive_files = []

    for line in lines:
        if line.startswith('diff --git'):
            # Extract filename from "diff --git a/path b/path"
            parts = line.split(' ')
            if len(parts) >= 4:
                filename = parts[3][2:]  # Remove 'b/' prefix

                for pattern in sensitive_file_patterns:
                    if re.search(pattern, filename, re.IGNORECASE):
                        sensitive_files.append(filename)
                        break

    return sensitive_files


def detect_scope_from_diff(diff_content: str) -> List[str]:
    """
    Detect potential scopes from changed files in the diff.

    Args:
        diff_content: The git diff content

    Returns:
        List of suggested scopes based on file paths
    """
    lines = diff_content.split('\n')
    changed_files = []

    for line in lines:
        if line.startswith('diff --git'):
            parts = line.split(' ')
            if len(parts) >= 4:
                filename = parts[3][2:]  # Remove 'b/' prefix
                changed_files.append(filename)

    if not changed_files:
        return []

    # Detect scopes based on file paths
    scopes = set()

    # Common directory-based scopes
    for filepath in changed_files:
        parts = filepath.split('/')

        # Check for common directory patterns
        if len(parts) > 1:
            # Check for component/module directories
            if parts[0] in ['src', 'lib', 'app']:
                if len(parts) > 1:
                    scopes.add(parts[1])
            else:
                scopes.add(parts[0])

        # Check for specific file patterns
        if 'test' in filepath.lower():
            scopes.add('tests')
        if 'doc' in filepath.lower() or filepath.endswith('.md'):
            scopes.add('docs')
        if 'config' in filepath.lower() or filepath.endswith(('.yml', '.yaml', '.toml', '.json', '.ini')):
            scopes.add('config')
        if filepath.endswith(('.css', '.scss', '.sass', '.less')):
            scopes.add('styles')
        if 'api' in filepath.lower():
            scopes.add('api')
        if 'cli' in filepath.lower():
            scopes.add('cli')
        if 'ui' in filepath.lower() or 'component' in filepath.lower():
            scopes.add('ui')
        if 'db' in filepath.lower() or 'database' in filepath.lower() or 'migration' in filepath.lower():
            scopes.add('database')
        if 'auth' in filepath.lower():
            scopes.add('auth')
        if 'util' in filepath.lower() or 'helper' in filepath.lower():
            scopes.add('utils')

    # Remove generic/unhelpful scopes
    scopes.discard('src')
    scopes.discard('lib')
    scopes.discard('app')
    scopes.discard('')

    return sorted(list(scopes))[:5]  # Return top 5 suggestions
