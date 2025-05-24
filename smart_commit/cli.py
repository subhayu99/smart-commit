"""Command-line interface for smart-commit."""

import os
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table

from smart_commit.ai_providers import get_ai_provider
from smart_commit.config import ConfigManager, GlobalConfig, RepositoryConfig
from smart_commit.repository import RepositoryAnalyzer, RepositoryContext
from smart_commit.templates import CommitMessageFormatter, PromptBuilder

app = typer.Typer(
    name="smart-commit",
    help="AI-powered git commit message generator with repository context awareness",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

console = Console()

# Global state
config_manager = ConfigManager()


@app.command()
def generate(
    message: Optional[str] = typer.Option(None, "--message", "-m", help="Additional context for the commit"),
    auto_commit: bool = typer.Option(False, "--auto", "-a", help="Automatically commit with generated message"),
    show_diff: bool = typer.Option(True, "--show-diff/--no-diff", help="Show the staged diff"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", "-i", help="Interactive mode for editing"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Generate message without committing"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Generate an AI-powered commit message for staged changes."""
    
    try:
        # Load configuration
        config = config_manager.load_config()
        
        # Check for staged changes
        staged_changes = _get_staged_changes()
        if not staged_changes:
            console.print("[yellow]No staged changes found. Stage some changes first with 'git add'.[/yellow]")
            raise typer.Exit(1)
        
        # Initialize repository analyzer
        repo_analyzer = RepositoryAnalyzer()
        repo_context = repo_analyzer.get_context()
        
        # Get repository-specific config
        repo_config = config.repositories.get(repo_context.name)
        
        if verbose:
            _display_context_info(repo_context, repo_config)
        
        if show_diff:
            _display_diff(staged_changes)
        
        # Filter diff if ignore patterns are configured
        if repo_config and repo_config.ignore_patterns:
            staged_changes = repo_analyzer.filter_diff(staged_changes, repo_config.ignore_patterns)
        
        # Build prompt
        prompt_builder = PromptBuilder(config.template)
        prompt = prompt_builder.build_prompt(
            diff_content=staged_changes,
            repo_context=repo_context,
            repo_config=repo_config,
            additional_context=message
        )
        
        if verbose:
            console.print("\n[blue]Generated Prompt:[/blue]")
            console.print(Panel(prompt, title="Prompt", border_style="blue"))
        
        # Generate commit message
        console.print("\n[green]Generating commit message...[/green]")
        
        try:
            ai_provider = get_ai_provider(
                provider_name=config.ai.provider,
                api_key=config.ai.api_key or "",
                model=config.ai.model,
                max_tokens=config.ai.max_tokens,
                temperature=config.ai.temperature
            )
            
            raw_message = ai_provider.generate_commit_message(prompt)
            
            # Format message
            formatter = CommitMessageFormatter(config.template)
            commit_message = formatter.format_message(raw_message)
            
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
        if auto_commit or (not interactive and not Confirm.ask("\nProceed with this commit message?")):
            if auto_commit:
                _perform_commit(commit_message)
                console.print("\n[green]✓ Committed successfully![/green]")
            else:
                console.print("\n[yellow]Commit cancelled.[/yellow]")
        else:
            _perform_commit(commit_message)
            console.print("\n[green]✓ Committed successfully![/green]")
            
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
def setup(
    provider: str = typer.Option("openai", help="AI provider (openai, anthropic)"),
    model: str = typer.Option("gpt-4o", help="Model to use"),
    api_key: Optional[str] = typer.Option(None, help="API key (will prompt if not provided)"),
) -> None:
    """Quick setup for smart-commit."""
    
    console.print("[bold blue]Smart-Commit Setup[/bold blue]")
    
    if not api_key:
        api_key = Prompt.ask(f"Enter your {provider.upper()} API key", password=True)
    
    # Create basic config
    config = config_manager.load_config()
    config.ai.provider = provider
    config.ai.model = model
    config.ai.api_key = api_key
    
    # Save global config
    config_manager.save_config(config, local=False)
    
    console.print("[green]✓ Configuration saved successfully![/green]")
    console.print(f"Provider: {provider}")
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
    
    provider = Prompt.ask(
        "AI Provider", 
        choices=["openai", "anthropic"], 
        default="openai"
    )
    config.ai.provider = provider
    
    if provider == "openai":
        model = Prompt.ask(
            "OpenAI Model",
            choices=["gpt-4o", "gpt-4", "gpt-3.5-turbo"],
            default="gpt-4o"
        )
        config.ai.model = model
    
    api_key = Prompt.ask(f"{provider.upper()} API Key", password=True)
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
        table.add_row("AI Provider", config.ai.provider)
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


if __name__ == "__main__":
    app()
