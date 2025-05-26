# Smart Commit 🤖

[![PyPI version](https://badge.fury.io/py/smart-commit-ai.svg)](https://badge.fury.io/py/smart-commit-ai)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An AI-powered git commit message generator with repository context awareness, built with Python and Typer.

## Why Smart Commit?

As developers, we know the importance of good commit messages. They serve as a historical record, help with debugging, facilitate code reviews, and make collaboration seamless. But let's be honest - writing detailed, meaningful commit messages consistently is **hard**.

### The Problem

**Time Pressure & Context Switching**: When you're juggling multiple projects simultaneously, switching between different codebases, technologies, and contexts, it becomes increasingly difficult to craft thoughtful commit messages. What used to be a natural part of your workflow becomes a bottleneck.

**Cognitive Load**: After spending hours deep in code, the last thing you want to do is context-switch to writing prose. Your brain is in "code mode," not "documentation mode."

**Consistency Across Projects**: Each project has its own conventions, tech stack, and commit patterns. Maintaining consistency becomes nearly impossible when you're working on 3-4 different repositories in a single day.

**The Vicious Cycle**: Poor commit messages lead to poor project history. When you need to understand what changed and why (during debugging, code reviews, or onboarding new team members), cryptic messages like "fix stuff" or "update" provide zero value.

### The Solution

Smart Commit understands your repository context - the tech stack, recent commit patterns, file changes, and project structure. It generates meaningful, detailed commit messages that:

- **Capture the "Why"**: Not just what changed, but the reasoning behind the change
- **Maintain Consistency**: Follows your project's established patterns and conventions
- **Save Mental Energy**: Let AI handle the prose while you focus on the code
- **Preserve History**: Create a rich, searchable project timeline that actually helps future you

**Example of the difference:**

Instead of:
```
fix auth bug
update dependencies  
refactor components
```

You get:
```
fix(auth): resolve JWT token expiration handling

- Fix race condition in token refresh mechanism
- Add proper error handling for expired tokens  
- Update token validation middleware
- Add unit tests for edge cases

This resolves the issue where users were unexpectedly logged out
during active sessions due to improper token lifecycle management.
```

Smart Commit turns your commit history into a valuable project resource that tells the story of your codebase evolution.

## Features

- 🧠 **AI-Powered**: Uses OpenAI GPT and Anthropic Claude models to generate meaningful commit messages
- 📁 **Repository Context**: Analyzes your repo structure, tech stack, and recent commits
- ⚙️ **Configurable**: Global and local configuration with conventional commit support
- 🖥️ **CLI Interface**: Rich, interactive command-line interface with Typer
- 🔧 **MCP Server**: Model Context Protocol server for integration with AI assistants
- 🎯 **Smart Filtering**: Ignore patterns and custom rules per repository
- 📝 **Interactive Editing**: Edit generated messages before committing
- 🏗️ **Context Files**: Include project documentation for enhanced understanding
- 🎨 **Custom Templates**: Configurable commit message formats and examples

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
# Initialize configuration (with optional sample repo config)
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
# Shows detailed information about the current repository
smart-commit context

# Shows detailed information about a specific repository
smart-commit context /path/to/repo
```

## Configuration

Smart-commit supports both global and local configurations:

- **Global**: `~/.config/smart-commit/config.toml`
- **Local**: `.smart-commit.toml` in your repository

### Enhanced Configuration Options

The configuration now includes enhanced features for better commit message generation:

```toml
[ai]
provider = "openai"
model = "gpt-4o"
api_key = "your-api-key"
max_tokens = 500
temperature = 0.1

[template]
max_subject_length = 50
max_recent_commits = 5  # Number of recent commits to analyze
include_body = true
include_reasoning = true
conventional_commits = true

# Custom example formats for AI guidance
example_formats = [
    """feat: add user authentication system

- Implement JWT-based authentication
- Add login and logout endpoints
- Include password hashing with bcrypt
- Add authentication middleware for protected routes

This enables secure user sessions and protects sensitive endpoints from unauthorized access."""
]

# Enhanced commit type prefixes with descriptions
[template.custom_prefixes]
feat = "for new features"
fix = "for bug fixes"
docs = "for documentation changes"
style = "for formatting changes"
refactor = "for code refactoring"
test = "for test changes"
chore = "for maintenance tasks"
perf = "for performance improvements"
build = "for build system changes"
ci = "for CI/CD changes"
revert = "for reverting changes"

# Repository-specific configuration with enhanced context
[repositories.my-project]
name = "my-project"
description = "My awesome project"
absolute_path = "/absolute/path/to/project"  # Explicit path for accessing context files globally
tech_stack = ["python", "react", "docker"]
ignore_patterns = ["*.log", "node_modules/**"]
context_files = ["README.md", "CHANGELOG.md"]  # Files included in AI context

# Comprehensive commit conventions
[repositories.my-project.commit_conventions]
breaking = "Use BREAKING CHANGE: in footer for breaking changes that require major version bump"
scope = "Use scope in parentheses after type: feat(auth): add login system"
subject_case = "Use imperative mood in lowercase: 'add feature' not 'adds feature' or 'added feature'"
subject_length = "Keep subject line under 50 characters for better readability"
body_format = "Wrap body at 72 characters, use bullet points for multiple changes"
body_separation = "Separate subject from body with a blank line"
present_tense = "Use present tense: 'change' not 'changed' or 'changes'"
no_period = "Do not end the subject line with a period"
why_not_what = "Explain why the change was made, not just what was changed"
atomic_commits = "Make each commit a single logical change"
test_coverage = "Include test changes when adding new functionality"
docs_update = "Update documentation when changing public APIs or behavior"
```

## Repository Context Features

Smart-commit automatically detects and uses:

- 📊 **Technology Stack**: Languages, frameworks, and tools
- 🌿 **Branch Information**: Active branches and current branch
- 📝 **Recent Commits**: Configurable number of recent commits for pattern analysis
- 📁 **File Structure**: Repository organization
- 🔍 **Project Metadata**: README descriptions and project info
- 📚 **Context Files**: Project documentation included in AI context
- 🎯 **Absolute Paths**: Precise file location for multi-repo setups
- 🚫 **Ignore Patterns**: Custom patterns to exclude files from analysis
- 🗂️ **Commit Conventions**: Project-specific commit message guidelines

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

### Context Files for Enhanced Understanding

Include specific files for additional AI context:

```toml
[repositories.my-project]
absolute_path = "/home/user/projects/my-project"
context_files = [
    "README.md",
    "CHANGELOG.md", 
    "docs/contributing.md",
    "API_REFERENCE.md"
]
```

The AI will read these files and use their content to better understand your project structure and generate more relevant commit messages.

### Custom Commit Types with Descriptions

Define project-specific commit types with clear descriptions:

```toml
[template.custom_prefixes]
feat = "for new features"
fix = "for bug fixes"
hotfix = "for critical production fixes"
security = "for security-related changes"
deps = "for dependency updates"
config = "for configuration changes"
```

### Recent Commits Analysis

Configure how many recent commits to analyze for pattern consistency:

```toml
[template]
max_recent_commits = 10  # Analyze last 10 commits for patterns
```

This helps maintain consistency with your existing commit style and conventions.

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

### With Enhanced Context

```bash
# Generate with additional context
smart-commit generate -m "Resolves GitHub issue #123"

# Auto-commit
smart-commit generate --auto

# Verbose output
smart-commit generate --verbose
```

### Repository Setup with Context Files

```bash
# Initialize local config for your project
smart-commit config --init --local
# Will prompt: "Include sample repository configuration? [y/N]"

# This will create configuration including context files
# Edit .smart-commit.toml to specify your context files:

[repositories.my-project]
name = "my-project"
description = "My awesome project description"
absolute_path = "/full/path/to/project"
context_files = ["README.md", "docs/ARCHITECTURE.md"]
```

### Multi-Repository Workflow

For developers working on multiple repositories:

```toml
# Global config at ~/.config/smart-commit/config.toml

[repositories.frontend-app]
name = "frontend-app"
description = "React frontend application"
absolute_path = "/home/dev/projects/frontend-app"
tech_stack = ["react", "typescript", "tailwind"]
context_files = ["README.md", "package.json"]

[repositories.backend-api]
name = "backend-api" 
description = "Python FastAPI backend"
absolute_path = "/home/dev/projects/backend-api"
tech_stack = ["python", "fastapi", "postgresql"]
context_files = ["README.md", "requirements.txt", "docs/API.md"]

[repositories.mobile-app]
name = "mobile-app"
description = "React Native mobile application"
absolute_path = "/home/dev/projects/mobile-app"
tech_stack = ["react-native", "typescript", "expo"]
context_files = ["README.md", "app.json", "docs/SETUP.md"]
```

This allows Smart Commit to automatically understand the context of whichever repository you're working in and generate appropriate commit messages.

## Environment Variables

- `EDITOR`: Preferred editor for interactive message editing (default: nano)

## Troubleshooting

### Common Issues

**"No staged changes found"**
- Make sure you've staged your changes with `git add`
- Check if you're in a git repository

**"API key not configured"**
- Run `smart-commit setup` to configure your API key

**"AI provider error"**
- Verify your API key is valid and has sufficient credits
- Check your internet connection
- Try switching to a different model

**"Configuration not found"**
- Run `smart-commit config --init` to create initial configuration
- Check if the config file exists at `~/.config/smart-commit/config.toml`

**"Context file not found"**
- Verify the `absolute_path` in your repository configuration is correct
- Check that context files exist at the specified locations
- Use relative paths from the repository root if `absolute_path` is not set

### Debug Mode

```bash
# Run with verbose output for debugging
smart-commit generate --verbose

# Show configuration details
smart-commit config --show

# Analyze repository context
smart-commit context
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