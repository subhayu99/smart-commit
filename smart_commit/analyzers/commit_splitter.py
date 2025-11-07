"""Analyze and suggest commit splitting strategies."""

from typing import List, Dict, Tuple
from dataclasses import dataclass
from smart_commit.utils import detect_scope_from_diff, count_diff_stats


@dataclass
class CommitGroup:
    """Represents a suggested group of files for a single commit."""
    name: str
    files: List[str]
    reason: str
    scope: str
    priority: int = 0  # Lower number = higher priority


def analyze_commit_split(diff_content: str) -> List[CommitGroup]:
    """
    Analyze a large diff and suggest how to split it into multiple commits.

    Args:
        diff_content: The full git diff content

    Returns:
        List of suggested commit groups
    """
    # Parse files from diff
    files_data = _parse_diff_files(diff_content)

    if len(files_data) <= 5:
        # Small enough, no split needed
        return []

    # Analyze and group files
    groups = []

    # Group 1: Test files
    test_files = [f for f in files_data if _is_test_file(f['path'])]
    if test_files:
        groups.append(CommitGroup(
            name="Tests",
            files=[f['path'] for f in test_files],
            reason="Separate test changes for easier review and CI validation",
            scope="test",
            priority=3
        ))

    # Group 2: Documentation
    doc_files = [f for f in files_data if _is_doc_file(f['path'])]
    if doc_files:
        groups.append(CommitGroup(
            name="Documentation",
            files=[f['path'] for f in doc_files],
            reason="Documentation updates independent of code changes",
            scope="docs",
            priority=4
        ))

    # Group 3: Configuration
    config_files = [f for f in files_data if _is_config_file(f['path'])]
    if config_files:
        groups.append(CommitGroup(
            name="Configuration",
            files=[f['path'] for f in config_files],
            reason="Configuration changes that affect build/deploy",
            scope="config",
            priority=2
        ))

    # Group 4: Group remaining files by directory/scope
    remaining_files = [
        f for f in files_data
        if f not in test_files and f not in doc_files and f not in config_files
    ]

    if remaining_files:
        scope_groups = _group_by_scope(remaining_files)
        for scope, files in scope_groups.items():
            if len(files) >= 2:
                groups.append(CommitGroup(
                    name=f"{scope.title()} Changes",
                    files=[f['path'] for f in files],
                    reason=f"Related {scope} functionality changes",
                    scope=scope,
                    priority=1
                ))

    # Sort by priority
    groups.sort(key=lambda g: g.priority)

    return groups


def _parse_diff_files(diff_content: str) -> List[Dict]:
    """Parse file information from diff."""
    files = []
    current_file = None
    additions = 0
    deletions = 0

    for line in diff_content.split('\n'):
        if line.startswith('diff --git'):
            # Save previous file
            if current_file:
                current_file['additions'] = additions
                current_file['deletions'] = deletions
                files.append(current_file)

            # Start new file
            parts = line.split(' ')
            if len(parts) >= 4:
                b_index = line.find(' b/')
                if b_index != -1:
                    filepath = line[b_index + 3:]
                    current_file = {'path': filepath}
                    additions = 0
                    deletions = 0
        elif line.startswith('+') and not line.startswith('+++'):
            additions += 1
        elif line.startswith('-') and not line.startswith('---'):
            deletions += 1

    # Don't forget the last file
    if current_file:
        current_file['additions'] = additions
        current_file['deletions'] = deletions
        files.append(current_file)

    return files


def _is_test_file(filepath: str) -> bool:
    """Check if file is a test file."""
    return (
        'test' in filepath.lower() or
        filepath.startswith('tests/') or
        filepath.endswith('_test.py') or
        filepath.endswith('.test.js') or
        filepath.endswith('.spec.js') or
        filepath.endswith('.test.ts') or
        filepath.endswith('.spec.ts')
    )


def _is_doc_file(filepath: str) -> bool:
    """Check if file is documentation."""
    return (
        filepath.endswith('.md') or
        filepath.endswith('.rst') or
        filepath.endswith('.txt') or
        'doc' in filepath.lower() or
        filepath.startswith('docs/')
    )


def _is_config_file(filepath: str) -> bool:
    """Check if file is configuration."""
    config_patterns = [
        '.toml', '.yaml', '.yml', '.json', '.ini', '.cfg',
        'Dockerfile', 'docker-compose', '.env', 'requirements',
        'package.json', 'package-lock.json', 'Cargo.toml',
        'go.mod', 'go.sum', 'pom.xml', 'build.gradle'
    ]
    filepath_lower = filepath.lower()
    return any(pattern in filepath_lower for pattern in config_patterns)


def _group_by_scope(files: List[Dict]) -> Dict[str, List[Dict]]:
    """Group files by their scope/directory."""
    scope_map = {}

    for file_data in files:
        filepath = file_data['path']

        # Determine scope based on path
        parts = filepath.split('/')

        if len(parts) > 1:
            # Use first directory as scope
            scope = parts[0]

            # Refine scope for common patterns
            if parts[0] in ['src', 'lib']:
                scope = parts[1] if len(parts) > 1 else parts[0]
        else:
            # Root level file
            scope = 'root'

        if scope not in scope_map:
            scope_map[scope] = []
        scope_map[scope].append(file_data)

    return scope_map


def suggest_git_commands(groups: List[CommitGroup]) -> List[Tuple[str, str]]:
    """
    Generate git commands to stage each group.

    Returns:
        List of (description, command) tuples
    """
    commands = []

    # First, unstage everything
    commands.append((
        "Reset staging area",
        "git reset"
    ))

    # Then stage each group
    for i, group in enumerate(groups, 1):
        files_str = " ".join(f'"{f}"' for f in group.files)
        commands.append((
            f"Commit {i}: {group.name}",
            f"git add {files_str} && git commit"
        ))

    return commands
