"""Command-line interface for smart-commit."""

import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table

from smart_commit import __version__
from smart_commit.ai_providers import get_ai_provider
from smart_commit.cache import CommitMessageCache
from smart_commit.config import ConfigManager, GlobalConfig, RepositoryConfig
from smart_commit.repository import RepositoryAnalyzer, RepositoryContext
from smart_commit.templates import CommitMessageFormatter, PromptBuilder
from smart_commit.utils import (
    validate_diff_size,
    count_diff_stats,
    detect_sensitive_data,
    check_sensitive_files,
    detect_breaking_changes,
)


def version_callback(value: bool):
    """Show version and exit."""
    if value:
        console = Console()
        console.print(f"[bold cyan]smart-commit[/bold cyan] version [bold green]{__version__}[/bold green]")
        raise typer.Exit()


app = typer.Typer(
    name="smart-commit",
    help="AI-powered git commit message generator with repository context awareness",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

console = Console()

# Global state
config_manager = ConfigManager()

# Logger setup
logger = logging.getLogger("smart_commit")


def setup_logging(debug: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if debug else logging.INFO

    # Clear existing handlers
    logger.handlers.clear()

    # Add rich handler
    handler = RichHandler(
        console=console,
        show_time=debug,
        show_path=debug,
        markup=True,
        rich_tracebacks=True,
    )
    handler.setFormatter(logging.Formatter("%(message)s"))

    logger.addHandler(handler)
    logger.setLevel(level)

    # Set level for other loggers
    logging.getLogger("smart_commit.ai_providers").setLevel(level)
    logging.getLogger("smart_commit.repository").setLevel(level)
    logging.getLogger("smart_commit.templates").setLevel(level)


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    )
):
    """Smart-commit CLI application."""
    pass


