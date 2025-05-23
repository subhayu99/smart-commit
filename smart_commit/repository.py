"""Repository context and analysis."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

import git
import pathspec


@dataclass
class RepositoryContext:
    """Repository context information."""
    name: str
    path: Path
    description: Optional[str]
    tech_stack: List[str]
    recent_commits: List[str]
    active_branches: List[str]
    file_structure: Dict[str, List[str]]
    

class RepositoryAnalyzer:
    """Analyzes repository structure and context."""
    
    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path or Path.cwd()
        try:
            self.repo = git.Repo(self.repo_path, search_parent_directories=True)
            self.repo_root = Path(self.repo.working_dir)
        except git.InvalidGitRepositoryError:
            raise ValueError(f"Not a git repository: {self.repo_path}")
    
    def get_context(self) -> RepositoryContext:
        """Get comprehensive repository context."""
        return RepositoryContext(
            name=self._get_repo_name(),
            path=self.repo_root,
            description=self._get_repo_description(),
            tech_stack=self._detect_tech_stack(),
            recent_commits=self._get_recent_commits(),
            active_branches=self._get_active_branches(),
            file_structure=self._analyze_file_structure()
        )
    
    def _get_repo_name(self) -> str:
        """Get repository name."""
        try:
            origin_url = self.repo.remotes.origin.url
            if origin_url.endswith('.git'):
                origin_url = origin_url[:-4]
            return origin_url.split('/')[-1]
        except Exception:
            return self.repo_root.name
    
    def _get_repo_description(self) -> Optional[str]:
        """Get repository description from README or other sources."""
        readme_files = ['README.md', 'README.rst', 'README.txt', 'README']
        
        for readme in readme_files:
            readme_path = self.repo_root / readme
            if readme_path.exists():
                try:
                    content = readme_path.read_text(encoding='utf-8')
                    # Extract first paragraph as description
                    lines = content.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            return line[:200] + ('...' if len(line) > 200 else '')
                except Exception:
                    pass
        return None
    
    def _detect_tech_stack(self) -> List[str]:
        """Detect technologies used in the repository."""
        tech_indicators = {
            'python': ['requirements.txt', 'pyproject.toml', 'setup.py', 'Pipfile', '*.py'],
            'javascript': ['package.json', 'yarn.lock', 'npm-shrinkwrap.json', '*.js'],
            'typescript': ['tsconfig.json', '*.ts', '*.tsx'],
            'react': ['package.json'],  # Check package.json content separately
            'vue': ['*.vue'],
            'rust': ['Cargo.toml', '*.rs'],
            'go': ['go.mod', 'go.sum', '*.go'],
            'java': ['pom.xml', 'build.gradle', '*.java'],
            'docker': ['Dockerfile', 'docker-compose.yml'],
            # 'kubernetes': ['*.yaml', '*.yml'],  # Check content for k8s resources
            'terraform': ['*.tf'],
            # 'ansible': ['*.yml', '*.yaml'],  # Check for ansible-specific content
        }
        
        detected = set()
        
        for tech, indicators in tech_indicators.items():
            for indicator in indicators:
                if indicator.startswith('*.'):
                    # Check for file extensions
                    ext = indicator[1:]
                    if list(self.repo_root.rglob(f'*{ext}')):
                        detected.add(tech)
                        break
                else:
                    # Check for specific files
                    if (self.repo_root / indicator).exists():
                        detected.add(tech)
                        break
        
        # Special checks for content-based detection
        self._check_package_json(detected)
        
        return sorted(list(detected))
    
    def _check_package_json(self, detected: Set[str]) -> None:
        """Check package.json for specific frameworks."""
        package_json = self.repo_root / 'package.json'
        if package_json.exists():
            try:
                import json
                with open(package_json) as f:
                    data = json.load(f)
                    
                deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
                
                if any(dep.startswith('react') for dep in deps):
                    detected.add('react')
                if any(dep.startswith('vue') for dep in deps):
                    detected.add('vue')
                if any(dep.startswith('@angular') for dep in deps):
                    detected.add('angular')
                if 'next' in deps:
                    detected.add('nextjs')
            except Exception:
                pass
    
    def _get_recent_commits(self, limit: int = 10) -> List[str]:
        """Get recent commit messages."""
        try:
            commits = list(self.repo.iter_commits(max_count=limit))
            return [
                (
                    commit.message if isinstance(commit.message, str)
                    else commit.message.decode("utf-8") if isinstance(commit.message, bytes)
                    else ""
                ).strip().split("\n")[0]
                for commit in commits
            ]
        except Exception:
            return []
    
    def _get_active_branches(self) -> List[str]:
        """Get list of active branches."""
        try:
            branches = [branch.name for branch in self.repo.branches]
            return sorted(branches)
        except Exception:
            return []
    
    def _analyze_file_structure(self) -> Dict[str, List[str]]:
        """Analyze repository file structure."""
        structure = {}
        
        try:
            # Get top-level directories
            for item in self.repo_root.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    files = []
                    try:
                        for file in item.rglob('*'):
                            if file.is_file() and not any(part.startswith('.') for part in file.parts):
                                files.append(file.name)
                    except Exception:
                        pass
                    structure[item.name] = files[:20]  # Limit to first 20 files
        except Exception:
            pass
        
        return structure
    
    def filter_diff(self, diff_content: str, ignore_patterns: List[str]) -> str:
        """Filter diff content based on ignore patterns."""
        if not ignore_patterns:
            return diff_content
        
        spec = pathspec.PathSpec.from_lines('gitwildmatch', ignore_patterns)
        lines = diff_content.split('\n')
        filtered_lines = []
        current_file = None
        skip_file = False
        
        for line in lines:
            if line.startswith('diff --git'):
                # Extract filename from diff header
                parts = line.split(' ')
                if len(parts) >= 4:
                    current_file = parts[3][2:]  # Remove 'b/' prefix
                    skip_file = spec.match_file(current_file)
            
            if not skip_file:
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
