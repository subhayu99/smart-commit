# Smart Commit 🤖

[![PyPI version](https://badge.fury.io/py/smart-commit-ai.svg)](https://badge.fury.io/py/smart-commit-ai)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An AI-powered git commit message generator with repository context awareness, built with Python and Typer.

## Features

- 🧠 **AI-Powered**: Uses OpenAI GPT and Anthropic Claude models to generate meaningful commit messages
- 📁 **Repository Context**: Analyzes your repo structure, tech stack, and recent commits
- ⚙️ **Configurable**: Global and local configuration with conventional commit support
- 🖥️ **CLI Interface**: Rich, interactive command-line interface with Typer
- 🔧 **MCP Server**: Model Context Protocol server for integration with AI assistants
- 🎯 **Smart Filtering**: Ignore patterns and custom rules per repository
- 📝 **Interactive Editing**: Edit generated messages before committing

## Installation

### Requirements

- Python 3.10 or higher
- Git repository (for generating commit messages)
- API key for your chosen AI provider (OpenAI or Anthropic)

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

# Install with Anthropic support
pip install smart-commit-ai[anthropic]

# Install with all optional dependencies
pip install smart-commit-ai[all]
```

## Quick Setup

```bash
# Quick setup with OpenAI
smart-commit setup --provider openai --model gpt-4o --api-key your-api-key

# Quick setup with Anthropic Claude
smart-commit setup --provider anthropic --model claude-3-5-sonnet-20241022 --api-key your-api-key

# Or use the short alias
sc setup --provider openai --model gpt-4o --api-key your-api-key
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
provider = "openai"  # or "anthropic"
model = "gpt-4o"     # or "claude-3-5-sonnet-20241022"
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

## MCP Server Integration

Smart-commit includes MCP (Model Context Protocol) server support for integration with AI assistants like Claude Desktop.

### Running as MCP Server

```bash
# Run the MCP server directly
python -m smart_commit.mcp

# Or use it in your MCP client configuration
```

### MCP Client Configuration

Add to your MCP client configuration (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "smart-commit": {
      "command": "python",
      "args": ["-m", "smart_commit.mcp"]
    }
  }
}
```

### Available MCP Tools

- `analyze_repository`: Analyze repository structure and context
- `generate_commit_message`: Generate AI-powered commit messages
- `get_staged_changes`: Get current staged changes
- `configure_smart_commit`: Update configuration settings
- `get_repository_context`: Get detailed repository information
- `quick_setup`: Quick configuration setup
- `show_configuration`: Display current configuration

### MCP Resources

- `repository://current`: Current repository information
- `config://smart-commit`: Smart-commit configuration

### MCP Prompts

- `commit_message_template`: Template for commit message generation
- `repository_analysis_prompt`: Template for repository analysis

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

Example output:
```
Generated commit message:

feat: add user authentication system

- Implement JWT-based authentication
- Add login and logout endpoints
- Create user session management
- Add password hashing with bcrypt

This change introduces a complete authentication system to secure
user access and manage sessions effectively.
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

Example context output:
```
Repository Analysis: my-awesome-app

Technology Stack: Python, JavaScript, Docker, PostgreSQL
Active Branches: main, feature/auth, hotfix/security-patch
Recent Commits:
- fix: resolve SQL injection vulnerability
- feat: add user dashboard
- docs: update API documentation
```

## Environment Variables

- `SMART_COMMIT_API_KEY`: API key for your AI provider
- `SMART_COMMIT_PROVIDER`: Default AI provider (openai or anthropic)
- `EDITOR`: Preferred editor for interactive message editing (default: nano)

## Troubleshooting

### Common Issues

**"No staged changes found"**
- Make sure you've staged your changes with `git add`
- Check if you're in a git repository

**"API key not configured"**
- Run `smart-commit setup` to configure your API key
- Or set the `SMART_COMMIT_API_KEY` environment variable

**"AI provider error"**
- Verify your API key is valid and has sufficient credits
- Check your internet connection
- Try switching to a different model

**"Configuration not found"**
- Run `smart-commit config --init` to create initial configuration
- Check if the config file exists at `~/.config/smart-commit/config.toml`

### Debug Mode

```bash
# Run with verbose output for debugging
smart-commit generate --verbose

# Show configuration details
smart-commit config --show
```

## Development

### Setting up Development Environment

```bash
# Clone the repository
git clone https://github.com/subhayu99/smart-commit.git
cd smart-commit

# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install development dependencies
uv pip install -e ".[dev]"

# Install with all optional dependencies
uv pip install -e ".[all]"
```

### Running Tests

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=smart_commit
```

### Code Quality

```bash
# Format code
black smart_commit/
isort smart_commit/

# Type checking
mypy smart_commit/

# Run pre-commit hooks
pre-commit run --all-files
```

### Building and Publishing

```bash
# Build the package
uv build

# Publish to PyPI (maintainers only)
uv publish
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Run the test suite (`pytest`)
6. Commit your changes with a descriptive message
7. Push to your branch (`git push origin feature/amazing-feature`)
8. Create a Pull Request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Roadmap

- [ ] Plugin system for custom commit message formats
- [ ] Integration with popular Git GUIs
- [ ] Commit message templates and presets
- [ ] Team/organization shared configurations
- [ ] Webhook support for CI/CD integration
- [ ] VS Code extension
- [ ] Git hooks integration
- [ ] Support for more AI models (Gemini, local models)
- [ ] Commit message quality scoring
- [ ] Integration with issue tracking systems

## Support

- 📖 [Documentation](https://github.com/subhayu99/smart-commit#readme)
- 🐛 [Bug Reports](https://github.com/subhayu99/smart-commit/issues)
- 💡 [Feature Requests](https://github.com/subhayu99/smart-commit/issues)
- 💬 [Discussions](https://github.com/subhayu99/smart-commit/discussions)

---

Made with ❤️ by [Subhayu Kumar Bala](https://github.com/subhayu99)