@app.command()
def generate(
    message: Optional[str] = typer.Option(None, "--message", "-m", help="Additional context for the commit"),
    auto_commit: bool = typer.Option(False, "--auto", "-a", help="Automatically commit with generated message"),
    show_diff: bool = typer.Option(True, "--show-diff/--no-diff", help="Show the staged diff"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", "-i", help="Interactive mode for editing"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Generate message without committing"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
    template: Optional[str] = typer.Option(None, "--template", "-t", help="Use a predefined template (hotfix, feature, docs, refactor, release)"),
    privacy: bool = typer.Option(False, "--privacy", help="Privacy mode: exclude context files and file paths from AI prompt"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass cache and generate fresh commit message"),
) -> None:
    """Generate an AI-powered commit message for staged changes."""

    # Setup logging
    setup_logging(debug=debug or verbose)

    # Handle template mode
    if template:
        _generate_from_template(template, auto_commit, interactive)
        return

    # Privacy mode notification
    if privacy:
        console.print("[yellow]🔒 Privacy mode enabled: Context files and paths will be excluded from AI prompt[/yellow]")

    # Initialize cache
    cache = CommitMessageCache()
    logger.debug(f"Cache initialized at {cache.cache_dir}")

    try:
        logger.debug("Starting commit message generation")
        logger.debug(f"Options: auto_commit={auto_commit}, interactive={interactive}, dry_run={dry_run}")
        # Load configuration
        logger.debug("Loading configuration")
        config = config_manager.load_config()
        logger.debug(f"Configuration loaded: model={config.ai.model}")

        # Get AI credentials from environment variables first, then from config
        api_key = os.getenv("AI_API_KEY") or config.ai.api_key
        model = os.getenv("AI_MODEL") or config.ai.model

        logger.debug(f"Using model: {model}")
        logger.debug(f"API key configured: {'Yes' if api_key else 'No'}")

        if not api_key:
            console.print("[red]Error: AI_API_KEY environment variable or api_key in config not set.[/red]")
            console.print("Please run `smart-commit setup` or set the environment variable.")
            raise typer.Exit(1)

        if not model:
            console.print("[red]Error: AI_MODEL environment variable or model in config not set.[/red]")
            raise typer.Exit(1)

        # Check for staged changes
        logger.debug("Checking for staged changes")
        staged_changes = _get_staged_changes()
        if not staged_changes:
            console.print("[yellow]No staged changes found. Stage some changes first with 'git add'.[/yellow]")
            raise typer.Exit(1)

        logger.debug(f"Found {len(staged_changes)} characters in staged changes")

        # Validate diff size
        validation_result = validate_diff_size(staged_changes)
        if validation_result["warnings"]:
            console.print("\n[yellow]⚠️  Warnings:[/yellow]")
            for warning in validation_result["warnings"]:
                console.print(f"  • {warning}")

            # Show stats
            stats = count_diff_stats(staged_changes)
            console.print(f"\n[dim]Stats: {stats['files_changed']} files, "
                         f"+{stats['additions']} -{stats['deletions']} lines[/dim]")

            if not validation_result["is_valid"]:
                if not Confirm.ask("\nDiff is quite large. Continue anyway?", default=True):
                    console.print("[yellow]Cancelled.[/yellow]")
                    raise typer.Exit(1)

        # Check for sensitive data
        sensitive_data = detect_sensitive_data(staged_changes)
        sensitive_files = check_sensitive_files(staged_changes)

        if sensitive_data or sensitive_files:
            console.print("\n[bold red]🔒 Security Warning: Potential sensitive data detected![/bold red]")

            if sensitive_files:
                console.print("\n[red]Sensitive files detected:[/red]")
                for filename in sensitive_files:
                    console.print(f"  • {filename}")

            if sensitive_data:
                console.print("\n[red]Potential secrets detected:[/red]")
                # Group by pattern type and show limited results
                by_pattern = {}
                for pattern_name, masked_text, line_num in sensitive_data[:10]:  # Limit to 10
                    if pattern_name not in by_pattern:
                        by_pattern[pattern_name] = []
                    by_pattern[pattern_name].append((masked_text, line_num))

                for pattern_name, findings in by_pattern.items():
                    console.print(f"  • {pattern_name}: {len(findings)} occurrence(s)")
                    for masked_text, line_num in findings[:3]:  # Show first 3
                        console.print(f"    - Line {line_num}: {masked_text}")

            console.print("\n[yellow]⚠️  It's highly recommended to remove sensitive data before committing![/yellow]")
            console.print("[dim]Consider using environment variables or secret management tools.[/dim]")

            if not Confirm.ask("\n[bold]Are you SURE you want to continue?[/bold]", default=False):
                console.print("[yellow]Commit cancelled. Please remove sensitive data and try again.[/yellow]")
                raise typer.Exit(1)

        # Check for breaking changes
        breaking_changes = detect_breaking_changes(staged_changes)
        if breaking_changes and verbose:
            console.print("\n[bold yellow]⚡ Potential Breaking Changes Detected![/bold yellow]")
            console.print("[yellow]Consider adding 'BREAKING CHANGE:' to your commit message footer.[/yellow]\n")

            for reason, detail in breaking_changes[:5]:  # Show top 5
                console.print(f"  • [bold]{reason}[/bold]")
                console.print(f"    [dim]{detail}[/dim]")

            console.print("\n[dim]These changes might require a major version bump (semantic versioning).[/dim]")

        # Initialize repository analyzer with progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("[cyan]Analyzing repository context...", total=None)
            logger.debug("Analyzing repository context")
            repo_analyzer = RepositoryAnalyzer()
            repo_context = repo_analyzer.get_context()
            logger.debug(f"Repository: {repo_context.name}, Tech stack: {repo_context.tech_stack}")
            progress.update(task, completed=True)

        # Get repository-specific config
        repo_config = config.repositories.get(repo_context.name)
        if repo_config:
            logger.debug(f"Found repository-specific config for {repo_context.name}")
        
        if verbose:
            _display_context_info(repo_context, repo_config)
        
        if show_diff:
            _display_diff(staged_changes)
        
        # Filter diff if ignore patterns are configured
        if repo_config and repo_config.ignore_patterns:
            staged_changes = repo_analyzer.filter_diff(staged_changes, repo_config.ignore_patterns)
        
        # Build prompt with progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("[cyan]Building prompt from context...", total=None)
            prompt_builder = PromptBuilder(config.template)
            prompt = prompt_builder.build_prompt(
                diff_content=staged_changes,
                repo_context=repo_context,
                repo_config=repo_config if not privacy else None,
                additional_context=message,
                privacy_mode=privacy
            )
            progress.update(task, completed=True)

        if verbose:
            console.print("\n[blue]Generated Prompt:[/blue]")
            console.print(Panel(prompt, title="Prompt", border_style="blue"))

        # Check cache first (unless --no-cache or privacy mode)
        commit_message = None
        if not no_cache and not privacy:
            logger.debug("Checking cache for existing commit message")
            commit_message = cache.get(staged_changes, model)
            if commit_message:
                console.print("[cyan]💾 Using cached commit message[/cyan]")
                logger.debug("Cache hit!")

        # Generate commit message with progress if not cached
        if commit_message is None:
            try:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                    transient=True,
                ) as progress:
                    task = progress.add_task("[green]Generating commit message with AI...", total=None)

                    ai_provider = get_ai_provider(
                        api_key=api_key,
                        model=model,
                        max_tokens=config.ai.max_tokens,
                        temperature=config.ai.temperature
                    )
                    raw_message = ai_provider.generate_commit_message(prompt)

                    # Format message
                    formatter = CommitMessageFormatter(config.template)
                    commit_message = formatter.format_message(raw_message)

                    progress.update(task, completed=True)

                # Store in cache (unless privacy mode)
                if not privacy:
                    logger.debug("Storing commit message in cache")
                    cache.set(staged_changes, model, commit_message)

            except Exception as e:
                console.print(f"[red]Error generating commit message: {e}[/red]")
                raise typer.Exit(1)
        
        # Display generated message
        console.print("\n[green]Generated Commit Message:[/green]")
        console.print(Panel(commit_message, title="Commit Message", border_style="green"))
        
        if dry_run:
            console.print("\n[yellow]Dry run mode - no commit performed.[/yellow]")
            return
        
        # Interactive editing
        if interactive and not auto_commit:
            if Confirm.ask("\nWould you like to edit the message?"):
                commit_message = _edit_message_interactive(commit_message)

        # Commit or confirm
        should_commit = False

        if auto_commit:
            should_commit = True
        elif interactive:
            should_commit = Confirm.ask("\nProceed with this commit message?")
        else:
            # Non-interactive mode commits by default
            should_commit = True

        if should_commit:
            _perform_commit(commit_message)
            console.print("\n[green]✓ Committed successfully![/green]")
        else:
            console.print("\n[yellow]Commit cancelled.[/yellow]")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user.[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        import traceback
        def get_trace(e: Exception, n: int = 5):
            """Get the last n lines of the traceback for an exception"""
            return "".join(traceback.format_exception(e)[-n:])
        console.print(f"\n[red]Error: {get_trace(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def config(
    init: bool = typer.Option(False, "--init", help="Initialize configuration"),
    edit: bool = typer.Option(False, "--edit", help="Edit configuration"),
    show: bool = typer.Option(False, "--show", help="Show current configuration"),
    local: bool = typer.Option(False, "--local", help="Use local repository configuration"),
    reset: bool = typer.Option(False, "--reset", help="Reset configuration to defaults"),
) -> None:
    """Manage smart-commit configuration."""
    
    if init:
        _init_config(local)
    elif edit:
        _edit_config(local)
    elif show:
        _show_config(local)
    elif reset:
        _reset_config(local)
    else:
        console.print("Use --init, --edit, --show, or --reset")


@app.command()
def context(
    repo_path: Optional[Path] = typer.Argument(None, help="Repository path (default: current directory)"),
) -> None:
    """Show repository context information."""
    
    try:
        analyzer = RepositoryAnalyzer(repo_path)
        repo_context = analyzer.get_context()
        
        _display_context_info(repo_context, None, detailed=True)
        
    except Exception as e:
        console.print(f"[red]Error analyzing repository: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def install_hook(
    hook_type: str = typer.Option(
        "prepare-commit-msg",
        "--type",
        "-t",
        help="Hook type: 'prepare-commit-msg' or 'post-commit'"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing hook"),
) -> None:
    """Install git hook for automatic commit message generation."""
    try:
        # Check if we're in a git repository
        repo_analyzer = RepositoryAnalyzer()
        repo_root = repo_analyzer.repo_root

        hooks_dir = repo_root / ".git" / "hooks"
        if not hooks_dir.exists():
            console.print("[red]Error: .git/hooks directory not found.[/red]")
            raise typer.Exit(1)

        hook_path = hooks_dir / hook_type

        # Check if hook already exists
        if hook_path.exists() and not force:
            console.print(f"[yellow]Hook already exists at {hook_path}[/yellow]")
            if not Confirm.ask("Overwrite existing hook?"):
                console.print("[yellow]Installation cancelled.[/yellow]")
                return

        # Create hook script
        if hook_type == "prepare-commit-msg":
            hook_content = """#!/bin/bash
# smart-commit prepare-commit-msg hook
# Auto-generates commit message if none provided

COMMIT_MSG_FILE=$1
COMMIT_SOURCE=$2

# Only run if commit source is not provided (i.e., user didn't use -m)
if [ -z "$COMMIT_SOURCE" ]; then
    # Generate commit message
    smart-commit generate --no-interactive --dry-run > "$COMMIT_MSG_FILE" 2>/dev/null || true
fi
"""
        elif hook_type == "post-commit":
            hook_content = """#!/bin/bash
# smart-commit post-commit hook
# Displays commit message analysis

echo ""
echo "✓ Commit created successfully!"
"""
        else:
            console.print(f"[red]Error: Unsupported hook type '{hook_type}'[/red]")
            console.print("Supported types: prepare-commit-msg, post-commit")
            raise typer.Exit(1)

        # Write hook file
        hook_path.write_text(hook_content)
        hook_path.chmod(0o755)  # Make executable

        console.print(f"[green]✓ Git hook installed successfully![/green]")
        console.print(f"Hook: {hook_path}")
        console.print(f"Type: {hook_type}")

        if hook_type == "prepare-commit-msg":
            console.print("\n[dim]The hook will automatically generate commit messages")
            console.print("when you run 'git commit' without the -m flag.[/dim]")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error installing hook: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def uninstall_hook(
    hook_type: str = typer.Option(
        "prepare-commit-msg",
        "--type",
        "-t",
        help="Hook type to uninstall"
    ),
) -> None:
    """Uninstall git hook."""
    try:
        repo_analyzer = RepositoryAnalyzer()
        repo_root = repo_analyzer.repo_root

        hook_path = repo_root / ".git" / "hooks" / hook_type

        if not hook_path.exists():
            console.print(f"[yellow]Hook not found at {hook_path}[/yellow]")
            return

        # Check if it's a smart-commit hook
        content = hook_path.read_text()
        if "smart-commit" not in content:
            console.print("[yellow]This doesn't appear to be a smart-commit hook.[/yellow]")
            if not Confirm.ask("Remove it anyway?"):
                console.print("[yellow]Uninstall cancelled.[/yellow]")
                return

        hook_path.unlink()
        console.print(f"[green]✓ Hook removed successfully![/green]")

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error uninstalling hook: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def cache_cmd(
    clear: bool = typer.Option(False, "--clear", help="Clear all cached commit messages"),
    stats: bool = typer.Option(False, "--stats", help="Show cache statistics"),
    clear_expired: bool = typer.Option(False, "--clear-expired", help="Clear expired cache entries only"),
) -> None:
    """Manage commit message cache."""

    cache = CommitMessageCache()

    if clear:
        count = cache.clear()
        console.print(f"[green]✓ Cleared {count} cached commit message(s)[/green]")
        console.print(f"[dim]Cache directory: {cache.cache_dir}[/dim]")
        return

    if clear_expired:
        count = cache.clear_expired()
        console.print(f"[green]✓ Cleared {count} expired cache entry(s)[/green]")
        return

    if stats or not (clear or clear_expired):
        # Show stats by default
        stats_data = cache.get_stats()

        table = Table(title="Cache Statistics", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Total Entries", str(stats_data['total_entries']))
        table.add_row("Cache Size (MB)", str(stats_data['cache_size_mb']))
        table.add_row("Cache Directory", stats_data['cache_dir'])

        console.print(table)

        if stats_data['total_entries'] > 0:
            console.print("\n[dim]Tip: Use --clear to clear all cached messages[/dim]")
            console.print("[dim]Tip: Use --clear-expired to clear only expired entries[/dim]")


@app.command()
def setup(
    model: str = typer.Option("openai/gpt-4o", help="Model to use (e.g., 'openai/gpt-4o', 'claude-3-haiku-20240307')"),
    api_key: Optional[str] = typer.Option(None, help="API key (will prompt if not provided)"),
) -> None:
    """Quick setup for smart-commit."""
    
    console.print("[bold blue]Smart-Commit Setup[/bold blue]")
    
    console.print("This will save your configuration globally. For best practice, use environment variables:")
    console.print("  [cyan]export AI_MODEL='model_name'[/cyan]")
    console.print("  [cyan]export AI_API_KEY='your_api_key'[/cyan]")
    if not api_key:
        api_key = Prompt.ask("Enter your API key", password=True)
    
    # Save to global config as a fallback
    config = config_manager.load_config()
    config.ai.model = model
    config.ai.api_key = api_key
    
    # Save global config
    config_manager.save_config(config, local=False)
    
    console.print("[green]✓ Configuration saved successfully![/green]")
    console.print(f"Model: {model}")
    console.print(f"Config saved to: {config_manager.global_config_path}")


# Helper functions

def _get_staged_changes() -> str:
    """Get staged changes from git."""
    try:
        result = subprocess.run(
            ["git", "diff", "--staged"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return ""


def _display_diff(diff_content: str) -> None:
    """Display the git diff."""
    console.print("\n[blue]Staged Changes:[/blue]")
    syntax = Syntax(diff_content, "diff", theme="monokai", line_numbers=False)
    console.print(Panel(syntax, title="Git Diff", border_style="blue"))


def _display_context_info(
    repo_context: RepositoryContext, 
    repo_config: Optional[RepositoryConfig],
    detailed: bool = False
) -> None:
    """Display repository context information."""
    
    table = Table(title="Repository Context", show_header=True, header_style="bold magenta")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Name", repo_context.name)
    table.add_row("Path", str(repo_context.path))
    
    if repo_context.description:
        table.add_row("Description", repo_context.description)
    
    if repo_context.tech_stack:
        table.add_row("Tech Stack", ", ".join(repo_context.tech_stack))
    
    if repo_context.active_branches:
        table.add_row("Branches", ", ".join(repo_context.active_branches))
    
    if detailed and repo_context.recent_commits:
        table.add_row("Recent Commits", "\n".join(repo_context.recent_commits[:5]))
    
    console.print(table)
    
    if repo_config:
        console.print("\n[yellow]Repository-specific configuration found.[/yellow]")


def _edit_message_interactive(message: str) -> str:
    """Allow interactive editing of commit message."""
    import subprocess
    import tempfile

    # Create temporary file with message
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(message)
        temp_file = f.name
    
    try:
        # Open editor
        editor = os.environ.get('EDITOR', 'nano')
        subprocess.run([editor, temp_file], check=True)
        
        # Read edited message
        with open(temp_file, 'r') as f:
            edited_message = f.read().strip()
        
        return edited_message
    finally:
        # Clean up
        os.unlink(temp_file)


def _perform_commit(message: str) -> None:
    """Perform the git commit."""
    try:
        subprocess.run(
            ["git", "commit", "-m", message],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        raise Exception(f"Git commit failed: {e.stderr}")


def _init_config(local: bool) -> None:
    """Initialize configuration."""
    config_path = config_manager.get_config_path(local)
    
    if config_path.exists():
        if not Confirm.ask(f"Configuration already exists at {config_path}. Overwrite?"):
            return
    
    # Create default config
    config = GlobalConfig()
    
    # Interactive setup
    console.print("[bold blue]Configuration Setup[/bold blue]")
    console.print("[dim]Supported models: OpenAI (openai/gpt-4o), Anthropic (claude-3-5-sonnet-20241022), Google (gemini/gemini-1.5-pro), etc.[/dim]")
    console.print("[dim]See https://docs.litellm.ai/docs/providers for full list[/dim]\n")

    model = Prompt.ask(
        "AI Model",
        default="openai/gpt-4o"
    )
    config.ai.model = model

    api_key = Prompt.ask("API Key", password=True)
    config.ai.api_key = api_key
    
    # Template configuration
    config.template.max_subject_length = int(Prompt.ask(
        "Maximum subject line length", 
        default="50"
    ))
    
    config.template.conventional_commits = Confirm.ask(
        "Use conventional commits format?", 
        default=True
    )
    
    include_sample_repo_config = Confirm.ask(
        "Include sample repository configuration?", 
        default=False
    )
    if include_sample_repo_config:
        config.repositories = {
            "{your_repo}": RepositoryConfig(
                name="{your_repo}",
                description="{your_repository_description}",
                absolute_path="{/absolute/path/to/your/repo}",
                tech_stack=["{tech1}", "{tech2}", "{tech3}"],
                ignore_patterns=["*.pyc", "__pycache__"],
                context_files=["README.md"],
            )
        }
    
    # Save configuration
    config_manager.save_config(config, local)
    
    scope = "local" if local else "global"
    console.print(f"[green]✓ {scope.title()} configuration saved to {config_path}[/green]")


def _edit_config(local: bool) -> None:
    """Edit configuration file."""
    config_path = config_manager.get_config_path(local)
    
    if not config_path.exists():
        console.print(f"[yellow]No configuration found at {config_path}. Run --init first.[/yellow]")
        return
    
    editor = os.environ.get('EDITOR', 'nano')
    try:
        subprocess.run([editor, str(config_path)], check=True)
        console.print("[green]✓ Configuration updated.[/green]")
    except subprocess.CalledProcessError:
        console.print("[red]Error opening editor.[/red]")


def _show_config(local: bool) -> None:
    """Show current configuration."""
    try:
        config = config_manager.load_config()
        
        table = Table(title="Current Configuration", show_header=True)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="white")

        # AI Configuration
        table.add_row("AI Model", config.ai.model)
        table.add_row("API Key", ("***" + config.ai.api_key[-4:]) if config.ai.api_key else "Not set")
        
        # Template Configuration
        table.add_row("Max Subject Length", str(config.template.max_subject_length))
        table.add_row("Conventional Commits", str(config.template.conventional_commits))
        table.add_row("Include Body", str(config.template.include_body))
        table.add_row("Include Reasoning", str(config.template.include_reasoning))
        
        console.print(table)
        
        # Show config file locations
        console.print(f"\n[dim]Global config: {config_manager.global_config_path}[/dim]")
        console.print(f"[dim]Local config: {config_manager.local_config_path}[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")


def _reset_config(local: bool) -> None:
    """Reset configuration to defaults."""
    config_path = config_manager.get_config_path(local)

    if config_path.exists():
        if Confirm.ask(f"Reset configuration at {config_path}?"):
            config_path.unlink()
            console.print("[green]✓ Configuration reset.[/green]")
    else:
        console.print("[yellow]No configuration file found.[/yellow]")


def _generate_from_template(template_name: str, auto_commit: bool, interactive: bool) -> None:
    """Generate commit message from a predefined template."""

    # Predefined templates
    templates = {
        "hotfix": """hotfix: {brief_description}

Critical bug fix deployed to production.

Issue: {issue_description}
Impact: {impact}
Fix: {fix_description}

Tested: {testing_notes}""",

        "feature": """feat: {feature_name}

{feature_description}

Changes:
- {change_1}
- {change_2}
- {change_3}

Benefits:
- {benefit_1}
- {benefit_2}""",

        "docs": """docs: {documentation_area}

{description}

Updated:
- {item_1}
- {item_2}""",

        "refactor": """refactor: {component_name}

{description}

Changes:
- {change_1}
- {change_2}

This refactor improves {improvement_area} without changing external behavior.""",

        "release": """chore(release): {version}

Release version {version}

Changes in this release:
- {change_1}
- {change_2}
- {change_3}

Breaking Changes:
{breaking_changes_description}""",

        "deps": """build(deps): {dependency_action}

{description}

Updated packages:
- {package_1}: {old_version} → {new_version}
- {package_2}: {old_version} → {new_version}""",
    }

    if template_name not in templates:
        console.print(f"[red]Error: Unknown template '{template_name}'[/red]")
        console.print(f"[yellow]Available templates: {', '.join(templates.keys())}[/yellow]")
        raise typer.Exit(1)

    # Get template
    template = templates[template_name]

    # Display template
    console.print(f"\n[bold cyan]Template: {template_name}[/bold cyan]")
    console.print(Panel(template, title="Commit Message Template", border_style="cyan"))

    console.print("\n[yellow]Fill in the placeholders (text in curly braces).[/yellow]")
    console.print("[dim]Tip: You can edit the final message in your editor.[/dim]\n")

    # Extract placeholders
    import re
    placeholders = re.findall(r'\{([^}]+)\}', template)

    # Ask user to fill in placeholders
    values = {}
    for placeholder in placeholders:
        if placeholder not in values:  # Avoid asking twice for repeated placeholders
            value = Prompt.ask(f"  {placeholder}")
            values[placeholder] = value

    # Fill template
    commit_message = template
    for placeholder, value in values.items():
        commit_message = commit_message.replace(f"{{{placeholder}}}", value)

    # Display generated message
    console.print("\n[green]Generated Commit Message:[/green]")
    console.print(Panel(commit_message, title="Commit Message", border_style="green"))

    # Interactive editing
    if interactive and not auto_commit:
        if Confirm.ask("\nWould you like to edit the message?"):
            commit_message = _edit_message_interactive(commit_message)

    # Commit logic
    should_commit = False
    if auto_commit:
        should_commit = True
    elif interactive:
        should_commit = Confirm.ask("\nProceed with this commit message?")
    else:
        should_commit = True

    if should_commit:
        _perform_commit(commit_message)
        console.print("\n[green]✓ Committed successfully![/green]")
    else:
        console.print("\n[yellow]Commit cancelled.[/yellow]")


# Command aliases for convenience
@app.command(name="g", hidden=True)
def g_alias(
    message: Optional[str] = typer.Option(None, "--message", "-m"),
    auto_commit: bool = typer.Option(False, "--auto", "-a"),
    show_diff: bool = typer.Option(True, "--show-diff/--no-diff"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", "-i"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    debug: bool = typer.Option(False, "--debug"),
    template: Optional[str] = typer.Option(None, "--template", "-t"),
    privacy: bool = typer.Option(False, "--privacy"),
    no_cache: bool = typer.Option(False, "--no-cache"),
):
    """Alias for 'generate' command."""
    generate(message, auto_commit, show_diff, interactive, dry_run, verbose, debug, template, privacy, no_cache)


@app.command(name="cfg", hidden=True)
def cfg_alias(
    init: bool = typer.Option(False, "--init"),
    edit: bool = typer.Option(False, "--edit"),
    show: bool = typer.Option(False, "--show"),
    local: bool = typer.Option(False, "--local"),
    reset: bool = typer.Option(False, "--reset"),
):
    """Alias for 'config' command."""
    config(init, edit, show, local, reset)


@app.command(name="ctx", hidden=True)
def ctx_alias(repo_path: Optional[Path] = typer.Argument(None)):
    """Alias for 'context' command."""
    context(repo_path)


if __name__ == "__main__":
    app()
