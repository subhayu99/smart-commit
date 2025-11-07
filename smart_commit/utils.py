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
    "Database Connection String": r"(?i)(postgres|postgresql|mysql|mongodb|redis)://[^\s]+",
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
            # Handle spaces in filenames by looking for 'b/' prefix
            # Format: diff --git a/path/to/file b/path/to/file
            b_index = line.find(' b/')
            if b_index != -1:
                filename = line[b_index + 3:]  # Skip ' b/'
                changed_files.append(filename)

    if not changed_files:
        return []

    # Detect scopes based on file paths, tracking frequency
    scope_counts = {}

    def add_scope(scope_name):
        """Helper to increment scope count."""
        scope_counts[scope_name] = scope_counts.get(scope_name, 0) + 1

    # Common directory-based scopes
    for filepath in changed_files:
        parts = filepath.split('/')

        # Check for common directory patterns
        if len(parts) > 1:
            # Check for component/module directories
            if parts[0] in ['src', 'lib', 'app']:
                if len(parts) > 1:
                    add_scope(parts[1])
            else:
                add_scope(parts[0])

        # Check for specific file patterns
        if 'test' in filepath.lower():
            add_scope('tests')
        if 'doc' in filepath.lower() or filepath.endswith('.md'):
            add_scope('docs')
        if 'config' in filepath.lower() or filepath.endswith(('.yml', '.yaml', '.toml', '.json', '.ini')):
            add_scope('config')
        if filepath.endswith(('.css', '.scss', '.sass', '.less')):
            add_scope('styles')
        if 'api' in filepath.lower():
            add_scope('api')
        if 'cli' in filepath.lower():
            add_scope('cli')
        if 'ui' in filepath.lower() or 'component' in filepath.lower():
            add_scope('ui')
        if 'db' in filepath.lower() or 'database' in filepath.lower() or 'migration' in filepath.lower():
            add_scope('database')
        if 'auth' in filepath.lower():
            add_scope('auth')
        if 'util' in filepath.lower() or 'helper' in filepath.lower():
            add_scope('utils')

    # Remove generic/unhelpful scopes
    scope_counts.pop('src', None)
    scope_counts.pop('lib', None)
    scope_counts.pop('app', None)
    scope_counts.pop('', None)

    # Sort by frequency (descending) then alphabetically
    sorted_scopes = sorted(scope_counts.items(), key=lambda x: (-x[1], x[0]))
    return [scope for scope, count in sorted_scopes[:5]]  # Return top 5 suggestions


def detect_breaking_changes(diff_content: str) -> List[Tuple[str, str]]:
    """
    Detect potential breaking changes in the diff.

    Args:
        diff_content: The git diff content

    Returns:
        List of tuples (reason, detail) for potential breaking changes
    """
    breaking_changes = []
    lines = diff_content.split('\n')

    # Patterns that suggest breaking changes
    breaking_patterns = {
        # Function/method signature changes
        r'^\-\s*def\s+(\w+)\s*\(([^)]*)\)': "Function signature changed",
        r'^\-\s*public\s+\w+\s+(\w+)\s*\(': "Public method signature changed",
        r'^\-\s*export\s+(function|class|interface|type)\s+(\w+)': "Exported API changed",

        # API endpoint changes
        r'^\-\s*@(app|router)\.(get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]\)': "API endpoint removed/changed",
        r'^\-\s*(GET|POST|PUT|DELETE|PATCH)\s+/': "HTTP route changed",

        # Database schema changes
        r'^\-\s*(CREATE|ALTER|DROP)\s+(TABLE|COLUMN)': "Database schema change",
        r'^\-\s*Column\(': "Database column definition changed",

        # Configuration changes
        r'^\-\s*(required|mandatory)': "Required field removed",
        r'^\-\s*class\s+\w+.*\(.*Config': "Configuration class changed",

        # Type/interface changes
        r'^\-\s*interface\s+(\w+)': "Interface definition changed",
        r'^\-\s*type\s+(\w+)\s*=': "Type definition changed",
        r'^\-\s*class\s+(\w+)': "Class definition changed",

        # Dependency changes
        r'^\-\s*"([^"]+)":\s*"\^?(\d+)\.': "Dependency version changed",

        # Public API removal
        r'^\-\s*(export|public)\s': "Public API element removed",
    }

    current_file = None

    for i, line in enumerate(lines):
        # Track current file
        if line.startswith('diff --git'):
            parts = line.split(' ')
            if len(parts) >= 4:
                current_file = parts[3][2:]

        # Only check removed lines (potential breaking changes)
        if line.startswith('-') and not line.startswith('---'):
            for pattern, reason in breaking_patterns.items():
                match = re.search(pattern, line)
                if match:
                    detail = f"{current_file}: {line[1:].strip()[:80]}"
                    breaking_changes.append((reason, detail))
                    break  # Only report first matching pattern per line

    return breaking_changes[:10]  # Limit to first 10 findings


def analyze_diff_impact(diff_content: str) -> Dict[str, Any]:
    """
    Analyze the overall impact of changes in the diff.

    Args:
        diff_content: The git diff content

    Returns:
        Dict with impact analysis:
        - breaking_changes: List of potential breaking changes
        - risk_level: 'low', 'medium', or 'high'
        - affected_areas: List of affected code areas
        - change_type: 'refactor', 'feature', 'fix', 'docs', etc.
    """
    lines = diff_content.split('\n')
    breaking_changes = detect_breaking_changes(diff_content)

    # Count additions and deletions
    additions = len([l for l in lines if l.startswith('+') and not l.startswith('+++')])
    deletions = len([l for l in lines if l.startswith('-') and not l.startswith('---')])

    # Get file types
    changed_files = []
    for line in lines:
        if line.startswith('diff --git'):
            parts = line.split(' ')
            if len(parts) >= 4:
                filename = parts[3][2:]
                changed_files.append(filename)

    # Determine change type
    change_type = 'refactor'
    if any('.md' in f or 'doc' in f.lower() for f in changed_files):
        change_type = 'docs'
    elif any('test' in f.lower() for f in changed_files):
        change_type = 'test'
    elif additions > deletions * 2:
        change_type = 'feature'
    elif deletions > additions * 2:
        change_type = 'removal'
    elif breaking_changes:
        change_type = 'breaking'

    # Determine risk level
    risk_level = 'low'
    if breaking_changes:
        risk_level = 'high'
    elif deletions > 100 or additions > 500:
        risk_level = 'high'
    elif deletions > 50 or additions > 200:
        risk_level = 'medium'

    # Affected areas
    affected_areas = detect_scope_from_diff(diff_content)

    return {
        "breaking_changes": breaking_changes,
        "risk_level": risk_level,
        "affected_areas": affected_areas,
        "change_type": change_type,
        "additions": additions,
        "deletions": deletions,
        "files_changed": len(changed_files),
    }
