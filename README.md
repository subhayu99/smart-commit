# Smart Commit 🤖

An AI-powered git commit message generator with repository context awareness, built with Python and Typer.

## Features

- 🧠 **AI-Powered**: Uses OpenAI GPT models to generate meaningful commit messages
- 📁 **Repository Context**: Analyzes your repo structure, tech stack, and recent commits
- ⚙️ **Configurable**: Global and local configuration with conventional commit support
- 🖥️ **CLI Interface**: Rich, interactive command-line interface with Typer
- 🔧 **MCP Agent**: Model Context Protocol support for integration with AI assistants
- 🎯 **Smart Filtering**: Ignore patterns and custom rules per repository
- 📝 **Interactive Editing**: Edit generated messages before committing

## Installation

### Using uv (Recommended)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install and run as a tool (system-wide install)
uv tool install smart-commit-ai

# Use the tool in any repository
sc generate
```

### Using pip

```bash
pip install smart-commit-ai
```

## Quick Setup

```bash
# Quick setup with OpenAI
smart-commit setup --provider openai --model gpt-4o

# Or use the short alias
sc setup --provider openai --model gpt-4o
```

## Usage

### Generate Commit Messages

```bash
# Generate commit message for staged changes
smart-commit generate

# Add additional context
smart-commit generate --message "Fixes issue with user authentication"

# Auto-commit without confirmation
smart-commit generate --auto

# Dry run (generate message only)
smart-commit generate --dry-run

# Non-interactive mode
smart-commit generate --no-interactive
```

### Configuration Management

```bash
# Initialize configuration
smart-commit config --init

# Edit configuration
smart-commit config --edit

# Show current configuration
smart-commit config --show

# Local repository configuration
smart-commit config --init --local
```

### Repository Analysis

```bash
# Analyze current repository
smart-commit context

# Analyze specific repository
smart-commit context /path/to/repo
```

## Configuration

Smart-commit supports both global and local configurations:

- **Global**: `~/.config/smart-commit/config.toml`
- **Local**: `.smart-commit.toml` in your repository

### Example Configuration

```toml
[ai]
provider = "openai"
model = "gpt-4o"
api_key = "your-api-key"
max_tokens = 500
temperature = 0.1

[template]
max_subject_length = 50
include_body = true
include_reasoning = true
conventional_commits = true

[template.custom_prefixes]
hotfix = "hotfix:"
wip = "wip:"

[repositories.my-project]
name = "my-project"
description = "My awesome project"
tech_stack = ["python", "react", "docker"]
ignore_patterns = ["*.log", "node_modules/**"]
context_files = ["README.md", "CHANGELOG.md"]

[repositories.my-project.commit_conventions]
breaking = "Use BREAKING CHANGE in footer for breaking changes"
scope = "Use scope in parentheses: feat(auth): add login"
```

## Repository Context Features

Smart-commit automatically detects:

- 📊 **Technology Stack**: Languages, frameworks, and tools
- 🌿 **Branch Information**: Active branches and current branch
- 📝 **Recent Commits**: Recent commit patterns for consistency
- 📁 **File Structure**: Repository organization
- 🔍 **Project Metadata**: README descriptions and project info

## MCP Agent Integration

Smart-commit includes MCP (Model Context Protocol) support for integration with AI assistants:

```python
from smart_commit.mcp import SmartCommitMCP

# Create MCP agent
agent = SmartCommitMCP()

# Get available tools
tools = agent.get_tools()

# Execute tools
response = agent.execute_tool("generate_commit_message", {
    "additional_context": "Fix critical security issue"
})
```

### Available MCP Tools

- `analyze_repository`: Analyze repository structure and context
- `generate_commit_message`: Generate AI-powered commit messages
- `get_staged_changes`: Get current staged changes
- `configure_smart_commit`: Update configuration settings

## Advanced Features

### Custom Ignore Patterns

Add patterns to ignore specific files or changes:

```toml
[repositories.my-project]
ignore_patterns = [
    "*.log",
    "node_modules/**",
    "dist/**",
    "*.generated.*"
]
```

### Context Files

Include specific files for additional context:

```toml
[repositories.my-project]
context_files = [
    "README.md",
    "CHANGELOG.md", 
    "docs/contributing.md"
]
```

### Custom Commit Types

Define project-specific commit types:

```toml
[template.custom_prefixes]
hotfix = "hotfix:"
security = "security:"
deps = "deps:"
```

## Examples

### Basic Usage

```bash
# Stage your changes
git add .

# Generate commit message
smart-commit generate
```

### With Context

```bash
# Generate with additional context
smart-commit generate -m "Resolves GitHub issue #123"

# Auto-commit
smart-commit generate --auto

# Verbose output
smart-commit generate --verbose
```

### Repository Setup

```bash
# Initialize local config for your project
smart-commit config --init --local

# Analyze your repository
smart-commit context
```

## Environment Variables

- `EDITOR`: Preferred editor for interactive message editing (default: nano)

## Development

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Format code
black smart_commit/
isort smart_commit/

# Type checking
mypy smart_commit/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Run the test suite
6. Create a pull request

## License

MIT License - see LICENSE file for details.

## Roadmap

- [ ] Support for more AI providers (Anthropic Claude, etc.)
- [ ] Plugin system for custom commit message formats
- [ ] Integration with popular Git GUIs
- [ ] Commit message templates and presets
- [ ] Team/organization shared configurations
- [ ] Webhook support for CI/CD integration
- [ ] VS Code extension
- [ ] Git hooks integration
