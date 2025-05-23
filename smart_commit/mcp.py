"""MCP (Model Context Protocol) agent implementation."""

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from smart_commit.ai_providers import get_ai_provider
from smart_commit.config import ConfigManager
from smart_commit.repository import RepositoryAnalyzer
from smart_commit.templates import PromptBuilder


@dataclass
class MCPTool:
    """MCP tool definition."""
    name: str
    description: str
    parameters: Dict[str, Any]


@dataclass
class MCPResponse:
    """MCP response structure."""
    content: str
    metadata: Optional[Dict[str, Any]] = None


class SmartCommitMCP:
    """MCP agent for smart-commit functionality."""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.tools = self._register_tools()
    
    def _register_tools(self) -> List[MCPTool]:
        """Register available MCP tools."""
        return [
            MCPTool(
                name="analyze_repository",
                description="Analyze repository structure and context",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Repository path (optional, defaults to current directory)"
                        }
                    }
                }
            ),
            MCPTool(
                name="generate_commit_message",
                description="Generate AI-powered commit message for staged changes",
                parameters={
                    "type": "object",
                    "properties": {
                        "additional_context": {
                            "type": "string",
                            "description": "Additional context for commit message generation"
                        },
                        "repository_path": {
                            "type": "string", 
                            "description": "Repository path (optional)"
                        }
                    }
                }
            ),
            MCPTool(
                name="get_staged_changes",
                description="Get current staged changes in git diff format",
                parameters={
                    "type": "object",
                    "properties": {
                        "repository_path": {
                            "type": "string",
                            "description": "Repository path (optional)"
                        }
                    }
                }
            ),
            MCPTool(
                name="configure_smart_commit",
                description="Configure smart-commit settings",
                parameters={
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": ["openai", "anthropic"],
                            "description": "AI provider"
                        },
                        "model": {
                            "type": "string", 
                            "description": "Model name"
                        },
                        "api_key": {
                            "type": "string",
                            "description": "API key for the provider"
                        }
                    },
                    "required": ["provider"]
                }
            )
        ]
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools in MCP format."""
        return [asdict(tool) for tool in self.tools]
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> MCPResponse:
        """Execute an MCP tool."""
        try:
            if tool_name == "analyze_repository":
                return self._analyze_repository(parameters)
            elif tool_name == "generate_commit_message":
                return self._generate_commit_message(parameters)
            elif tool_name == "get_staged_changes":
                return self._get_staged_changes(parameters)
            elif tool_name == "configure_smart_commit":
                return self._configure_smart_commit(parameters)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
        except Exception as e:
            return MCPResponse(
                content=f"Error executing {tool_name}: {str(e)}",
                metadata={"error": True}
            )
    
    def _analyze_repository(self, parameters: Dict[str, Any]) -> MCPResponse:
        """Analyze repository structure and context."""
        from pathlib import Path
        
        repo_path = parameters.get("path")
        if repo_path:
            repo_path = Path(repo_path)
        
        analyzer = RepositoryAnalyzer(repo_path)
        context = analyzer.get_context()
        
        # Format context for display
        content = f"""# Repository Analysis: {context.name}

**Path:** {context.path}
**Description:** {context.description or 'No description available'}

## Technology Stack
{', '.join(context.tech_stack) if context.tech_stack else 'Not detected'}

## Active Branches
{', '.join(context.active_branches) if context.active_branches else 'None found'}

## Recent Commits
"""
        
        for commit in context.recent_commits[:5]:
            content += f"- {commit}\n"
        
        if context.file_structure:
            content += "\n## File Structure\n"
            for directory, files in context.file_structure.items():
                content += f"- **{directory}/**: {len(files)} files\n"
        
        return MCPResponse(
            content=content,
            metadata={
                "repository_name": context.name,
                "tech_stack": context.tech_stack,
                "branch_count": len(context.active_branches)
            }
        )
    
    def _generate_commit_message(self, parameters: Dict[str, Any]) -> MCPResponse:
        """Generate commit message for staged changes."""
        import subprocess
        from pathlib import Path
        
        repo_path = parameters.get("repository_path")
        additional_context = parameters.get("additional_context", "")
        
        if repo_path:
            repo_path = Path(repo_path)
        
        # Get staged changes
        try:
            if repo_path:
                result = subprocess.run(
                    ["git", "diff", "--staged"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
            else:
                result = subprocess.run(
                    ["git", "diff", "--staged"],
                    capture_output=True,
                    text=True,
                    check=True
                )
            staged_changes = result.stdout
        except subprocess.CalledProcessError:
            return MCPResponse(
                content="Error: Could not get staged changes. Make sure you're in a git repository with staged changes.",
                metadata={"error": True}
            )
        
        if not staged_changes:
            return MCPResponse(
                content="No staged changes found. Stage some changes first with 'git add'.",
                metadata={"warning": True}
            )
        
        # Analyze repository
        analyzer = RepositoryAnalyzer(repo_path)
        repo_context = analyzer.get_context()
        
        # Load configuration
        config = self.config_manager.load_config()
        
        # Build prompt
        prompt_builder = PromptBuilder(config.template)
        prompt = prompt_builder.build_prompt(
            diff_content=staged_changes,
            repo_context=repo_context,
            additional_context=additional_context
        )
        
        # Generate commit message
        try:
            ai_provider = get_ai_provider(
                provider_name=config.ai.provider,
                api_key=config.ai.api_key,
                model=config.ai.model,
                max_tokens=config.ai.max_tokens,
                temperature=config.ai.temperature
            )
            
            commit_message = ai_provider.generate_commit_message(prompt)
            
            return MCPResponse(
                content=f"# Generated Commit Message\n\n```\n{commit_message}\n```",
                metadata={
                    "commit_message": commit_message,
                    "repository": repo_context.name,
                    "changes_detected": bool(staged_changes)
                }
            )
            
        except Exception as e:
            return MCPResponse(
                content=f"Error generating commit message: {str(e)}",
                metadata={"error": True}
            )
    
    def _get_staged_changes(self, parameters: Dict[str, Any]) -> MCPResponse:
        """Get staged changes in diff format."""
        import subprocess
        from pathlib import Path
        
        repo_path = parameters.get("repository_path")
        
        try:
            if repo_path:
                result = subprocess.run(
                    ["git", "diff", "--staged"],
                    cwd=Path(repo_path),
                    capture_output=True,
                    text=True,
                    check=True
                )
            else:
                result = subprocess.run(
                    ["git", "diff", "--staged"],
                    capture_output=True,
                    text=True,
                    check=True
                )
            
            staged_changes = result.stdout
            
            if not staged_changes:
                return MCPResponse(
                    content="No staged changes found.",
                    metadata={"has_changes": False}
                )
            
            return MCPResponse(
                content=f"# Staged Changes\n\n```diff\n{staged_changes}\n```",
                metadata={
                    "has_changes": True,
                    "diff_length": len(staged_changes)
                }
            )
            
        except subprocess.CalledProcessError as e:
            return MCPResponse(
                content=f"Error getting staged changes: {e}",
                metadata={"error": True}
            )
    
    def _configure_smart_commit(self, parameters: Dict[str, Any]) -> MCPResponse:
        """Configure smart-commit settings."""
        try:
            config = self.config_manager.load_config()
            
            # Update configuration
            if "provider" in parameters:
                config.ai.provider = parameters["provider"]
            
            if "model" in parameters:
                config.ai.model = parameters["model"]
            
            if "api_key" in parameters:
                config.ai.api_key = parameters["api_key"]
            
            # Save configuration
            self.config_manager.save_config(config)
            
            return MCPResponse(
                content="✓ Smart-commit configuration updated successfully!",
                metadata={
                    "provider": config.ai.provider,
                    "model": config.ai.model,
                    "config_path": str(self.config_manager.global_config_path)
                }
            )
            
        except Exception as e:
            return MCPResponse(
                content=f"Error updating configuration: {str(e)}",
                metadata={"error": True}
            )


# MCP Server Implementation
def create_mcp_server():
    """Create MCP server for smart-commit."""
    agent = SmartCommitMCP()
    
    def handle_request(request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP requests."""
        method = request.get("method")
        
        if method == "tools/list":
            return {
                "tools": agent.get_tools()
            }
        
        elif method == "tools/call":
            params = request.get("params", {})
            tool_name = params.get("name")
            tool_params = params.get("arguments", {})
            
            response = agent.execute_tool(tool_name, tool_params)
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": response.content
                    }
                ],
                "metadata": response.metadata or {}
            }
        
        else:
            return {
                "error": f"Unknown method: {method}"
            }
    
    return handle_request
